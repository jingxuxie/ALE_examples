import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def run(command, directory, log_path):
    environment = os.environ.copy()
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[variable] = "1"
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    started = time.perf_counter()
    with log_path.open("w") as stream:
        completed = subprocess.run(command, cwd=directory, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, timeout=120, check=False)
    if completed.returncode:
        raise RuntimeError("standalone command failed: " + str(log_path))
    return time.perf_counter() - started


def main():
    spec = json.loads((ROOT / "evaluator/hidden/assay_spec.json").read_text())
    if "Construction time: one hour" not in (ROOT / "participant/TASK.md").read_text():
        raise AssertionError("missing solver construction budget")
    tests = (ROOT / "adversary/tests.log").read_text()
    if "Ran 23 tests" not in tests or not tests.rstrip().endswith("OK"):
        raise AssertionError("implementation tests have not passed")
    measurements = {}
    for name in ("baseline", "b2_champion", "author", "portfolio_best"):
        report = json.loads((ROOT / ("adversary/" + name + "_report.json")).read_text())
        if not report["valid"] or not report["evaluation_complete"] or report["resource_score"] != 1:
            raise AssertionError("reference evaluation incomplete or inadmissible")
        measurements[name] = dict(valid=report["valid"], passed=report["passed"],
                                  core_score=report["core_score"], worst_family_score=report["worst_family_score"],
                                  successes={family: result["successes"] for family, result in report["robustness_families"].items()},
                                  resource_score=report["resource_score"], runtime_seconds=report["runtime_seconds"],
                                  peak_memory_mib=report["peak_memory_mib"], report="adversary/" + name + "_report.json")
    files = {}
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise AssertionError("symlink in frozen packet")
            if path.is_file() and path.name != "freeze.json":
                files[str(path.relative_to(ROOT))] = digest(path)
    freeze_path = ROOT / "evaluator/hidden/freeze.json"
    freeze = dict(target_id=spec["target_id"], generation=3, final_generation_under_cap=True,
                  frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  nominal_target_sha256=spec["nominal_target_sha256"],
                  hidden_uniforms_sha256=spec["hidden_uniforms_sha256"],
                  assay_spec_sha256=digest(ROOT / "evaluator/hidden/assay_spec.json"),
                  construction_seconds=3600, participant_read_only=True, evaluator_read_only=True,
                  artifact="witness.json at writable work root", files=files,
                  rule="No source, condition, distribution, pool, baseline, or participant changes after freeze; no fresh launch by generation agent.")
    if freeze_path.exists():
        previous = json.loads(freeze_path.read_text())
        if previous["files"] != files:
            raise AssertionError("refusing to revise a frozen packet")
        freeze = previous
    else:
        write_json(freeze_path, freeze)
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in directory.rglob("*"):
            path.chmod(0o555 if path.is_dir() else 0o444)
        directory.chmod(0o555)
    print("FROZEN " + digest(freeze_path), flush=True)
    standalone = ROOT / "adversary/standalone_packet"
    standalone.mkdir(exist_ok=True)
    for name in ("participant", "evaluator"):
        if not (standalone / name).exists():
            shutil.copytree(ROOT / name, standalone / name)
    (standalone / "adversary").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "adversary/draw_provenance.json", standalone / "adversary/draw_provenance.json")
    timings = {}
    timings["baseline_generation_seconds"] = run([sys.executable, "-B", "participant/workspace/baseline.py"], standalone, ROOT / "adversary/standalone_baseline.log")
    timings["public_checker_seconds"] = run([sys.executable, "-B", "participant/workspace/check.py", "witness.json", "--samples", "2", "--seed", "71717", "--report", "public_report.json"], standalone, ROOT / "adversary/standalone_public.log")
    timings["official_evaluation_seconds"] = run([sys.executable, "-B", "evaluator/evaluate.py", "witness.json", "--report", "official_report.json"], standalone, ROOT / "adversary/standalone_official.log")
    timings["independent_test_seconds"] = run([sys.executable, "-B", "evaluator/hidden/test_packet.py"], standalone, ROOT / "adversary/standalone_tests.log")
    standalone_report = json.loads((standalone / "official_report.json").read_text())
    baseline_report = json.loads((ROOT / "adversary/baseline_report.json").read_text())
    for key in ("valid", "passed", "core_score", "worst_family_score", "family_scores", "nominal", "robustness_families", "resource_score"):
        if standalone_report[key] != baseline_report[key]:
            raise AssertionError("standalone baseline mismatch: " + key)
    public = json.loads((standalone / "public_report.json").read_text())
    if not public["valid"] or public["passed"]:
        raise AssertionError("unexpected standalone public baseline result")
    mismatches = [name for name, expected in files.items() if digest(ROOT / name) != expected or digest(standalone / name) != expected]
    if mismatches or list((ROOT / "attempts").iterdir()):
        raise AssertionError("frozen file changed or attempts not empty")
    read_only = all(not path.stat().st_mode & 0o222 for directory in (ROOT / "participant", ROOT / "evaluator") for path in [directory, *directory.rglob("*")])
    if not read_only:
        raise AssertionError("frozen trees are writable")
    passing = [name for name, result in measurements.items() if result["passed"]]
    audit = dict(passed=True, standalone_copy_passed=True, independent_tests=23,
                 standalone_tests=23, timings=timings, frozen_file_count=len(files),
                 frozen_manifest_sha256=digest(freeze_path), frozen_files_unchanged=True,
                 participant_and_evaluator_read_only=read_only, attempts_empty=True,
                 no_fresh_agents_launched=True, no_original_root_edits=True,
                 measurements=measurements, known_passing_references=passing,
                 feasibility="passing reference exists" if passing else "open; no tested reference passes B3",
                 participant_contains_prior_privileged_artifacts=False)
    write_json(ROOT / "adversary/readiness.json", audit)
    status = dict(status="ready_frozen", target_id=spec["target_id"], generation=3,
                  final_generation_under_cap=True, construction_seconds=3600,
                  frozen_manifest_sha256=digest(freeze_path), freeze="evaluator/hidden/freeze.json",
                  ready_for_fresh_launch=True, fresh_launch_owner="main", fresh_attempts=0,
                  attempts_empty=True, participant_read_only=True, evaluator_read_only=True,
                  baseline_admissible=True, known_passing_references=passing,
                  feasibility=audit["feasibility"], readiness_report="adversary/readiness.json",
                  artifact="witness.json", original_root_modified=False)
    write_json(ROOT / "status.json", status)
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == "__main__":
    main()
