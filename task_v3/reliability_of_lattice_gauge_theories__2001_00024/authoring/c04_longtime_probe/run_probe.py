import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[1]
PILOT = TASK / "pilots/c04_colored_noise"
REFERENCE = PILOT / "private/reference/longtime"
sys.path.insert(0, str(REFERENCE))
sys.path.insert(1, str(PILOT / "private"))
sys.path.insert(2, str(TASK / "authoring"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    paths = list((PILOT / "participant").rglob("*"))
    paths += list((PILOT / "private/challenge_pool").rglob("*"))
    paths += list((PILOT / "attempt").glob("*.py"))
    paths += list((PILOT / "private/reference").glob("*.py"))
    paths += [PILOT / "private/evaluator.py", PILOT / "private/scoring.py", PILOT / "private/freeze.json"]
    return {str(path.relative_to(TASK)): digest(path) for path in paths
            if path.is_file() and "__pycache__" not in path.parts}


def stage():
    shutil.copyfile(PILOT / "private/reference/engine.py", REFERENCE / "engine.py")
    destination = HERE / "original_submission"
    destination.mkdir(exist_ok=True)
    shutil.copyfile(PILOT / "attempt/solver.py", destination / "solver.py")
    write_json(HERE / "source_hashes.json", dict(
        original_solver=digest(PILOT / "attempt/solver.py"), staged_solver=digest(destination / "solver.py"),
        original_engine=digest(PILOT / "private/reference/engine.py"), staged_engine=digest(REFERENCE / "engine.py")))


def load_base(identifier):
    return json.loads((PILOT / "private/challenge_pool/screening" / (identifier + ".json")).read_text())["case"]


def build_cases():
    import numpy as np
    import engine

    specifications = [
        ("weak_pink_T1000", "1b74c29e8a9a", 1000.0, 1, 2.5e-5, 0.45, 48001),
        ("weak_brown_T10000", "c2ec672ca1ab", 10000.0, 2, 1.5e-5, 0.65, 48002),
    ]
    for name, base_identifier, final_time, beta, amplitude, eta, seed in specifications:
        case = load_base(base_identifier)
        case["case_id"] = name
        case["times"] = np.linspace(0, final_time, 7).tolist()
        case["model"]["lambda"] = float(np.sqrt(2.6 / final_time))
        case["model"]["kappa"] = 0.0
        bath = dict(beta=beta, amplitude=amplitude, cutoff=0.45, floor=0.0, eta=eta)
        random = np.random.default_rng(seed)
        for row in case["calibration"]:
            mean = float(engine.calibration_rates(bath, [row])[0])
            row["sigma"] = max(1e-11, 0.008 * abs(mean))
            row["value"] = float(mean + row["sigma"] * random.normal())
        assert 1e-5 <= amplitude <= 0.12 and 0.12 <= bath["cutoff"] <= 1.2
        assert 0 <= bath["floor"] <= 0.02 and 0 <= eta <= 1
        assert np.all(np.diff(case["times"]) > 0) and np.allclose(np.diff(case["times"]), final_time / 6)
        write_json(HERE / "cases" / (name + ".json"), case)
        write_json(HERE / "case_metadata" / (name + ".json"), dict(
            base_case_id=base_identifier, generating_bath=bath, calibration_seed=seed,
            final_time=final_time, lambda_value=case["model"]["lambda"],
            coherent_drift_scale=2.6 / case["model"]["lambda"]**2,
            incoherent_scaling_indicator=amplitude * final_time / 2.6**beta,
            public_bounds_valid=True, hilbert_dimension=64, time_count=7,
            changed_fields=["case_id", "times", "model.lambda", "model.kappa", "calibration.value", "calibration.sigma"]))


def comparison(case, actual, expected):
    import numpy as np
    from scoring import FLOORS, prediction_array, score_result

    scored = score_result(case, actual, dict(reference=expected, anchors=FLOORS))
    scored["normalization"] = "Public anchor-floor lower bound; no late weak baseline is presumed"
    scored["max_observable_error"] = float(max(
        np.max(np.abs(prediction_array(actual["predictions"][identifier], len(case["times"]))
                      - prediction_array(expected["predictions"][identifier], len(case["times"]))))
        for identifier in expected["predictions"]))
    return scored


def closed_control(case):
    import numpy as np
    import engine

    operators = engine.build_model(case)
    action = next(action for action in case["actions"] if action["id"] == "flat_high")
    energies, basis = np.linalg.eigh(engine.hamiltonian(case, operators, action))
    initial = operators["initial"]
    states = basis @ (np.exp(-1j * np.outer(energies, case["times"])) * (basis.conj().T @ initial)[:, None])
    ideal_energies, ideal_basis = np.linalg.eigh(operators["hzero"])
    ideal = ideal_basis @ (np.exp(-1j * np.outer(ideal_energies, case["times"])) * (ideal_basis.conj().T @ initial)[:, None])
    return dict(action="flat_high", role="Closed-system diagnostic, not an additional scored case",
                gauge=np.einsum("it,ij,jt->t", states.conj(), operators["gauge"], states).real.tolist(),
                fidelity=(np.abs(np.sum(ideal.conj() * states, axis=0))**2).tolist())


def precompute():
    import numpy as np
    import engine
    from accelerated import solve_detailed

    validations = []
    short_cases = [load_base(identifier) for identifier in ("db807062bda9", "1b74c29e8a9a", "c2ec672ca1ab")]
    for path in sorted((HERE / "cases").glob("*.json")):
        short = json.loads(path.read_text())
        short["case_id"] += "_short_control"
        short["times"] = np.linspace(0, 4.0, 7).tolist()
        short_cases.append(short)
    for case in short_cases:
        timer = time.perf_counter()
        original = engine.solve(case)
        accelerated, diagnostics, _ = solve_detailed(case)
        scored = comparison(case, accelerated, original)
        if scored["core"] < 0.999 or scored["max_observable_error"] > 2e-8:
            raise ArithmeticError("short-time agreement failed")
        validations.append(dict(case_id=case["case_id"], seconds=time.perf_counter() - timer,
                                comparison=scored, diagnostics=diagnostics))
        print("short validated", case["case_id"], scored["max_observable_error"], flush=True)
    write_json(HERE / "short_reference_checks.json", validations)
    for path in sorted((HERE / "cases").glob("*.json")):
        case = json.loads(path.read_text())
        timer = time.perf_counter()
        target, exact_diagnostics, exact_states = solve_detailed(case, method="centered_expm")
        exact_seconds = time.perf_counter() - timer
        timer = time.perf_counter()
        fast, fast_diagnostics, fast_states = solve_detailed(case, method="commuting_eigh")
        fast_seconds = time.perf_counter() - timer
        scored = comparison(case, fast, target)
        state_error = float(max(np.max(np.abs(fast_states[identifier] - exact_states[identifier])) for identifier in exact_states))
        if scored["core"] < 0.999 or scored["max_observable_error"] > 2e-8 or state_error > 2e-8:
            raise ArithmeticError("independent late-time propagation agreement failed")
        write_json(HERE / "labels" / path.name, dict(
            reference=target, normalization="Anchor-floor lower bounds only; no frozen-pool score",
            centered_expm_seconds=exact_seconds, commuting_eigh_seconds=fast_seconds,
            cross_method_comparison=scored, max_density_entry_difference=state_error,
            centered_expm_diagnostics=exact_diagnostics, commuting_eigh_diagnostics=fast_diagnostics,
            closed_system_control=closed_control(case)))
        print("late reference validated", case["case_id"], "seconds", exact_seconds, fast_seconds,
              "observable error", scored["max_observable_error"], flush=True)


def process_snapshot():
    ticks = os.sysconf("SC_CLK_TCK")
    page_kib = os.sysconf("SC_PAGE_SIZE") / 1024
    pending = [os.getpid()]
    visited, records = set(), []
    while pending:
        parent = pending.pop()
        if parent in visited:
            continue
        visited.add(parent)
        try:
            children = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
        except (OSError, ProcessLookupError):
            continue
        for child in map(int, children):
            pending.append(child)
            try:
                raw = Path(f"/proc/{child}/stat").read_text()
                fields = raw[raw.rfind(")") + 2:].split()
                command = Path(f"/proc/{child}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
                records.append(dict(pid=child, parent_pid=int(fields[1]), state=fields[0],
                                    cpu_seconds=(int(fields[11]) + int(fields[12])) / ticks,
                                    rss_kib=int(fields[21]) * page_kib, command=command))
            except (OSError, ValueError, ProcessLookupError):
                continue
    return records


def run_monitored(submission, case, report_path, startup_grace):
    from isolated_eval import run_solver

    stopped = threading.Event()
    samples = []
    started = time.monotonic()

    def monitor():
        while not stopped.is_set():
            samples.append(dict(elapsed=time.monotonic() - started, processes=process_snapshot()))
            stopped.wait(0.2)

    watcher = threading.Thread(target=monitor, daemon=True)
    watcher.start()
    try:
        execution = run_solver(submission, PILOT / "participant", case, timeout=60, memory_gib=6,
                               startup_grace=startup_grace)
    except Exception as exception:
        execution = dict(ok=False, infrastructure_failure=True, error=repr(exception), seconds=time.monotonic() - started)
    finally:
        stopped.set()
        watcher.join()
    process_maxima = {}
    for sample in samples:
        for process in sample["processes"]:
            previous = process_maxima.get(str(process["pid"]))
            if previous is None or process["cpu_seconds"] >= previous["cpu_seconds"]:
                process_maxima[str(process["pid"])] = process
    cpu_evidence = dict(sample_interval_seconds=0.2,
                        observed_process_cpu_seconds=sum(process["cpu_seconds"] for process in process_maxima.values()),
                        maxima=process_maxima, samples=samples)
    write_json(report_path.with_name(report_path.stem + "_cpu.json"), cpu_evidence)
    result = execution.pop("result", None)
    if result is not None:
        write_json(report_path.with_name(report_path.stem + "_output.json"), result)
    execution["observed_process_cpu_seconds"] = cpu_evidence["observed_process_cpu_seconds"]
    execution["budget"] = dict(worker_wall_seconds=60, worker_cpu_soft_seconds=61,
                               worker_cpu_hard_seconds=62, startup_grace_seconds=startup_grace,
                               parent_watchdog_seconds=60 + startup_grace, memory_gib=6)
    execution["isolation_api_sha256"] = digest(TASK / "authoring/isolated_eval.py")
    execution["isolation_worker_sha256"] = digest(TASK / "authoring/eval_worker.py")
    if execution.get("ok"):
        label = json.loads((HERE / "labels" / (case["case_id"] + ".json")).read_text())
        execution["comparison"] = comparison(case, result, label["reference"])
    else:
        execution["protocol_core_score"] = 0.0
        execution["failure_class"] = "infrastructure" if execution.get("infrastructure_failure") else (
            ("worker_wall_timeout" if "worker" in execution.get("error", "") else "parent_watchdog_timeout")
            if execution.get("timeout") else "execution_or_schema")
    write_json(report_path, execution)
    print(report_path.name, "ok", execution["ok"], "seconds", execution.get("seconds"),
          "cpu", execution["observed_process_cpu_seconds"], "score", execution.get("comparison", {}).get("core"), flush=True)
    return execution


def evaluate(startup_grace):
    run_directory = HERE / "runs" / f"strict_worker60_grace{startup_grace}"
    for path in sorted((HERE / "cases").glob("*.json")):
        case = json.loads(path.read_text())
        reference_report = run_directory / (case["case_id"] + "_reference.json")
        reference = run_monitored(REFERENCE, case, reference_report, startup_grace)
        if not reference.get("ok") or reference["comparison"]["core"] <= 0.9:
            raise RuntimeError("isolated efficient reference failed; not testing candidate against invalid target")
        run_monitored(HERE / "original_submission", case,
                      run_directory / (case["case_id"] + "_original.json"), startup_grace)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("prepare", "evaluate", "all"), default="all")
    parser.add_argument("--startup-grace", type=int, default=30)
    arguments = parser.parse_args()
    before = protected_hashes()
    write_json(HERE / "protected_before.json", before)
    if arguments.phase in ("prepare", "all"):
        stage()
        build_cases()
        precompute()
    if arguments.phase in ("evaluate", "all"):
        evaluate(arguments.startup_grace)
    after = protected_hashes()
    write_json(HERE / "protected_integrity.json", dict(unchanged=before == after, hashes=after))
    if before != after:
        raise RuntimeError("protected original artifact hashes changed")
