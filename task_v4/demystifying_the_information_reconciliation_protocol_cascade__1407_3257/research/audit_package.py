import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def manifest(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError(f"symlink in frozen assets: {path}")
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def audit():
    checks = []
    concepts = []
    for concept_number in (1, 2, 3):
        concept = ROOT / f"concept_{concept_number}"
        status = json.loads((concept / "status.json").read_text())
        required = ("participant/TASK.md", "participant/input", "participant/workspace",
                    "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden",
                    "attempts", "champions", "adversary", "status.json")
        missing = [relative for relative in required if not (concept / relative).exists()]
        concepts.append({"concept": concept_number, "mode": status["verification_mode"],
                         "status": status["status"], "missing": missing})
        for evidence in sorted((concept / "attempts").glob("v_*_evidence")):
            frozen = json.loads((evidence / "frozen_manifest.json").read_text())
            launch = json.loads((evidence / "launch.json").read_text())
            candidates = (concept, concept / "champions" / f"generation_{launch['generation']}")
            matches = []
            for candidate in candidates:
                if all(manifest(candidate / area) == contents for area, contents in frozen.items()):
                    matches.append(str(candidate.relative_to(ROOT)))
            complete = "participant_unchanged" in launch
            score_path = evidence / "score.json"
            score = json.loads(score_path.read_text()) if score_path.exists() else None
            conditions = {
                "frozen_assets_match": bool(matches),
                "complete": complete,
                "participant_unchanged": launch.get("participant_unchanged") is True,
                "output_initially_empty": launch.get("output_initially_empty") is True,
                "task_read_only": launch.get("task_read_only") is True,
                "requested_model": launch.get("model") == "ultima-alpha",
                "one_hour_limit": launch.get("limit_seconds") == 3600,
                "within_termination_grace": complete and launch.get("elapsed_seconds", 3617) <= 3616,
                "scored": score is not None,
            }
            checks.append({"concept": concept_number, "attempt": evidence.name,
                           "generation": launch["generation"], "reference_matches": matches,
                           "checks": conditions, "passed": all(conditions.values()),
                           "score_file": str(score_path.relative_to(ROOT)) if score is not None else None})
    accepted = {"solved", "hard_open_candidate", "hard_verified_achievable", "invalid", "rejected"}
    complete = all(item["status"] in accepted and not item["missing"] for item in concepts)
    modes = {item["mode"] for item in concepts}
    passed = complete and len(modes) == 3 and all(item["passed"] for item in checks)
    return {"passed": passed, "concepts": concepts, "fresh_attempts": len(checks), "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = audit()
    encoded = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded, end="")
    raise SystemExit(0 if result["passed"] else 1)
