import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
for variable in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "private" / "reference" / "vendor" / "tenpy"
if not (SOURCE / "tenpy" / "__init__.py").exists():
    SOURCE = ROOT.parent / "private" / "sources" / "tenpy"
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import numpy as np
import tenpy
from tenpy.algorithms import dmrg
from tenpy.models.hubbard import BoseHubbardChain
from tenpy.models.lattice import Chain
from tenpy.models.model import CouplingMPOModel
from tenpy.networks.mps import MPS
from tenpy.networks.site import SpinSite

from baseline import exact_result, product_configuration, product_result
from cases import all_cases, small_cases


TENPY_COMMIT = "b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04"
LIMITS = {"energy_per_site": 3e-6, "gap": 2e-4, "correlations_max": 3e-4}


class ExplicitSpinModel(CouplingMPOModel):
    default_lattice = Chain
    force_default_lattice = True

    def __init__(self, case):
        self.case = case
        super().__init__({"L": case["length"], "bc_MPS": "finite", "bc_x": "open"})

    def init_sites(self, model_params):
        site = SpinSite(S=self.case["spin"], conserve="Sz")
        if self.case["spin"] == 1:
            diagonal = np.diag(site.Sz.to_ndarray())
            site.add_op("StringZ", np.diag(np.cos(np.pi * diagonal)), permute_dense=False)
        return site

    def init_terms(self, model_params):
        for site in range(self.case["length"]):
            self.add_onsite_term(self.case["single_ion"][site], site, "Sz Sz")
            self.add_onsite_term(-self.case["field"][site], site, "Sz")
        for bond in self.case["bonds"]:
            left, right = bond["sites"]
            self.add_coupling_term(bond["jxy"] / 2, left, right, "Sp", "Sm", plus_hc=True)
            self.add_coupling_term(bond["jz"], left, right, "Sz", "Sz")


def make_model(case):
    if case["family"] != "bose_hubbard":
        return ExplicitSpinModel(case)
    return BoseHubbardChain({
        "L": case["length"], "n_max": case["nmax"], "filling": 1.0,
        "bc_MPS": "finite", "bc_x": "open", "conserve": "N",
        "t": np.array([bond["hopping"] for bond in case["bonds"]]),
        "U": np.asarray(case["interaction"]), "mu": -np.asarray(case["potential"]),
    })


def initial_state(case, model, sector):
    values = product_configuration(case, sector)
    operator = "N" if case["family"] == "bose_hubbard" else "Sz"
    indices = []
    for site, value in zip(model.lat.mps_sites(), values):
        diagonal = np.real(np.diag(site.get_op(operator).to_ndarray()))
        indices.append(int(np.argmin(abs(diagonal - value))))
    return MPS.from_product_state(model.lat.mps_sites(), indices, bc="finite", dtype=float)


def optimize(case, model, sector, chi, state=None):
    if state is None:
        state = initial_state(case, model, sector)
    options = {
        "mixer": True, "mixer_params": {"amplitude": 1e-5, "decay": 2.0, "disable_after": 8},
        "trunc_params": {"chi_max": chi, "svd_min": 1e-12},
        "max_E_err": 1e-11, "max_S_err": 1e-8,
        "min_sweeps": 6, "max_sweeps": 30, "N_sweeps_check": 2,
        "lanczos_params": {"N_max": 80, "P_tol": 1e-12, "E_tol": 1e-12},
        "combine": True,
    }
    started = time.perf_counter()
    engine = dmrg.TwoSiteDMRGEngine(state, model, options)
    _, state = engine.run()
    state.canonical_form()
    energy = float(np.real(model.H_MPO.expectation_value(state)))
    charge_operator = "N" if case["family"] == "bose_hubbard" else "Sz"
    measured_sector = float(np.real(np.sum(state.expectation_value(charge_operator))))
    if abs(measured_sector - sector) > 1e-7:
        raise ValueError(f"wrong sector: {measured_sector} != {sector}")
    statistics = {
        "sector": sector, "energy": energy, "chi_requested": chi,
        "chi_used": int(max(state.chi)), "sweeps": int(engine.sweeps),
        "seconds": time.perf_counter() - started,
        "measured_sector": measured_sector,
        "norm_error": float(np.linalg.norm(state.norm_test())),
        "last_sweep_energies": [float(value) for value in engine.sweep_stats["E"][-6:]],
    }
    return energy, state, statistics


def correlations(case, state):
    results = []
    for observable in case["observables"]:
        left, right = observable["sites"]
        kind = observable["kind"]
        if kind == "zz":
            value = state.expectation_value_term([("Sz", left), ("Sz", right)])
        elif kind == "xx":
            value = (state.expectation_value_term([("Sp", left), ("Sm", right)]) + state.expectation_value_term([("Sm", left), ("Sp", right)])) / 4
        elif kind == "string":
            terms = [("Sz", left)] + [("StringZ", site) for site in range(left + 1, right)] + [("Sz", right)]
            value = -state.expectation_value_term(terms)
        elif kind == "one_body":
            value = state.expectation_value_term([("Bd", left), ("B", right)])
        elif kind == "density_connected":
            value = state.expectation_value_term([("N", left), ("N", right)])
            value -= state.expectation_value_term([("N", left)]) * state.expectation_value_term([("N", right)])
        else:
            raise ValueError(kind)
        if abs(np.imag(value)) > 1e-9:
            raise ValueError("unexpected imaginary correlation")
        results.append(float(np.real(value)))
    return results


def differences(first, second, length):
    return {
        "energy_per_site": abs(first["energy"] - second["energy"]) / length,
        "gap": abs(first["gap"] - second["gap"]),
        "correlations_max": float(np.max(np.abs(np.asarray(first["correlations"]) - second["correlations"]))),
    }


def calculate(case, chis):
    model = make_model(case)
    bosons = case["family"] == "bose_hubbard"
    primary_sector = case["particles"] if bosons else case["ground_sector"]
    sectors = [primary_sector, primary_sector - 1, primary_sector + 1] if bosons else [primary_sector, case["excited_sector"]]
    states = {}
    history = []
    difference = None
    for chi in chis:
        energies = {}
        stage = {"chi": chi, "sectors": []}
        for sector in sectors:
            energy, states[sector], stats = optimize(case, model, sector, chi, states.get(sector))
            energies[sector] = energy
            stage["sectors"].append(stats)
        gap = energies[primary_sector - 1] + energies[primary_sector + 1] - 2 * energies[primary_sector] if bosons else energies[case["excited_sector"]] - energies[primary_sector]
        result = {"energy": energies[primary_sector], "gap": gap, "correlations": correlations(case, states[primary_sector])}
        stage["result"] = result
        if history:
            difference = differences(result, history[-1]["result"], case["length"])
        history.append(stage)
        if difference is not None and all(difference[key] <= LIMITS[key] for key in LIMITS):
            break
    ready = difference is not None and all(difference[key] <= LIMITS[key] for key in LIMITS)
    return result, {"ready": ready, "limits": LIMITS, "last_difference": difference, "history": history}


def generate_one(case_id, case, chis):
    folder = ROOT / "private" / "reference"
    (folder / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.WARNING, filename=folder / "logs" / f"{case_id}.log", force=True)
    started = time.perf_counter()
    try:
        result, validation = calculate(case, chis)
        payload = {
            "case_id": case_id, "family": case["family"], "ready": validation["ready"],
            "reference": result, "weak": product_result(case), "convergence": validation,
            "source": {"library": "TeNPy", "version": tenpy.__version__, "commit": TENPY_COMMIT},
            "input_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
            "generation_seconds": time.perf_counter() - started,
        }
    except Exception:
        payload = {"case_id": case_id, "ready": False, "error": traceback.format_exc(), "generation_seconds": time.perf_counter() - started}
    (folder / "data").mkdir(exist_ok=True)
    destination = folder / "data" / f"{case_id}.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    temporary.replace(destination)
    return {"case_id": case_id, "ready": payload["ready"], "seconds": payload["generation_seconds"], "error": payload.get("error")}


def validate_small():
    records = []
    for case_id, case in small_cases().items():
        exact = exact_result(case)
        reference, convergence = calculate(case, [32, 64])
        delta = differences(reference, exact, case["length"])
        passed = delta["energy_per_site"] < 1e-9 and delta["gap"] < 1e-8 and delta["correlations_max"] < 1e-7 and exact["max_residual"] < 1e-8
        record = {"case_id": case_id, "passed": passed, "input": case, "exact": exact, "reference": reference, "difference": delta, "convergence": convergence}
        records.append(record)
        print(json.dumps({"case_id": case_id, "passed": passed, "difference": delta}), flush=True)
    destination = ROOT / "private" / "reference" / "validation" / "small_exact.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps({"passed": all(record["passed"] for record in records), "cases": records}, indent=2, allow_nan=False) + "\n")
    return all(record["passed"] for record in records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["core", "challenge", "all", "small"], default="all")
    parser.add_argument("--case")
    parser.add_argument("--chis", default="64,128,192")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.split == "small":
        raise SystemExit(0 if validate_small() else 1)
    selected = {}
    for split, cases in all_cases().items():
        if args.split in ["all", split]:
            selected.update(cases)
    if args.case:
        selected = {args.case: selected[args.case]}
    chis = [int(value) for value in args.chis.split(",")]
    outcomes = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(generate_one, case_id, case, chis) for case_id, case in selected.items()]
        for future in as_completed(futures):
            outcome = future.result()
            outcomes.append(outcome)
            print(json.dumps(outcome), flush=True)
    raise SystemExit(0 if all(outcome["ready"] for outcome in outcomes) else 1)


if __name__ == "__main__":
    main()
