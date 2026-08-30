"""Independent extended control portability audit, strictly outside the frozen packet."""

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
BENCHMARK = ROOT.parent
CONCEPT = BENCHMARK.parents[1]
PACKET = BENCHMARK.parent / "generation_2_packet"
sys.path.insert(0, str(BENCHMARK))

from run_benchmark import load_engine, sandbox_command


def save_texts(files):
    patch = "*** Begin Patch\n"
    for relative, content in files.items():
        path = ROOT / relative
        if path.exists():
            raise RuntimeError("refusing to overwrite extended audit asset: " + relative)
        text = content if isinstance(content, str) else json.dumps(content, indent=2, allow_nan=False) + "\n"
        patch += "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, capture_output=True, check=True)


def frozen_hashes():
    manifest = json.loads((PACKET / "evaluator/private/frozen_manifest.json").read_text())
    checks = {}
    for name, expected in manifest["participant_sha256"].items():
        checks["participant/" + name] = hashlib.sha256((PACKET / "participant" / name).read_bytes()).hexdigest() == expected
    for name, expected in manifest["private_sha256"].items():
        checks["evaluator/private/" + name] = hashlib.sha256((PACKET / "evaluator/private" / name).read_bytes()).hexdigest() == expected
    assert all(checks.values())
    return checks


def prepare():
    files, hashes = {}, {}
    for relative in ("champion/explore.py", "champion/assemble.py", "champion/continuous.py", "champion/refine.py",
                     "champion/bridges.py", "champion/export_data.py", "workspace/fermion.py", "workspace/baseline.py"):
        source = BENCHMARK / "runtime" / relative
        files["runtime/" + relative] = source.read_text()
        hashes[relative] = {"sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source": "previously audited path-only adapted archived source"}
    save_texts(files)
    for name in ("beam", "beam2", "beam3", "model.so"):
        source = CONCEPT / "champions/generation_1" / name
        destination = ROOT / "runtime/champion" / name
        shutil.copyfile(source, destination)
        destination.chmod(0o755)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
        hashes["champion/" + name] = {"sha256": digest, "source": "unmodified completed primary champion binary"}
    save_texts({"provenance.json": {"files": hashes, "algorithms_modified": False,
                                  "archived_checkpoints_solutions_and_seeds_copied": False,
                                  "secondary_completed_source_interfaces_inspected": True,
                                  "secondary_algorithm_used": False}})


def run_control(identifier, engine):
    work = ROOT / "runs" / identifier
    work.mkdir(parents=True, exist_ok=False)
    target = BENCHMARK / "inputs" / ("control_" + identifier) / "targets.json"
    command = sandbox_command(work, target, 580, "extended")
    command = [str(ROOT / "runtime") if part == str(BENCHMARK / "runtime") else part for part in command]
    started = time.perf_counter()
    timed_out = False
    with (work / "launcher.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
    elapsed = time.perf_counter() - started
    score = engine.evaluate_path(work / "result.json", target)
    report = json.loads((work / "report.json").read_text()) if (work / "report.json").exists() else None
    errors = {}
    for path in work.glob("*.log"):
        text = path.read_text()
        if "Traceback (most recent call last)" in text or "error while loading shared libraries" in text:
            errors[path.name] = text[-1800:]
    result = {"case_id": identifier, "outer_budget_seconds": 600, "worker_budget_seconds": 580,
              "runtime_seconds": elapsed, "launcher_returncode": returncode, "outer_timeout": timed_out,
              "healthy": bool(report) and not errors and bool(score["cases"]), "method_errors": errors,
              "score": score, "worker_report": report, "command": command,
              "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "work_path": str(work.relative_to(ROOT))}
    (work / "trusted_score.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"case_id": identifier, "healthy": result["healthy"], "pass": score["pass"],
                      "fidelity": score["core"], "runtime_seconds": elapsed,
                      "phases": [phase["method"] for phase in report["phases"]] if report else []}), flush=True)
    return result


def main():
    started = time.perf_counter()
    before = frozen_hashes()
    prepare()
    engine = load_engine()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_control, identifier, engine) for identifier in ("sector_10_4", "sector_10_6")]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    after = frozen_hashes()
    report = {"status": "extended_controls_complete", "portability_pass": all(result["healthy"] and result["score"]["pass"] for result in results),
              "results": sorted(results, key=lambda result: result["case_id"]), "runtime_seconds": time.perf_counter() - started,
              "budget_seconds_per_control": 600, "parallel_jobs": 2, "frozen_hash_checks_before": before,
              "frozen_hash_checks_after": after, "frozen_packet_modified": False,
              "input_isolation": "system-library allowlist, sanitized archived code/binaries, one public old target, fresh writable workspace; no certificates or archived answers/checkpoints",
              "profile_difference_from_selection_benchmark": "original beam variant width 2000/branches 60, fresh-checkpoint bridges, fresh-beam refinement/pruning, wider beam2 fallback; not the earlier narrow beam3 configuration",
              "full_hour_failure_claimed": False, "new_cases_retested_with_this_extended_profile": False}
    save_texts({"report.json": report})
    print(json.dumps({"portability_pass": report["portability_pass"], "report": str(ROOT / "report.json"),
                      "frozen_packet_hashes_unchanged": all(after.values()), "runtime_seconds": report["runtime_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
