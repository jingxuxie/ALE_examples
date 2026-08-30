import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "champion"))

import numpy as np
from scipy.special import ellipk

import optimizer
from contractor import load_mps, measure, save_mps
from observables import diagnostics
from refine import project_parity, refine


def phase_center(quartic, coupling):
    effective = quartic / coupling ** 1.5
    renormalized = effective / 65.0
    correction = effective * ellipk(4 / (4 + renormalized)) / (2 * np.pi * np.sqrt(4 + renormalized))
    return float(coupling * (renormalized - correction))


def request_for(args, mass, sector):
    request = {"version": 1, "case_id": "%s-%s-%+.4f" % (args.label, sector, mass), "seed": 13025582,
               "n_sites": args.length, "local_dim": args.dimension, "bond_cap": args.cap, "sector": sector,
               "omega": [args.omega] * args.length, "mass2": [mass] * args.length,
               "lambda4": [args.quartic] * args.length, "coupling": [args.coupling] * (args.length - 1),
               "field": [0.0] * args.length, "budget_seconds": args.champion_cpu, "wall_seconds": 120.0}
    if args.weak_link < 1.0:
        request["coupling"][args.length // 2 - 1] *= args.weak_link
    if args.mass_modulation:
        request["mass2"] = (mass + args.mass_modulation * np.cos(np.linspace(0, 2 * np.pi, args.length))).tolist()
    if args.field_amplitude:
        if sector != "any":
            raise ValueError("Nonzero fields require an unrestricted request")
        profile = np.ones(args.length) if args.field_mode == "uniform" else np.cos(np.linspace(0, np.pi, args.length))
        request["field"] = (args.field_amplitude * profile).tolist()
    return request


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def run_case(args, mass, sector):
    request = request_for(args, mass, sector)
    directory = ROOT / "runs" / request["case_id"]
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / "request.json"
    if request_path.exists() and json.loads(request_path.read_text()) != request:
        raise ValueError("Refusing to reuse a label for a different request")
    write_json(request_path, request)
    champion_state = directory / "champion.npz"
    result_path = directory / "result.json"
    source_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in list(sorted((ROOT / "champion").glob("*.py")))
                     + [ROOT / "teacher_engine.py", ROOT / "refine.py", ROOT / "observables.py", Path(__file__)]}
    if champion_state.exists() and result_path.exists():
        result = json.loads(result_path.read_text())
        tensors = load_mps(champion_state, request)
    else:
        started = time.process_time()
        wall_started = time.monotonic()
        with (directory / "champion.log").open("w") as output, contextlib.redirect_stdout(output):
            tensors = optimizer.optimize(request, start_cpu=started, start_wall=wall_started)
        elapsed_cpu = time.process_time() - started
        elapsed_wall = time.monotonic() - wall_started
        save_mps(champion_state, tensors)
        checked = measure(load_mps(champion_state, request), request)
        result = {"request": request, "seed_center_mass2": phase_center(args.quartic, args.coupling),
                  "physical_validity": True, "score": None,
                  "mode": "generation-time reviewed-copy in-process probe; not resource certification",
                  "champion": dict(checked, optimization_cpu_seconds=elapsed_cpu,
                                   optimization_wall_seconds=elapsed_wall,
                                   diagnostics=diagnostics(tensors, request, checked["energy"]))}
        result["champion_source_hashes"] = source_hashes
        write_json(result_path, result)
        print(json.dumps({"event": "champion", "case": request["case_id"], "mass2": mass,
                          "energy": checked["energy"], "cpu_seconds": elapsed_cpu,
                          "entropy": result["champion"]["diagnostics"]["center_entropy"],
                          "variance": result["champion"]["diagnostics"]["energy_variance"]}), flush=True)
    if args.refine:
        result["reference_source_hashes"] = source_hashes
        started = time.process_time()
        wall_started = time.monotonic()
        teacher_request = request
        teacher_seed = tensors
        if args.teacher_parity is not None:
            if request["sector"] != "any":
                raise ValueError("Teacher parity probes require an unrestricted champion request")
            zero_field_request = dict(request, field=[0.0] * request["n_sites"])
            teacher_seed = project_parity(tensors, zero_field_request, args.teacher_parity)
            teacher_request = request if any(request["field"]) else dict(request, sector=args.teacher_parity)
            result["teacher_projection"] = dict(measure(teacher_seed, request), projected_sector=args.teacher_parity,
                                                 refinement_uses_full_original_hamiltonian=True,
                                                 refinement_sector=teacher_request["sector"])
            save_mps(directory / "projected_seed.npz", teacher_seed)

        def checkpoint(state, trajectory):
            save_mps(directory / "reference.npz", state)
            write_json(directory / "trajectory.json", trajectory)

        reference, trajectory = refine(teacher_seed, teacher_request, args.teacher_cpu, args.teacher_sweeps, checkpoint)
        if measure(reference, request)["energy"] > result["champion"]["energy"]:
            reference = tensors
        elapsed_cpu = time.process_time() - started
        elapsed_wall = time.monotonic() - wall_started
        save_mps(directory / "reference.npz", reference)
        checked = measure(load_mps(directory / "reference.npz", request), request)
        result["reference"] = dict(checked, optimization_cpu_seconds=elapsed_cpu,
                                   optimization_wall_seconds=elapsed_wall,
                                   diagnostics=diagnostics(reference, request, checked["energy"]))
        result["trajectory"] = trajectory
        result["achieved_energy_gap"] = result["champion"]["energy"] - checked["energy"]
        result["gap_per_site"] = result["achieved_energy_gap"] / request["n_sites"]
        result["gap_above_requested_screen"] = result["gap_per_site"] > 1e-7
        result["ground_energy_certified"] = False
        result["artifact_hashes"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in (request_path, champion_state, directory / "reference.npz")}
        write_json(result_path, result)
        print(json.dumps({"event": "reference", "case": request["case_id"], "energy": checked["energy"],
                          "gap": result["achieved_energy_gap"], "gap_per_site": result["gap_per_site"],
                          "cpu_seconds": elapsed_cpu, "physical_validity": True,
                          "result": str(result_path.relative_to(ROOT))}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--length", type=int, default=20)
    parser.add_argument("--dimension", type=int, default=12)
    parser.add_argument("--cap", type=int, default=8)
    parser.add_argument("--quartic", type=float, default=2.0)
    parser.add_argument("--coupling", type=float, default=1.0)
    parser.add_argument("--omega", type=float, default=1.0)
    parser.add_argument("--masses", default="-0.6,-0.5,-0.7,-0.4,-0.8,-0.3")
    parser.add_argument("--sectors", nargs="+", default=["even", "odd"])
    parser.add_argument("--champion-cpu", type=float, default=40.0)
    parser.add_argument("--teacher-cpu", type=float, default=30.0)
    parser.add_argument("--teacher-sweeps", type=int, default=6)
    parser.add_argument("--weak-link", type=float, default=1.0)
    parser.add_argument("--mass-modulation", type=float, default=0.0)
    parser.add_argument("--field-amplitude", type=float, default=0.0)
    parser.add_argument("--field-mode", choices=("uniform", "cosine"), default="uniform")
    parser.add_argument("--teacher-parity", choices=("even", "odd"))
    parser.add_argument("--refine", action="store_true")
    args = parser.parse_args()
    results = []
    for mass in map(float, args.masses.split(",")):
        for sector in args.sectors:
            results.append(run_case(args, mass, sector))
            summary = {"score": None, "timing_is_not_a_hardness_metric": True,
                       "source_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in sorted((ROOT / "champion").glob("*.py"))},
                       "results": results}
            write_json(ROOT / (args.label + "_summary.json"), summary)


if __name__ == "__main__":
    main()
