import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
import resource
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import eigsh

import direct_control

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
PRIOR = CONCEPT / "adversary/champion_1_search"
TARGETS = direct_control.TARGETS
CASE_BUDGET_SECONDS = 1000


def write_json(path, record):
    path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    return {
        str(path.relative_to(CONCEPT)): sha256(path)
        for directory in ("participant", "evaluator", "champions/generation_1")
        for path in (CONCEPT / directory).rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def gaps(record):
    return np.array([record["prediction"]["targets"][target] for target in TARGETS])


def reference(case, count, fock=80, frequency=2.0, tolerance=2e-13):
    wall_start, cpu_start = time.monotonic(), time.process_time()
    prediction, diagnostic = direct_control.solve(
        case, count=count, fock=fock, frequency=frequency, tolerance=tolerance
    )
    scale = (case["lambda"] / 6) ** (1 / 3)
    physical_gaps = np.array([prediction["targets"][target] for target in TARGETS])
    residuals = np.array(diagnostic["residuals_dimensionless"])
    residual_sums = np.array([
        residuals[0, 0] + residuals[1, 0], residuals[0].sum(), residuals[1].sum()
    ])
    rounding = 64 * np.finfo(float).eps * max(
        1.0, np.max(np.abs(diagnostic["shifted_sector_energies_dimensionless"]))
    )
    masses = np.array(case.get("mu2_by_site", [case["mu2"]] * case["sites"])) / scale**2
    quartics = np.array(case.get("lambda_by_site", [case["lambda"]] * case["sites"])) / (6 * scale**3)
    bonds = np.array(case.get("kappa_by_bond", [case["kappa"]] * (case["sites"] - 1))) / scale**2
    origin = 0.0
    for site in range(case["sites"]):
        degree = (bonds[site - 1] if site else 0.0) + (bonds[site] if site < case["sites"] - 1 else 0.0)
        levels, unused_position = direct_control.local_basis(masses[site] + degree, quartics[site], count, fock, frequency)
        origin += levels[0]
    absolute = (np.array(diagnostic["shifted_sector_energies_dimensionless"]) + origin) * scale
    return {
        "prediction": prediction,
        "diagnostic": diagnostic,
        "absolute_sector_energies": {"even": absolute[0].tolist(), "odd": absolute[1].tolist()},
        "ground_energy": float(absolute[0, 0]),
        "residual_roundoff_gap_ratio": ((residual_sums + rounding) / np.maximum(np.abs(physical_gaps / scale), 1e-300)).tolist(),
        "seconds": time.monotonic() - wall_start,
        "cpu_seconds": time.process_time() - cpu_start,
        "peak_rss_mib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }


def admissible_solve(record, scale):
    return bool(
        np.min(gaps(record) / scale) >= 1e-6
        and max(record["residual_roundoff_gap_ratio"]) <= 2e-6
        and np.max(record["diagnostic"]["residuals_dimensionless"]) <= 1e-10
    )


def native_fock_crosscheck(case, cutoff):
    started, cpu_start = time.monotonic(), time.process_time()
    sites = case["sites"]
    scale = (case["lambda"] / 6) ** (1 / 3)
    frequency = 2.34
    padded = cutoff + 4
    lowering = np.diag(np.sqrt(np.arange(1, padded)), 1)
    coordinate = (lowering + lowering.T) / np.sqrt(2 * frequency)
    momentum = 1j * np.sqrt(frequency / 2) * (lowering.T - lowering)
    square = coordinate @ coordinate
    fourth = square @ square
    kinetic = (momentum @ momentum).real / 2
    coordinate, square, fourth, kinetic = [sparse.csr_matrix(matrix[:cutoff, :cutoff]) for matrix in (coordinate, square, fourth, kinetic)]
    identity = sparse.eye(cutoff, format="csr")
    masses = np.array(case.get("mu2_by_site", [case["mu2"]] * sites)) / scale**2
    quartics = np.array(case.get("lambda_by_site", [case["lambda"]] * sites)) / (6 * scale**3)
    bonds = np.array(case.get("kappa_by_bond", [case["kappa"]] * (sites - 1))) / scale**2
    origins = -np.minimum(masses, 0)**2 / (4 * quartics)

    def product(factors):
        result = factors[0]
        for factor in factors[1:]:
            result = sparse.kron(result, factor, format="csr")
        return result

    matrix = sparse.csr_matrix((cutoff**sites, cutoff**sites))
    for site in range(sites):
        degree = (bonds[site - 1] if site else 0.0) + (bonds[site] if site < sites - 1 else 0.0)
        factors = [identity] * sites
        factors[site] = kinetic + (masses[site] + degree) * square / 2 + quartics[site] * fourth / 4 - origins[site] * identity
        matrix += product(factors)
    for bond, coupling in enumerate(bonds):
        factors = [identity] * sites
        factors[bond], factors[bond + 1] = coordinate, coordinate
        matrix -= coupling * product(factors)
    occupations = np.indices((cutoff,) * sites).reshape(sites, -1)
    parity = occupations.sum(axis=0) % 2
    sectors, residuals = [], []
    for sector in (0, 1):
        indices = np.flatnonzero(parity == sector)
        block = matrix[indices][:, indices].tocsr()
        initial = np.cos(np.arange(len(indices)) * np.sqrt(2) + 0.739)
        values, vectors = eigsh(block, k=2, which="SA", tol=1e-13, ncv=40, v0=initial, maxiter=20000)
        order = np.argsort(values)
        vectors = vectors[:, order].astype(np.longdouble)
        products = block.astype(np.longdouble) @ vectors
        rayleigh = np.sum(vectors * products, axis=0) / np.sum(vectors**2, axis=0)
        residuals.append(np.sqrt(np.sum((products - vectors * rayleigh)**2, axis=0)).astype(float).tolist())
        sectors.append(rayleigh)
    even, odd = sectors
    targets = scale * np.array([odd[0] - even[0], even[1] - even[0], odd[1] - odd[0]], dtype=float)
    return {"cutoff": cutoff, "frequency": frequency, "targets": dict(zip(TARGETS, targets.tolist())), "state_residuals_dimensionless": residuals, "absolute_sector_energies": ((np.asarray(sectors, dtype=float) + origins.sum()) * scale).tolist(), "seconds": time.monotonic() - started, "cpu_seconds": time.process_time() - cpu_start}


def timeout_handler(unused_signal, unused_frame):
    raise TimeoutError("bounded independent truth gate exhausted")


def worker(index):
    case = json.loads((PRIOR / "private/extension_seeds.json").read_text())["cases"][index]
    directory = ROOT / f"L{case['sites']}"
    directory.mkdir(exist_ok=True)
    result = {"case": case, "accepted": False, "truth_extrapolated": False, "rigorous_full_Hilbert_space_bound": False, "residual_scope": "finite compressed product Hamiltonian; independent cutoff and oscillator-basis comparisons test truncation empirically", "history": [], "controls": []}
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, CASE_BUDGET_SECONDS)
    started = time.monotonic()
    try:
        scale = (case["lambda"] / 6) ** (1 / 3)
        for count in (6, 8, 10, 12, 14, 16):
            current = reference(case, count)
            result["history"].append(current)
            write_json(directory / "result.json", result)
            print(json.dumps({"sites": case["sites"], "count": count, "targets": current["prediction"]["targets"], "cpu_seconds": current["cpu_seconds"], "residual": float(np.max(current["diagnostic"]["residuals_dimensionless"]))}), flush=True)
            if len(result["history"]) < 3:
                continue
            recent = result["history"][-3:]
            if not all(admissible_solve(record, scale) for record in recent):
                continue
            changes = [np.abs(np.log(gaps(recent[offset + 1]) / gaps(recent[offset]))) for offset in (0, 1)]
            result["last_two_cutoff_log_changes"] = [change.tolist() for change in changes]
            write_json(directory / "result.json", result)
            if np.max(changes) > 2e-5:
                continue
            doubled = reference(case, count, fock=160)
            independent = reference(case, count, fock=160, frequency=2.34, tolerance=1e-13)
            doubling_error = np.abs(np.log(gaps(doubled) / gaps(current)))
            basis_error = np.abs(np.log(gaps(independent) / gaps(doubled)))
            result.update({"doubled_onsite_cutoff": doubled, "independent_basis": independent, "doubled_cutoff_log_change": doubling_error.tolist(), "independent_basis_log_change": basis_error.tolist()})
            if not admissible_solve(doubled, scale) or not admissible_solve(independent, scale) or max(np.max(doubling_error), np.max(basis_error)) > 2e-5:
                write_json(directory / "result.json", result)
                continue
            result.update({"accepted": True, "label": doubled["prediction"], "ground_energy": doubled["ground_energy"], "absolute_sector_energies": doubled["absolute_sector_energies"], "retained_local_states": count, "label_rule": "direct doubled-Fock reference Ritz gaps; no extrapolation", "reason": "original numerical admission conditions plus 80-to-160 onsite-cutoff check passed"})
            write_json(directory / "result.json", result)
            for control_count in (4, 6, 8):
                control = reference(case, control_count, tolerance=1e-12)
                errors = np.abs(np.log(gaps(control) / gaps(doubled)))
                control.update({"absolute_log_errors": dict(zip(TARGETS, errors.tolist())), "mean_log_error": float(np.mean(errors)), "p95_log_error": float(np.quantile(errors, 0.95)), "max_log_error": float(np.max(errors)), "single_case_thresholds_pass": bool(np.mean(errors) <= 0.03 and np.quantile(errors, 0.95) <= 0.12), "full_72_case_resource_pass_claimed": False})
                result["controls"].append(control)
                write_json(directory / "result.json", result)
            if case["sites"] == 4:
                result["independent_full_Fock_crosschecks"] = []
                for cutoff in (24, 32):
                    crosscheck = native_fock_crosscheck(case, cutoff)
                    cross_gaps = np.array([crosscheck["targets"][target] for target in TARGETS])
                    crosscheck["log_difference_from_label"] = np.abs(np.log(cross_gaps / gaps(doubled))).tolist()
                    result["independent_full_Fock_crosschecks"].append(crosscheck)
                    write_json(directory / "result.json", result)
            break
        if not result["accepted"]:
            result["reason"] = "retained-basis, onsite-cutoff, basis-frequency, or residual certificate not achieved"
    except (TimeoutError, MemoryError, RuntimeError, ValueError) as error:
        result["bounded_stop"] = str(error)
        if not result["accepted"]:
            result["reason"] = "unconverged or uncertified within fixed numerical budget; not a label and not failure evidence"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        result["elapsed_seconds"] = time.monotonic() - started
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(directory / "result.json", result)
        print(json.dumps({"sites": case["sites"], "accepted": result["accepted"], "reason": result.get("reason"), "elapsed_seconds": result["elapsed_seconds"]}), flush=True)


def launch():
    source_files = [PRIOR / name for name in ("FINAL_REPORT.json", "FINDINGS.md", "target_proposal.json", "direct_control.py", "extension_teacher.py", "private/extension_seeds.json")]
    source_files += [CONCEPT / "evaluator/hidden/teacher.py", CONCEPT / "champions/generation_1/predict.py"]
    assert sha256(ROOT / "direct_control.py") == sha256(PRIOR / "direct_control.py")
    before = snapshot()
    write_json(ROOT / "plan.json", {"started_utc": datetime.now(timezone.utc).isoformat(), "case_selection": "Exactly the three pre-existing pilot seeds, selected before new results; no performance-conditioned sampling.", "case_budget_seconds": CASE_BUDGET_SECONDS, "maximum_workers": 3, "maximum_fresh_agents": 0, "source_native_control_identical_copy": True, "sources": {str(path.relative_to(CONCEPT)): sha256(path) for path in source_files}, "frozen_snapshot": before, "admission": {"dimensionless_gap_floor": 1e-6, "two_successive_retained_cutoff_log_changes": 2e-5, "onsite_Fock_cutoffs": [80, 160], "independent_frequency": 2.34, "maximum_basis_log_change": 2e-5, "state_residual_max": 1e-10, "residual_roundoff_gap_ratio_max": 2e-6}, "no_unsupported_schema_failure_counted": True, "no_single_case_batch_time_extrapolation": True})
    workers = []
    for index in range(3):
        log = (ROOT / f"worker_{index}.log").open("w")
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(index)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        workers.append((process, log))
    for process, log in workers:
        process.wait()
        log.close()
    results = [json.loads(path.read_text()) for path in sorted(ROOT.glob("L*/result.json"))]
    assert snapshot() == before
    write_json(ROOT / "completion.json", {"finished_utc": datetime.now(timezone.utc).isoformat(), "all_workers_stopped": True, "worker_return_codes": [process.returncode for process, unused_log in workers], "frozen_and_champion_files_unchanged": True, "accepted_sites": [record["case"]["sites"] for record in results if record["accepted"]], "excluded_sites": [record["case"]["sites"] for record in results if not record["accepted"]], "fresh_agents_launched": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=int)
    arguments = parser.parse_args()
    if arguments.worker is None:
        launch()
    else:
        worker(arguments.worker)
