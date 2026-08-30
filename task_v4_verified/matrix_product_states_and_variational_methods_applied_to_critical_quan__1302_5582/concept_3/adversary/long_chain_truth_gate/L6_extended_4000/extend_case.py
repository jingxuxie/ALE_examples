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
from scipy.sparse.linalg import LinearOperator

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent
CONCEPT = PREVIOUS.parents[1]
sys.path.insert(0, str(PREVIOUS))
import direct_control
import truth_gate as previous_gate

WALL_BUDGET = 4000
CPU_BUDGET = 4000
MEMORY_LIMIT = 8 * 1024**3
TARGETS = direct_control.TARGETS
STARTED = None


class BudgetExceeded(RuntimeError):
    pass


def budget_handler(unused_signal, unused_frame):
    raise BudgetExceeded("extended one-case wall/CPU budget exhausted")


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def protected_snapshot():
    result = previous_gate.snapshot()
    for path in PREVIOUS.rglob("*"):
        if path.is_file() and not path.is_relative_to(ROOT):
            result[str(path.relative_to(CONCEPT))] = digest(path)
    return result


def gap_values(record):
    return np.array([record["prediction"]["targets"][target] for target in TARGETS])


def solve_stage(case, count, fock, frequency, name, warm_vectors=None):
    wall_start, cpu_start = time.monotonic(), time.process_time()
    original_local_basis = direct_control.local_basis
    original_eigsh = direct_control.eigsh
    local_data, captured_vectors, iterations = [], [], []

    def canonical_local_basis(*arguments):
        levels, position = original_local_basis(*arguments)
        phases = np.ones(len(levels))
        for index in range(1, len(levels)):
            adjacent = position[index - 1, index]
            if abs(adjacent) < 1e-12:
                raise ValueError("cannot fix adjacent onsite position phases reliably")
            phases[index] = phases[index - 1] * np.sign(adjacent)
        position = phases[:, None] * position * phases[None, :]
        local_data.append((levels.copy(), position.copy()))
        return levels, position

    def monitored_eigsh(operator, **arguments):
        sector = len(captured_vectors)
        calls = 0
        if warm_vectors is not None:
            previous_vectors = warm_vectors[sector]
            if previous_vectors.shape != (operator.shape[0], 2):
                raise ValueError("warm eigenvectors have the wrong parity-sector dimension")
            initial = previous_vectors[:, 0] + 0.63 * previous_vectors[:, 1]
            initial /= np.linalg.norm(initial)
            noise = arguments["v0"].copy()
            noise /= np.linalg.norm(noise)
            initial += 1e-8 * noise
            initial /= np.linalg.norm(initial)
            arguments["v0"] = initial
            arguments["ncv"] = min(32, operator.shape[0])

        def multiply(vector):
            nonlocal calls
            calls += 1
            if calls == 1 or calls % 25 == 0:
                write_json(ROOT / "progress.json", {
                    "stage": name, "sector": sector, "matvec_calls": calls,
                    "retained_count": count, "onsite_fock_cutoff": fock,
                    "frequency": frequency, "warm_started": warm_vectors is not None,
                    "stage_wall_seconds": time.monotonic() - wall_start,
                    "total_wall_seconds": time.monotonic() - STARTED,
                    "cpu_seconds_process": time.process_time(),
                })
            return operator.matvec(vector)

        monitored = LinearOperator(operator.shape, matvec=multiply, dtype=float)
        values, vectors = original_eigsh(monitored, **arguments)
        order = np.argsort(values)
        captured_vectors.append(vectors[:, order].copy())
        iterations.append({"sector": sector, "matvec_calls": calls, "ncv": arguments["ncv"]})
        return values, vectors

    direct_control.local_basis = canonical_local_basis
    direct_control.eigsh = monitored_eigsh
    try:
        prediction, diagnostic = direct_control.solve(
            case, count=count, fock=fock, frequency=frequency, tolerance=2e-13
        )
    finally:
        direct_control.local_basis = original_local_basis
        direct_control.eigsh = original_eigsh
    if len(local_data) != case["sites"] or len(captured_vectors) != 2:
        raise ValueError("incomplete onsite or parity-sector eigensolution")
    scale = (case["lambda"] / 6) ** (1 / 3)
    gaps = np.array([prediction["targets"][target] for target in TARGETS]) / scale
    residuals = np.array(diagnostic["residuals_dimensionless"])
    residual_sums = np.array([
        residuals[0, 0] + residuals[1, 0], residuals[0].sum(), residuals[1].sum()
    ])
    shifted = np.array(diagnostic["shifted_sector_energies_dimensionless"])
    rounding = 64 * np.finfo(float).eps * max(1.0, np.max(np.abs(shifted)))
    origin = sum(levels[0] for levels, unused_position in local_data)
    absolute = (shifted + origin) * scale
    state_path = ROOT / f"{name}.npz"
    np.savez(state_path, even_vectors=captured_vectors[0], odd_vectors=captured_vectors[1],
             onsite_levels=np.array([levels for levels, unused_position in local_data]),
             onsite_positions=np.array([position for unused_levels, position in local_data]),
             retained_count=count, onsite_fock_cutoff=fock, frequency=frequency)
    record = {
        "prediction": prediction, "diagnostic": diagnostic,
        "absolute_sector_energies": {"even": absolute[0].tolist(), "odd": absolute[1].tolist()},
        "ground_energy": float(absolute[0, 0]),
        "residual_roundoff_gap_ratio": ((residual_sums + rounding) / np.maximum(np.abs(gaps), 1e-300)).tolist(),
        "seconds": time.monotonic() - wall_start,
        "cpu_seconds": time.process_time() - cpu_start,
        "iterations": iterations, "warm_started": warm_vectors is not None,
        "actual_eigensolver_run": True, "eigenvectors": state_path.name,
        "eigenvectors_sha256": digest(state_path),
        "peak_rss_mib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "phase_gauge": "Adjacent onsite position matrix elements fixed positive; a diagonal parity-preserving unitary gauge only.",
    }
    write_json(ROOT / f"{name}.json", record)
    print(json.dumps({"stage": name, "targets": prediction["targets"], "seconds": record["seconds"],
                      "cpu_seconds": record["cpu_seconds"], "iterations": iterations,
                      "residual_max": float(np.max(residuals))}), flush=True)
    return record, captured_vectors


def validate_source_equivalence(case):
    small = dict(case, id="L6_extension_implementation_L2", sites=2)
    for key in ("mu2_by_site", "lambda_by_site"):
        small[key] = case[key][:2]
    small["kappa_by_bond"] = case["kappa_by_bond"][:1]
    first, vectors = solve_stage(small, 6, 20, 2.0, "validation_f20")
    second, unused_vectors = solve_stage(small, 6, 40, 2.34, "validation_f40", vectors)
    comparisons = []
    for record, fock, frequency in ((first, 20, 2.0), (second, 40, 2.34)):
        reference = previous_gate.reference(small, 6, fock=fock, frequency=frequency)
        difference = float(np.max(np.abs(gap_values(record) - gap_values(reference))))
        energy_difference = float(np.max(np.abs(
            np.array(list(record["absolute_sector_energies"].values()))
            - np.array(list(reference["absolute_sector_energies"].values()))
        )))
        if difference > 1e-11 or energy_difference > 1e-11:
            raise ValueError("phase-gauged/warm solver disagrees with unchanged native implementation")
        comparisons.append({"fock": fock, "frequency": frequency,
                            "maximum_gap_absolute_difference": difference,
                            "maximum_energy_absolute_difference": energy_difference})
    write_json(ROOT / "implementation_validation.json", {"passed": True, "comparisons": comparisons,
               "meaning": "Original matrix-free Hamiltonian and actual ARPACK solves retained; only onsite eigenvector phases, v0, ncv, monitoring and state retention differ."})


def native_probe(count):
    case = json.loads((ROOT / "query.json").read_text())["cases"][0]
    started, cpu_started = time.monotonic(), time.process_time()
    prediction, diagnostic = direct_control.solve(case, count=count)
    write_json(ROOT / f"native_{count}_prediction.json", {
        "prediction": prediction, "diagnostic": diagnostic,
        "cpu_seconds": time.process_time() - cpu_started,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    })


def probe_limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.signal(signal.SIGXCPU, signal.SIG_DFL)


def run_probe(name, command):
    started = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    timed_out = False
    with (ROOT / f"{name}.stdout.log").open("w") as stdout, (ROOT / f"{name}.stderr.log").open("w") as stderr:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                    timeout=60, preexec_fn=probe_limits)
            return_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            return_code = None
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"name": name, "command": command, "return_code": return_code,
            "wall_timeout": timed_out, "wall_seconds": time.monotonic() - started,
            "child_cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
            "limits": {"cpu_seconds": 30, "wall_seconds": 60, "address_space_gib": 2},
            "generation_only_probe": True, "official_30_CPU_batch_score": False,
            "stderr": f"{name}.stderr.log", "stdout": f"{name}.stdout.log"}


def run_controls(case, label):
    write_json(ROOT / "query.json", {"schema_version": 1, "cases": [case]})
    write_json(ROOT / "empty_train.json", {"schema_version": 1, "cases": []})
    probes = []
    literal = run_probe("unchanged_champion", [sys.executable, str(ROOT / "unchanged_predict.py"),
                        "--input", str(ROOT / "query.json"), "--train", str(ROOT / "empty_train.json"),
                        "--output", str(ROOT / "unchanged_prediction.json")])
    literal["source_sha256"] = digest(ROOT / "unchanged_predict.py")
    literal["interpretation"] = "Literal old champion is length-2/3-specific; unsupported length/schema errors are not scientific failures or official scores."
    probes.append(literal)
    write_json(ROOT / "generation_probes.json", {"probes": probes})
    for count in (4, 6, 8, 16):
        if time.monotonic() - STARTED > WALL_BUDGET - 100:
            break
        probe = run_probe(f"native_{count}", [sys.executable, str(Path(__file__).resolve()), "--native-probe", str(count)])
        probe["retained_local_states"] = count
        probe["source_sha256"] = digest(PREVIOUS / "direct_control.py")
        probe["implementation"] = "Unchanged reviewed general-length matrix-free source-native control, not the literal old length-specific champion."
        output = ROOT / f"native_{count}_prediction.json"
        if probe["return_code"] == 0 and output.exists():
            result = json.loads(output.read_text())
            predicted = np.array([result["prediction"]["targets"][target] for target in TARGETS])
            truth = np.array([label["targets"][target] for target in TARGETS])
            if np.all(predicted > 0):
                errors = np.abs(np.log(predicted / truth))
                probe.update({"targets": result["prediction"]["targets"],
                              "absolute_log_errors": dict(zip(TARGETS, errors.tolist())),
                              "mean_log_error": float(np.mean(errors)),
                              "p95_log_error": float(np.quantile(errors, 0.95)),
                              "maximum_log_error": float(np.max(errors)),
                              "single_case_accuracy_thresholds_pass": bool(np.mean(errors) <= 0.03 and np.quantile(errors, 0.95) <= 0.12),
                              "measured_solve_cpu_seconds": result["cpu_seconds"],
                              "peak_rss_mib": result["peak_rss_mib"]})
            else:
                probe.update({"invalid_nonpositive_prediction": True, "single_case_accuracy_thresholds_pass": False})
        else:
            probe["interpretation"] = "Generation-only single-case execution/resource failure; not an official full-batch score or evidence that all efficient methods fail."
        probes.append(probe)
        write_json(ROOT / "generation_probes.json", {"probes": probes})
    return probes


def main():
    global STARTED
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_BUDGET - 5, CPU_BUDGET))
    signal.signal(signal.SIGALRM, budget_handler)
    signal.signal(signal.SIGXCPU, budget_handler)
    STARTED = time.monotonic()
    signal.setitimer(signal.ITIMER_REAL, WALL_BUDGET)
    cpu_started = time.process_time()
    before = protected_snapshot()
    prior_path = PREVIOUS / "L6/result.json"
    prior = json.loads(prior_path.read_text())
    case = prior["case"]
    scale = (case["lambda"] / 6) ** (1 / 3)
    result = {"case": case, "accepted": False, "truth_extrapolated": False,
              "infinite_space_ground_state_certified": False,
              "prior_budgeted_run": str(prior_path.relative_to(CONCEPT)),
              "prior_budgeted_run_sha256": digest(prior_path),
              "prior_run_remains_unadmitted": True, "inherited_history": prior["history"],
              "new_stages": [], "generation_probes": [], "ratchet_admitted": False}
    write_json(ROOT / "plan.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(), "one_case_only": True,
        "wall_seconds": WALL_BUDGET, "cpu_seconds": CPU_BUDGET, "address_space_bytes": MEMORY_LIMIT,
        "case": case, "retained_counts_to_try": [14, 16],
        "source_hashes": {str(path.relative_to(CONCEPT)): digest(path) for path in
                          (PREVIOUS / "direct_control.py", PREVIOUS / "truth_gate.py", prior_path,
                           CONCEPT / "champions/generation_1/predict.py")},
        "protected_files": before,
        "admission": {"two_successive_retained_cutoff_log_changes": 2e-5,
                      "onsite_cutoffs": [80, 160], "basis_frequencies": [2.0, 2.34],
                      "maximum_basis_log_change": 2e-5, "state_residual_max": 1e-10,
                      "residual_roundoff_gap_ratio_max": 2e-6, "minimum_dimensionless_gap": 1e-6},
        "warm_start_policy": "Actual ARPACK solves at each cutoff and basis; matched onsite phase gauges, saved eigenvectors used only for v0, independent full-support noise and ncv32 for confirmation. No tolerance relaxation or finite-d12 truth assumption.",
        "fresh_agents_launched": 0, "public_or_evaluator_changes": False,
    })
    try:
        validate_source_equivalence(case)
        history = list(prior["history"])
        for count in (14, 16):
            base, vectors = solve_stage(case, count, 80, 2.0, f"d{count}_f80_w2")
            result["new_stages"].append(base)
            history.append(base)
            changes = [np.abs(np.log(gap_values(history[offset + 1]) / gap_values(history[offset])))
                       for offset in (len(history) - 3, len(history) - 2)]
            result["last_two_cutoff_log_changes"] = [change.tolist() for change in changes]
            write_json(ROOT / "result.json", result)
            if np.max(changes) > 2e-5 or not all(previous_gate.admissible_solve(record, scale) for record in history[-3:]):
                continue
            doubled, doubled_vectors = solve_stage(case, count, 160, 2.0, f"d{count}_f160_w2", vectors)
            result["new_stages"].append(doubled)
            write_json(ROOT / "result.json", result)
            independent, independent_vectors = solve_stage(case, count, 160, 2.34, f"d{count}_f160_w2p34", doubled_vectors)
            result["new_stages"].append(independent)
            doubling_change = np.abs(np.log(gap_values(doubled) / gap_values(base)))
            basis_change = np.abs(np.log(gap_values(independent) / gap_values(doubled)))
            result.update({"doubled_cutoff_log_change": doubling_change.tolist(),
                           "independent_basis_log_change": basis_change.tolist()})
            if max(np.max(doubling_change), np.max(basis_change)) <= 2e-5 and all(
                previous_gate.admissible_solve(record, scale) for record in (doubled, independent)
            ):
                result.update({"accepted": True, "retained_local_states": count,
                               "label": doubled["prediction"], "ground_energy": doubled["ground_energy"],
                               "absolute_sector_energies": doubled["absolute_sector_energies"],
                               "reason": "Original empirical numerical-admission rules plus actual doubled-Fock and changed-frequency eigensolves passed.",
                               "label_scope": "Finite-chain numerically converged Ritz gaps, not a rigorous infinite-Hilbert-space ground-state certificate."})
                write_json(ROOT / "LABEL_ACCEPTED.json", result)
                write_json(ROOT / "result.json", result)
                print("L6_LABEL_ACCEPTED " + json.dumps({"targets": doubled["prediction"]["targets"],
                      "retained_count": count, "elapsed_seconds": time.monotonic() - STARTED}), flush=True)
                del vectors, doubled_vectors, independent_vectors
                result["generation_probes"] = run_controls(case, result["label"])
                break
        if not result["accepted"]:
            result["reason"] = "Required cutoff/basis/residual confirmation was not achieved; no label admitted."
    except (BudgetExceeded, MemoryError, RuntimeError, ValueError, OSError) as error:
        result["bounded_stop_or_error"] = repr(error)
        if not result["accepted"]:
            result["reason"] = "Extended run remains uncertified; no truth or physics-failure claim."
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        result.update({"finished_utc": datetime.now(timezone.utc).isoformat(),
                       "elapsed_seconds": time.monotonic() - STARTED,
                       "cpu_seconds": time.process_time() - cpu_started,
                       "child_cpu_seconds": resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,
                       "peak_rss_mib_process": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                       "all_numerical_jobs_stopped": True,
                       "old_budgeted_runs_and_frozen_files_unchanged": protected_snapshot() == before,
                       "official_30_CPU_batch_score": False,
                       "full_dataset_built": False, "fresh_agents_launched": 0,
                       "hardness_claim": False})
        write_json(ROOT / "result.json", result)
        write_json(ROOT / "FINAL_REPORT.json", result)
        print("FINAL " + json.dumps({"accepted": result["accepted"], "reason": result.get("reason"),
              "targets": result.get("label", {}).get("targets"), "elapsed_seconds": result["elapsed_seconds"],
              "cpu_seconds": result["cpu_seconds"], "old_files_unchanged": result["old_budgeted_runs_and_frozen_files_unchanged"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-probe", type=int)
    arguments = parser.parse_args()
    if arguments.native_probe is not None:
        native_probe(arguments.native_probe)
    else:
        main()
