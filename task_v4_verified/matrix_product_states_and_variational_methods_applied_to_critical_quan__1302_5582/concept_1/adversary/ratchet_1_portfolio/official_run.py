import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import ast
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest():
    return {str(path.relative_to(HERE / "v1")): {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in sorted((HERE / "v1").rglob("*")) if path.is_file()}


def integrity_check(plan):
    sources = source_manifest()
    assert set(sources) == {"solve.py", "optimizer.py", "core.py", "contractor.py"}
    assert sum(entry["bytes"] for entry in sources.values()) <= 16 * 1024 ** 2
    assert not any(path.is_symlink() for path in (HERE / "v1").rglob("*"))
    imports = set()
    for name in sources:
        text = (HERE / "v1" / name).read_text()
        assert "case_id" not in text
        assert "adversary/" not in text and "evaluator/" not in text and "attempts/" not in text
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
    assert not imports.intersection({"subprocess", "socket", "requests", "multiprocessing"})
    calibration_path = CONCEPT / "evaluator/hidden/calibration.json"
    assert digest(calibration_path) == plan["expected_calibration_sha256"]
    frozen_hashes = json.loads(calibration_path.read_text())["frozen_hashes"]
    for relative, expected in frozen_hashes.items():
        assert digest(CONCEPT / relative) == expected, relative
    published = {name: digest(CONCEPT / "participant/baseline" / name)
                 for name in ("solve.py", "optimizer.py", "mps.py", "contractor.py")}
    for name, expected in published.items():
        assert digest(HERE / "provenance/published_baseline" / name) == expected
    assert digest(HERE / "v1/core.py") == published["optimizer.py"]
    assert digest(HERE / "v1/contractor.py") == published["contractor.py"]
    return {"valid": True, "sources": sources, "imports": sorted(imports),
            "submission_bytes": sum(entry["bytes"] for entry in sources.values()),
            "published_source_hashes": published, "frozen_asset_hashes": frozen_hashes,
            "calibration_sha256": digest(calibration_path), "lookup_artifacts_present": False,
            "fresh_attempt_outputs_read": False}


def main():
    if (HERE / "evaluation_run.json").exists() or (HERE / "evaluation.json").exists():
        raise RuntimeError("The one authorized official evaluation has already been started; no retry")
    plan = json.loads((HERE / "PLAN.json").read_text())
    preflight = json.loads((HERE / "preflight.json").read_text())
    assert "completed_utc" in preflight
    assert all(entry["v1"]["valid"] for entry in preflight["cases"])
    integrity = integrity_check(plan)
    write_json(HERE / "integrity.json", integrity)
    write_json(HERE / "source_hashes.json", integrity["sources"])
    now = datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(plan["started_utc"].replace("Z", "+00:00")) + timedelta(minutes=35)
    remaining = (deadline - now).total_seconds()
    assert remaining > 600, "Insufficient bounded-run time remains for the one full grade"
    command = [sys.executable, "evaluator/evaluate.py", "--submission", str(HERE / "v1"),
               "--output", str(HERE / "evaluation.json")]
    launch = {"started_utc": now.isoformat(), "official_evaluations_started": 1,
              "variants": 1, "retries": 0, "command": command,
              "calibration_sha256": integrity["calibration_sha256"], "source_hashes": integrity["sources"],
              "overall_deadline_utc": deadline.isoformat(), "stdin": "DEVNULL", "status": "running"}
    write_json(HERE / "evaluation_run.json", launch)
    started = time.monotonic()
    timed_out = False
    with (HERE / "evaluation.stdout.log").open("wb") as output, (HERE / "evaluation.stderr.log").open("wb") as error:
        process = subprocess.Popen(command, cwd=CONCEPT, env=os.environ.copy(), stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=error, start_new_session=True)
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            returncode = process.wait(timeout=10)
    unchanged = source_manifest() == integrity["sources"]
    frozen_unchanged = all(digest(CONCEPT / relative) == expected
                           for relative, expected in integrity["frozen_asset_hashes"].items())
    launch.update(completed_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - started,
                  returncode=returncode, overall_timeout=timed_out, sources_unchanged=unchanged,
                  frozen_assets_unchanged=frozen_unchanged, status="complete")
    write_json(HERE / "evaluation_run.json", launch)
    report = json.loads((HERE / "evaluation.json").read_text()) if (HERE / "evaluation.json").exists() else {}
    summary = report.get("summary", {})
    passed = bool(summary.get("passed", False)) and returncode == 0 and unchanged and frozen_unchanged and not timed_out
    stages = [{"case_id": row["case_id"], "family": row["family"], "stage": stage, **result}
              for row in report.get("cases", []) for stage, result in row["stages"].items()]
    write_json(HERE / "stage_resources.json", {"count": len(stages), "stages": stages})
    result = {"status": "verified_achievable" if passed else "single_portfolio_failed_or_unverified",
              "full_passing_general_solver_known": passed, "variants": 1, "official_evaluations": 1,
              "retries": 0, "post_feedback_solver_edits": False, "summary": summary,
              "official_report_status": report.get("status", "complete" if summary else "unavailable"),
              "all_stage_resources_preserved": len(stages) == 16,
              "public_preflight_candidate_all_valid": all(entry["v1"]["valid"] for entry in preflight["cases"]),
              "public_preflight_baseline_invalid_count": sum(not entry["baseline"]["valid"] for entry in preflight["cases"]),
              "sources_unchanged": unchanged, "frozen_assets_unchanged": frozen_unchanged,
              "calibration_sha256": integrity["calibration_sha256"],
              "official_report_sha256": digest(HERE / "evaluation.json") if (HERE / "evaluation.json").exists() else None,
              "modified_paths_scope": "adversary/ratchet_1_portfolio only"}
    write_json(HERE / "portfolio_result.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
