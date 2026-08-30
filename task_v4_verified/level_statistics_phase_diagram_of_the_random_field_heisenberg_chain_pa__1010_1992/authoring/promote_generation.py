import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from run_attempt import tree_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("--generation", type=int, required=True)
    arguments = parser.parse_args()
    concept = arguments.concept.resolve()
    if arguments.generation <= 1:
        raise ValueError("Promotion is only needed after a ratchet")
    if (concept / "promotion.json").exists():
        raise ValueError("Canonical generation already promoted")
    source = concept / "generations" / ("generation_" + str(arguments.generation))
    freeze_path = source / "adversary" / ("generation_" + str(arguments.generation) + "_freeze.json")
    if not freeze_path.is_file():
        raise ValueError("Active generation is not frozen")
    metadata_paths = sorted((concept / "attempts").glob("v_*.run.json"))
    metadata_records = []
    for path in metadata_paths:
        metadata = json.loads(path.read_text())
        if "returncode" not in metadata:
            raise ValueError("Attempt still running: " + str(path))
        if metadata["submission_sha256"] != tree_digest(Path(metadata["output"])):
            raise ValueError("Submission changed after termination: " + str(path))
        if not metadata["participant_unchanged"]:
            raise ValueError("Participant mutated during attempt")
        metadata_records.append((path, metadata))
    archive = concept / "generations/generation_1"
    archive.mkdir(parents=True, exist_ok=True)
    if (archive / "participant").exists() or (archive / "evaluator").exists():
        raise ValueError("Initial-generation archive already exists")
    for name in ("participant", "evaluator"):
        shutil.move(str(concept / name), str(archive / name))
        shutil.copytree(source / name, concept / name)
        if tree_digest(source / name) != tree_digest(concept / name):
            raise RuntimeError("Promoted tree differs from scored generation")
    (archive / "adversary").mkdir(exist_ok=True)
    for name in ("generation_1_freeze.json", "baseline_score.json", "privileged_score.json"):
        if (concept / "adversary" / name).is_file():
            shutil.copy2(concept / "adversary" / name, archive / "adversary" / name)
    shutil.copy2(concept / "status.json", archive / "status_before_promotion.json")
    shutil.copy2(freeze_path, concept / "adversary" / freeze_path.name)
    for path, metadata in metadata_records:
        if metadata["generation"] == 1:
            metadata["participant_snapshot"] = str(archive / "participant")
            metadata["evaluator_snapshot"] = str(archive / "evaluator/evaluate.py")
            if metadata["participant_sha256_before"] != tree_digest(archive / "participant"):
                raise RuntimeError("Historical task hash mismatch")
        else:
            metadata["participant_snapshot"] = metadata["participant"]
            metadata["evaluator_snapshot"] = str(Path(metadata["participant"]).parent / "evaluator/evaluate.py")
        path.write_text(json.dumps(metadata, indent=2) + "\n")
    report = {"current_generation": arguments.generation, "promoted_utc": datetime.now(timezone.utc).isoformat(),
              "initial_archive": str(archive), "active_scored_source": str(source),
              "participant_sha256": tree_digest(concept / "participant"),
              "evaluator_sha256": tree_digest(concept / "evaluator"), "historical_attempts_preserved": True}
    (concept / "promotion.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
