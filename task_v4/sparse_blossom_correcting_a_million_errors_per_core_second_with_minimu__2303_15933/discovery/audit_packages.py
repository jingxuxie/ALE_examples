import argparse
import json
from pathlib import Path

from run_attempt import inventory


def audit_generation(generation):
    required = [
        "participant/TASK.md", "participant/input", "participant/workspace",
        "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions",
        "adversary", "status.json",
    ]
    missing = [name for name in required if not (generation / name).exists()]
    participant = generation / "participant"
    escaping_links = []
    for path in participant.rglob("*"):
        if path.is_symlink():
            try:
                path.resolve().relative_to(participant.resolve())
            except ValueError:
                escaping_links.append(str(path.relative_to(participant)))
    attempts = []
    for launch_path in sorted((generation / "attempts").glob("v_*_logs/launch.json")):
        launch = json.loads(launch_path.read_text())
        if "finished" not in launch:
            continue
        attempt_name = launch_path.parent.name.removesuffix("_logs")
        attempt_path = generation / "attempts" / attempt_name
        if "stdin_infrastructure" in attempt_name:
            continue
        freeze_path = launch_path.parent / "freeze.json"
        freeze = json.loads(freeze_path.read_text())
        audit_path = generation / "attempts" / (attempt_name + "_evaluation_audit.json")
        metrics_path = generation / "attempts" / (attempt_name + "_result.json")
        evaluation = json.loads(audit_path.read_text()) if audit_path.exists() else {}
        metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
        attempts.append({
            "attempt": attempt_name,
            "submission_code_isolation_required": "concept_2" not in generation.parts,
            "finished": launch["finished"],
            "elapsed_seconds": launch["elapsed_seconds"],
            "timed_out": launch["timed_out"],
            "participant_unchanged_at_exit": launch["participant_unchanged"],
            "participant_matches_launch_freeze": inventory(participant) == freeze["participant_sha256"],
            "evaluator_matches_launch_freeze": inventory(generation / "evaluator") == freeze["evaluator_sha256"],
            "output_empty_at_launch": freeze["output_empty_at_launch"],
            "model": freeze["model"],
            "limit_seconds": freeze["limit_seconds"],
            "original_submission_unchanged": inventory(attempt_path) == launch["submission_sha256"],
            "freeze_keys": sorted(freeze),
            "evaluation_report_present": bool(metrics),
            "evaluation_isolation_audit_present": bool(evaluation),
            "evaluation_preserved_original": evaluation.get("original_unchanged_after_evaluation"),
            "valid": metrics.get("valid"),
            "passed": metrics.get("passed"),
        })
    return {
        "path": str(generation),
        "required_assets_present": not missing,
        "missing": missing,
        "participant_escaping_symlinks": escaping_links,
        "completed_attempts": attempts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    generations = []
    for concept in sorted(root.glob("concept_[123]")):
        generations.append(audit_generation(concept))
        for generation in sorted((concept / "generations").glob("generation_*")):
            generations.append(audit_generation(generation))
    report = {"concept_count": 3, "generations": generations}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"concept_count": 3, "generation_count": len(generations),
                      "missing_assets": sum(len(item["missing"]) for item in generations),
                      "escaping_links": sum(len(item["participant_escaping_symlinks"]) for item in generations)}, indent=2))


if __name__ == "__main__":
    main()
