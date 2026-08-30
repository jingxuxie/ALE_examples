from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from run_fresh import digest_tree, ROOT, RUNNER


def main():
    runs = []
    for path in sorted(ROOT.glob("concept_*/**/attempts/v_*_run/metadata.json")):
        metadata = json.loads(path.read_text())
        participant = Path(metadata["participant"])
        generation = participant.parent
        current = digest_tree(participant)
        evaluator = digest_tree(generation / "evaluator")
        submitted = None if metadata["status"] == "running" else digest_tree(Path(metadata["output"])) == metadata.get("submission_sha256")
        runs.append({"metadata": str(path.relative_to(ROOT)), "status": metadata["status"],
                     "scientific_assets_unchanged": current == metadata["participant_sha256"] and evaluator == metadata["evaluator_sha256"],
                     "finished_submission_unchanged": submitted,
                     "runner_unchanged": hashlib.sha256(RUNNER.read_bytes()).hexdigest() == metadata["runner_sha256"],
                     "model": metadata["model"], "time_limit_seconds": metadata["time_limit_seconds"],
                     "elapsed_seconds": metadata.get("elapsed_seconds"),
                     "content_isolation_transport": metadata.get("transport"),
                     "transport_hash_at_launch": metadata.get("transport_sha256"),
                     "score_present": (path.parent / "score.json").is_file()})
    packages = []
    for directory in sorted(ROOT.glob("concept_*")):
        generations = [directory] + sorted((directory / "generations").glob("generation_*"))
        for generation in generations:
            if not (generation / "participant").is_dir():
                continue
            required = ("participant/TASK.md", "participant/input", "participant/workspace",
                        "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden",
                        "attempts", "champions", "adversary", "status.json")
            packages.append({"path": str(generation.relative_to(ROOT)),
                             "missing": [name for name in required if not (generation / name).exists()]})
    probe = json.loads((ROOT / "authoring/isolation/probe/output/results.json").read_text())
    report = {"audited_at": datetime.now(timezone.utc).isoformat(), "runs": runs,
              "packages": packages, "content_isolation_probe": probe,
              "valid": all(item["scientific_assets_unchanged"] and item["runner_unchanged"] and item["finished_submission_unchanged"] is not False for item in runs)
                       and all(not item["missing"] for item in packages) and probe["valid"],
              "scope": "File provenance, fixed scientific assets, interface package completeness, and explicit read/write isolation checks. Scientific evaluator tests and feasibility reports are separate."}
    (ROOT / "authoring/audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
