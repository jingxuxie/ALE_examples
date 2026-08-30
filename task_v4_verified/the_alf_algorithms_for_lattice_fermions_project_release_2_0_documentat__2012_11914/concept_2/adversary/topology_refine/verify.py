import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "adversary/exact_refine"
PROTECTED = (
    "participant",
    "evaluator",
    "status.json",
    "champions/generation_1",
    "adversary/generations/generation_1",
    "adversary/exact_refine",
)


def save(name, payload):
    (HERE / name).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot():
    hashes = {}
    for relative in PROTECTED:
        root = ROOT / relative
        if not root.exists():
            raise FileNotFoundError(root)
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if path.is_file():
                hashes[str(path.relative_to(ROOT))] = digest(path.read_bytes())
    return dict(sorted(hashes.items()))


def main():
    before = snapshot()
    save("protected_before.json", before)
    old_snapshot = json.loads((SOURCE / "protected_before.json").read_text())
    current_contract = {
        name: value for name, value in before.items()
        if name.startswith(("participant/", "evaluator/"))
    }
    previous_search = json.loads((SOURCE / "order_search_summary.json").read_text())
    original_report = json.loads((SOURCE / "refined_official_report.json").read_text())
    raw = (SOURCE / "refined_submission.json").read_bytes()
    (HERE / "submission.json").write_bytes(raw)
    command = [
        sys.executable, "-B", "evaluator/evaluate.py",
        "--submission", "adversary/topology_refine/submission.json",
        "--output", "adversary/topology_refine/official_report.json",
    ]
    environment = dict(os.environ)
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    })
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True,
        text=True, timeout=180,
    )
    elapsed = time.monotonic() - started
    child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    (HERE / "official_stdout.json").write_text(completed.stdout)
    (HERE / "official_stderr.log").write_text(completed.stderr)
    after = snapshot()
    save("protected_after.json", after)
    changed = sorted(
        name for name in before.keys() | after.keys()
        if before.get(name) != after.get(name)
    )
    protection = {
        "protected_roots": list(PROTECTED),
        "protected_file_count": len(before),
        "protected_files_unchanged": before == after,
        "changed_paths": changed,
        "matches_original_contract_snapshot": current_contract == old_snapshot,
        "manifest_sha256": digest(json.dumps(before, sort_keys=True).encode()),
        "submission_sha256": digest(raw),
        "submission_copy_identical": (HERE / "submission.json").read_bytes() == raw,
        "source_submission_unchanged": (SOURCE / "refined_submission.json").read_bytes() == raw,
    }
    save("protection_check.json", protection)
    report = json.loads((HERE / "official_report.json").read_text())
    summary = {
        "purpose": "private privileged feasibility, not fresh-agent hardness evidence",
        "source_artifact": "adversary/exact_refine/refined_submission.json",
        "source_search": "adversary/exact_refine/order_search_summary.json",
        "source_search_completed_before_new_search": True,
        "fresh_v2_output_inspected": False,
        "new_optimization_cpu_budget_seconds": 900,
        "new_optimization_cpu_seconds": 0.0,
        "previous_aggregate_optimization_cpu_seconds": previous_search["aggregate_optimization_cpu_seconds"],
        "previous_word_candidates_scanned": previous_search["word_candidates_scanned"],
        "previous_search_stop": previous_search["stop"],
        "gradient_checks": previous_search["gradient_checks"],
        "validation_wall_seconds": elapsed,
        "validation_cpu_seconds": (
            child_after.ru_utime + child_after.ru_stime
            - child_before.ru_utime - child_before.ru_stime
        ),
        "official_exit_code": completed.returncode,
        "official_command": command,
        "official_validation": report,
        "score_deltas_from_previous_validation": {
            key: report[key] - original_report[key]
            for key in ("core_score", "worst_family_score", "max_point_ratio")
        },
        "protection": protection,
    }
    save("summary.json", summary)
    assert completed.returncode == 0, completed.stderr
    assert protection["protected_files_unchanged"], changed
    assert protection["matches_original_contract_snapshot"]
    assert protection["submission_copy_identical"]
    assert protection["source_submission_unchanged"]
    assert report["valid"] and report["passed"], report
    print(json.dumps({
        "valid": report["valid"],
        "passed": report["passed"],
        "core_score": report["core_score"],
        "worst_family_score": report["worst_family_score"],
        "max_point_ratio": report["max_point_ratio"],
        "validation_cpu_seconds": summary["validation_cpu_seconds"],
        "protection": protection,
    }, indent=2))


if __name__ == "__main__":
    main()
