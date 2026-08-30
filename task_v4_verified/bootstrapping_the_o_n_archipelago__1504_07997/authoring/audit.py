import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline",
            "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json")


def main():
    reports = {}
    for concept in sorted(ROOT.glob("concept_*")):
        if not concept.is_dir():
            continue
        missing = [relative for relative in REQUIRED if not (concept / relative).exists()]
        participant_links = [str(path.relative_to(concept)) for path in (concept / "participant").rglob("*")
                             if path.is_symlink()]
        attempts = []
        for source in sorted((concept / "attempts").glob("v_*.metadata.json")):
            metadata = json.loads(source.read_text())
            finished = metadata.get("status") in ("finished", "time_limit")
            invariants = {
                "correct_model": metadata.get("model") == "ultima-alpha",
                "one_hour_limit": metadata.get("time_limit_seconds") == 3600,
                "initially_empty": metadata.get("output_empty_at_start") is True,
                "participant_read_only": metadata.get("participant_access") == "read-only",
                "no_privileged_mounts": metadata.get("privileged_mounts") == [],
                "network_disabled": metadata.get("network") == "disabled",
            }
            if finished:
                for name in ("participant_unchanged", "evaluator_unchanged", "frozen_matches_submission"):
                    invariants[name] = metadata.get(name) is True
                for name in ("launcher_unchanged", "evaluation_sandbox_unchanged"):
                    if name in metadata:
                        invariants[name] = metadata[name] is True
            attempts.append({"metadata": str(source.relative_to(ROOT)), "finished": finished,
                             "invariants": invariants, "passed": all(invariants.values()),
                             "elapsed_seconds": metadata.get("elapsed_seconds")})
        reports[concept.name] = {"missing_paths": missing, "participant_symlinks": participant_links,
                                 "attempts": attempts,
                                 "valid": not missing and not participant_links and all(item["passed"] for item in attempts)}
    result = {"concept_count": len(reports), "required_modes": ["A", "C", "E"], "concepts": reports,
              "original_runner_sha256": hashlib.sha256((ROOT.parents[1] / "run_allowlisted_codex.sh").read_bytes()).hexdigest(),
              "passed": len(reports) == 3 and all(item["valid"] for item in reports.values())}
    destination = ROOT / "authoring/audit.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
