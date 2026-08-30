"""Trusted launcher/scorer; every archived algorithm runs in an allowlisted sandbox."""

import concurrent.futures
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def load_engine():
    specification = importlib.util.spec_from_file_location("trusted_benchmark_fermion", ROOT / "runtime/workspace/fermion.py")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def sandbox_command(work, target, seconds, profile):
    return ["bwrap", "--die-with-parent", "--unshare-all", "--new-session", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/etc/alternatives", "/etc/alternatives", "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--bind", str(work), "/work",
            "--ro-bind", str(ROOT / "runtime"), "/runtime", "--ro-bind", str(target), "/work/targets.json",
            "--chdir", "/work", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
            "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
            "--setenv", "MKL_NUM_THREADS", "1", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "/usr/bin/python3", "/runtime/worker.py", "--seconds", str(seconds), "--profile", profile]


def run_case(entry, profile, seconds, engine):
    work = ROOT / "runs" / profile / entry["id"]
    work.mkdir(parents=True, exist_ok=False)
    target = ROOT / "inputs" / entry["id"] / "targets.json"
    if profile == "deep":
        previous = ROOT / "runs/broad" / entry["id"] / "result.json"
        previous_score = engine.evaluate_path(previous, target)
        if previous_score["cases"]:
            write_json(work / "resume.json", engine.read_json(previous))
    command = sandbox_command(work, target, seconds, profile)
    started = time.perf_counter()
    with (work / "launcher.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = process.wait(timeout=seconds + 15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
    runtime = time.perf_counter() - started
    score = engine.evaluate_path(work / "result.json", target)
    report_path = work / "report.json"
    report = json.loads(report_path.read_text()) if report_path.is_file() else None
    beam_log = (work / "beam.log").read_text() if (work / "beam.log").exists() else ""
    trace = [{"depth": int(depth), "support": int(support)} for depth, support in re.findall(r" depth (\d+) nodes \d+ support (\d+)", beam_log)]
    method_errors = {}
    for method in ("beam", "continuous_refinement", "bridge"):
        path = work / (method + ".log")
        if path.exists():
            content = path.read_text()
            if "Traceback (most recent call last)" in content or "error while loading shared libraries" in content:
                method_errors[method] = content[-2000:]
    healthy = returncode == 0 and report is not None and bool(score["cases"]) and not method_errors
    result = dict(entry, profile=profile, probe_budget_seconds=seconds, launcher_runtime_seconds=runtime,
                  launcher_returncode=returncode, healthy=healthy, score=score, report=report,
                  beam_support_trace=trace, method_errors=method_errors,
                  work_path=str(work.relative_to(ROOT)), certificate_free_namespace=bool(report and report["namespace"]["certificate_free_allowlist"]))
    write_json(work / "trusted_score.json", result)
    print(json.dumps({"id": entry["id"], "profile": profile, "healthy": healthy,
                      "fidelity": score["core"], "pass": score["pass"], "runtime": runtime,
                      "last_beam_support": trace[-1] if trace else None}), flush=True)
    return result


def select_triple(results, excluded=()):
    groups = {depth: [result for result in results if result["group"] == "pool" and result["max_gates"] == depth
                     and result["healthy"] and not result["score"]["pass"] and result["id"] not in excluded]
              for depth in (24, 28, 32)}
    triples = [triple for triple in itertools.product(*(groups[depth] for depth in (24, 28, 32)))
               if {result["n_electrons"] for result in triple} == {4, 6}]
    if not triples:
        raise RuntimeError("no healthy failing triple covers both number sectors and all depths")
    return min(triples, key=lambda triple: (max(result["score"]["core"] for result in triple),
                                            sum(result["score"]["core"] for result in triple),
                                            tuple(result["id"] for result in triple)))


def main():
    started = time.perf_counter()
    engine = load_engine()
    catalog = json.loads((ROOT / "catalog.json").read_text())["cases"]
    broad = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_case, entry, "broad", 60, engine) for entry in catalog]
        for future in concurrent.futures.as_completed(futures):
            broad.append(future.result())
            write_json(ROOT / "broad_results.json", {"budget_seconds_per_case": 60, "max_parallel_jobs": 4, "results": broad})
    if not all(result["healthy"] for result in broad):
        raise RuntimeError("benchmark infrastructure/method errors; do not select failures from broken probes")
    selected = select_triple(broad)
    write_json(ROOT / "provisional_finalists.json", {"case_ids": [result["case_id"] for result in selected], "selection_basis": "minimize worst best-fidelity, then sum, with sector/depth coverage"})
    print(json.dumps({"deep_finalists": [result["case_id"] for result in selected]}), flush=True)
    deep = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_case, {key: result[key] for key in catalog[0]}, "deep", 300, engine) for result in selected]
        for future in concurrent.futures.as_completed(futures):
            deep.append(future.result())
            write_json(ROOT / "deep_results.json", {"additional_budget_seconds_per_case": 300, "max_parallel_jobs": 3, "results": deep})
    if not all(result["healthy"] and not result["score"]["pass"] for result in deep):
        raise RuntimeError("a finalist passed or a probe failed; explicit further selection is required")
    controls = [result for result in broad if result["group"] == "control"]
    report = {"status": "bounded_benchmark_complete", "broad_budget_seconds_per_case": 60,
              "deep_additional_budget_seconds_per_finalist": 300, "full_one_hour_champion_failure_claimed": False,
              "broad_pool_cases": 18, "old_public_controls": 3, "control_pass_count": sum(result["score"]["pass"] for result in controls),
              "broad": broad, "deep": deep, "selected_case_ids": [result["case_id"] for result in sorted(deep, key=lambda result: result["max_gates"])],
              "runtime_seconds": time.perf_counter() - started,
              "isolation": "bwrap system-library allowlist + sanitized read-only runtime + single public input + per-case writable output; no home/srv/task roots",
              "current_attempts_read": False, "active_generation_one_modified": False}
    write_json(ROOT / "benchmark_report.json", report)
    print(json.dumps({"ready_for_staging": True, "selected_case_ids": report["selected_case_ids"],
                      "control_pass_count": report["control_pass_count"], "runtime_seconds": report["runtime_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
