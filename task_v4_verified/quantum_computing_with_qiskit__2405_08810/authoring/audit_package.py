import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL_STATUSES = {"solved", "hard_open_candidate", "hard_verified_achievable", "invalid", "rejected"}


def digest_tree(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"unexpected symlink: {path}")
        if path.is_file() and "__pycache__" not in path.parts:
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def audit(require_final):
    checks = []

    def record(name, passed, detail=None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    modes = []
    attempt_count = 0
    for concept_index in range(1, 4):
        concept = ROOT / f"concept_{concept_index}"
        prefix = concept.name
        required = ["participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json"]
        record(f"{prefix}: package", all((concept / name).exists() for name in required))
        status = json.loads((concept / "status.json").read_text())
        modes.append(status.get("verification_mode", status.get("mode", status.get("task_mode"))))
        if require_final:
            record(f"{prefix}: final decision", status.get("status") in FINAL_STATUSES, status.get("status"))
        record(f"{prefix}: ratchet limit", status.get("ratchet_generations", 0) <= 3)
        public = digest_tree(concept / "participant")
        record(f"{prefix}: no public private paths", not any(any(part in {"hidden", "champions", "adversary", "attempts", "auth.json"} for part in Path(name).parts) for name in public))
        runs = sorted((concept / "adversary" / "tournament").glob("v_*/run.json"))
        record(f"{prefix}: fresh tournament exists", bool(runs))
        for run_path in runs:
            attempt_count += 1
            run = json.loads(run_path.read_text())
            label = f"{prefix}/{run_path.parent.name}"
            record(f"{label}: isolated runner", run.get("model") == "ultima-alpha" and run.get("limit_seconds") == 3600 and all(run.get(key) is True for key in ("initial_output_empty", "fresh_runtime", "task_read_only")))
            finished = "returncode" in run
            if require_final or finished:
                record(f"{label}: complete", finished)
                record(f"{label}: participant unchanged", run.get("participant_unchanged") is True)
                record(f"{label}: one-hour deadline", run.get("elapsed_seconds", float("inf")) <= 3611)
            frozen_public = json.loads((run_path.parent / "participant_sha256.json").read_text())
            generation = run["generation"] - 1
            archived = concept / "adversary" / "generations" / f"generation_{generation}" / "participant"
            comparison = digest_tree(archived) if archived.is_dir() else public
            record(f"{label}: public assets preserved", frozen_public == comparison)
            score_path = concept / "adversary" / "scored" / run_path.parent.name / "score.json"
            if score_path.exists():
                score = json.loads(score_path.read_text())
                record(f"{label}: score schema", all(key in score for key in ("core_score", "worst_family_score", "resource_score", "valid", "passed", "reason")))
                record(f"{label}: scientific evaluation valid", score.get("valid") is True, score.get("reason"))
                snapshot = score_path.parent / "submission"
                original = concept / "attempts" / run_path.parent.name
                preserved = digest_tree(snapshot)
                current = digest_tree(original)
                record(f"{label}: scored snapshot preserved", all(current.get(name) == value for name, value in preserved.items()))
            elif require_final:
                record(f"{label}: evaluated", False)
    record("three distinct verification modes", len(set(modes)) == 3, modes)
    credentials = [str(path.relative_to(ROOT)) for path in (ROOT / "authoring").rglob("auth.json") if path.is_file()]
    if require_final:
        record("temporary credentials removed", not credentials, credentials)
    result = {"audited_at_utc": datetime.now(timezone.utc).isoformat(), "require_final": require_final, "fresh_attempts": attempt_count, "passed": all(item["passed"] for item in checks), "checks": checks}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-final", action="store_true")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = audit(options.require_final)
    if options.output:
        options.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks": len(result["checks"]), "fresh_attempts": result["fresh_attempts"], "failed": [item for item in result["checks"] if not item["passed"]]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
