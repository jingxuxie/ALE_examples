import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
POOL = ROOT / "private/challenge_pool/postpilot"
PRIVATE_REFERENCE = ROOT / "private/reference"
TASK = ROOT.parents[1]
sys.path.insert(0, str(PRIVATE_REFERENCE))
sys.path.insert(0, str(ROOT / "private"))
sys.path.insert(0, str(TASK / "research"))

from official import compile_case, stim
from build import hgp_circuit, instrument, make_case
from metrics import compare
from isolation import run_submission

CPU_BUDGET = 8
MEMORY_MB = 1536


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def load(path):
    return json.loads(path.read_text())


def reference_run(case_path, label):
    output = AUDIT / f"{label}.reference.answer.json"
    usage = AUDIT / f"{label}.reference.usage.json"
    command = ["/usr/bin/time", "-f", '{"max_rss_kb":%M,"user_seconds":%U,"system_seconds":%S}',
               "-o", str(usage), "/usr/bin/python3", str(PRIVATE_REFERENCE / "official.py"),
               "--input", str(case_path), "--output", str(output)]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.update(PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1",
                       OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_BUDGET, CPU_BUDGET))
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_MB * 1024**2, MEMORY_MB * 1024**2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.perf_counter()
    process = subprocess.run(command, env=environment, capture_output=True, text=True,
                             timeout=120, preexec_fn=limits)
    result = {"returncode": process.returncode, "wall_seconds": time.perf_counter() - started,
              "stderr": process.stderr[-3000:]}
    if usage.exists():
        result.update(json.loads(usage.read_text().splitlines()[-1]))
        result["cpu_seconds"] = result["user_seconds"] + result["system_seconds"]
    result["feasible"] = process.returncode == 0 and result.get("cpu_seconds", float("inf")) <= CPU_BUDGET
    if process.returncode == 0:
        result.update(compare(load(output), load(case_path.with_suffix(".answer.json"))))
    return result


def candidate_run(submission, case_path, label):
    result = run_submission(submission, ROOT / "participant", case_path,
                            output_suffix=".json", timeout=120, memory_mb=MEMORY_MB,
                            cpu_limit=CPU_BUDGET)
    answer_bytes = result.pop("answer_bytes")
    result["cpu_seconds"] = result.get("user_seconds", 0) + result.get("system_seconds", 0)
    if answer_bytes is not None:
        (AUDIT / f"{label}.candidate.answer.json").write_bytes(answer_bytes)
        result.update(compare(json.loads(answer_bytes), load(case_path.with_suffix(".answer.json"))))
    else:
        result.update(quality=0, exact=False)
    for line in result["stderr"].splitlines():
        if line.startswith('{"profile":'):
            result.update(json.loads(line))
    return result


def build_regime(name, source, provenance):
    case, statistics = make_case(name, instrument(source), provenance)
    case_path = POOL / f"{name}.json"
    case_path.write_text(json.dumps(case, separators=(",", ":")) + "\n")
    start_cpu = time.process_time()
    answer, wrapper_metrics, circuit, model = compile_case(case)
    statistics["precompute_cpu_seconds"] = time.process_time() - start_cpu
    statistics["wrapper_metrics_wall"] = wrapper_metrics
    case_path.with_suffix(".answer.json").write_text(json.dumps(answer, separators=(",", ":")) + "\n")
    (POOL / f"{name}.stim").write_text(str(circuit))
    (POOL / f"{name}.dem").write_text(str(model))
    start_cpu = time.process_time()
    native = circuit.detector_error_model(decompose_errors=False, flatten_loops=True,
                                         allow_gauge_detectors=False, approximate_disjoint_errors=False)
    statistics["native_compile_cpu_seconds"] = time.process_time() - start_cpu
    statistics["reference_terms"] = len(answer["errors"])
    statistics["input_bytes"] = case_path.stat().st_size
    statistics["answer_bytes"] = case_path.with_suffix(".answer.json").stat().st_size
    statistics["native_recompile_matches"] = str(native) == str(model)
    statistics["noiseless_check"] = not circuit.without_noise().compile_detector_sampler(seed=319).sample(
        8, append_observables=True).any()
    save(AUDIT / f"{name}.statistics.json", statistics)
    return case_path, statistics


def main():
    POOL.mkdir(parents=True, exist_ok=True)
    submission = AUDIT / "submission_snapshot"
    submission.mkdir(exist_ok=True)
    source_path = ROOT / "attempt/solve.py"
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    shutil.copyfile(source_path, submission / "solve.py")
    shutil.copyfile(source_path, AUDIT / "profile_submission/candidate.py")
    report = {"submission_sha256": source_hash, "cpu_budget_seconds": CPU_BUDGET,
              "memory_mb": MEMORY_MB, "wall_allowance_seconds": 120,
              "scientific_regime_count": 2, "small_case_profiles": [], "regimes": []}
    small_case = ROOT / "private/challenge_pool/surface_d7_r8.json"
    for repetition in range(3):
        label = f"small_profile_{repetition}"
        result = candidate_run(AUDIT / "profile_submission", small_case, label)
        report["small_case_profiles"].append(result)
        save(AUDIT / "report.json", report)
        print(json.dumps({"label": label, **result}), flush=True)
    source = stim.Circuit.generated("surface_code:rotated_memory_z", distance=7, rounds=512)
    surface = build_regime("surface_d7_r512", source, {"family": "surface", "distance": 7,
                           "rounds": 512, "source": "Stim 1.16.0 Circuit.generated rotated_memory_z"})
    del source
    source, provenance = hgp_circuit(4, 7, 5, 8, 128, 613)
    hgp = build_regime("hgp_n76_r128", source, provenance)
    del source
    for case_path, statistics in (surface, hgp):
        name = statistics["case_id"]
        reference = reference_run(case_path, name)
        candidate = candidate_run(submission, case_path, name)
        substantive_failure = (reference["feasible"] and reference.get("exact", False)
                               and (not candidate["exact"] or candidate["cpu_seconds"] > CPU_BUDGET))
        report["regimes"].append({"statistics": statistics, "reference": reference,
                                 "candidate": candidate, "substantive_counterexample": substantive_failure})
        save(AUDIT / "report.json", report)
        print(json.dumps(report["regimes"][-1]), flush=True)
    report["submission_unchanged"] = hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
    report["verified_counterexamples"] = sum(case["substantive_counterexample"] for case in report["regimes"])
    report["recommendation"] = "discard ratchet" if not report["verified_counterexamples"] else "review counterexample"
    save(AUDIT / "report.json", report)


if __name__ == "__main__":
    main()
