import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    records = []
    errors = []
    for pilot in sorted((ROOT / "pilots").iterdir()):
        launch = json.loads((pilot / "private/runs/initial/launch.json").read_text())
        missing = [name for name in ("participant/TASK.md", "participant/input", "participant/workspace", "private/reference", "private/challenge_pool", "private/evaluator.py", "attempt/solve.py") if not (pilot / name).exists()]
        changed_public = [name for name, expected in launch["participant_sha256"].items() if not (pilot / "participant" / name).exists() or digest(pilot / "participant" / name) != expected]
        changed_attempt = [name for name, expected in launch["attempt_sha256"].items() if not (pilot / "attempt" / name).exists() or digest(pilot / "attempt" / name) != expected]
        mission = (pilot / "participant/TASK.md").read_text().lower()
        paper_mentioned = any(term in mission for term in ("arxiv", "1903.06168", "enhanced proximity effect", "paper"))
        record = {
            "pilot": pilot.name,
            "missing_roles": missing,
            "changed_public_files": changed_public,
            "changed_attempt_files": changed_attempt,
            "paper_mentioned_in_mission": paper_mentioned,
            "fresh_run_completed": launch["status"] == "completed" and launch["returncode"] == 0,
            "fresh_run_within_limit": launch["elapsed_seconds"] <= launch["limit_seconds"],
        }
        records.append(record)
        if missing or changed_public or changed_attempt or paper_mentioned or not record["fresh_run_completed"] or not record["fresh_run_within_limit"]:
            errors.append(pilot.name)
    parsed = []
    for path in sorted((ROOT / "author_tools").glob("*.py")):
        ast.parse(path.read_text(), filename=str(path))
        parsed.append(str(path.relative_to(ROOT)))
    credential_filenames = [str(path.relative_to(ROOT)) for pattern in ("auth.json", "credentials.json", ".env") for path in ROOT.rglob(pattern) if path.is_file()]
    report = {
        "passed": len(records) == 4 and not errors and not credential_filenames,
        "initial_concept_count": len(records),
        "records": records,
        "author_tools_syntax_checked": parsed,
        "credential_named_files": credential_filenames,
        "credential_check_scope": "Filename audit only; not a claim that arbitrary secret contents were exhaustively scanned",
        "note": "Hashes compare the original fresh-run manifests; bytecode caches are outside those manifests. This validates artifact integrity, not scientific hardness.",
    }
    (ROOT / "artifact_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
