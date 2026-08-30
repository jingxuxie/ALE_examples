import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "participant/TASK.md",
    "participant/input",
    "participant/workspace",
    "participant/baseline",
    "evaluator/evaluate.py",
    "evaluator/hidden",
    "attempts",
    "champions",
    "adversary",
    "status.json",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(directory, include_bytecode=False):
    return {
        str(path.relative_to(directory)): digest(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and (include_bytecode or "__pycache__" not in path.parts)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    errors = []
    pending = []
    trials = []
    runner_hash = digest(ROOT.parents[1] / "run_allowlisted_codex.sh")
    runner_revisions = json.loads((ROOT / "authoring/runner_revisions.json").read_text())
    reviewed_runners = set(runner_revisions["reviewed_sha256"])
    if runner_hash not in reviewed_runners:
        errors.append("provided runner has an unreviewed revision")
    for concept_number in (1, 2, 3):
        concept = ROOT / f"concept_{concept_number}"
        for required in REQUIRED:
            if not (concept / required).exists():
                errors.append(f"{concept.name}: missing {required}")
        metadata_paths = sorted((concept / "attempts").glob("v_*.metadata.json"))
        if not metadata_paths:
            errors.append(f"{concept.name}: no fresh trial")
        for metadata_path in metadata_paths:
            metadata = json.loads(metadata_path.read_text())
            name = metadata_path.name.removesuffix(".metadata.json")
            label = f"{concept.name}/{name}"
            required_metadata = {
                "model": "ultima-alpha",
                "limit_seconds": 3600,
                "initial_output_empty": True,
                "fresh_session": True,
                "ephemeral": True,
                "network": False,
                "task_access": "read",
            }
            for key, expected in required_metadata.items():
                if metadata.get(key) != expected:
                    errors.append(f"{label}: incorrect {key}")
            if metadata.get("runner_sha256") not in reviewed_runners:
                errors.append(f"{label}: unreviewed runner revision")
            if metadata.get("runner_snapshot"):
                if digest(Path(metadata["runner_snapshot"])) != metadata["runner_sha256"]:
                    errors.append(f"{label}: runner snapshot hash mismatch")
            participant = Path(metadata["participant"]).resolve()
            current = hashes(participant)
            if current != metadata["participant_hashes_before"]:
                errors.append(f"{label}: public assets changed since launch")
            if "finished_at" not in metadata:
                pending.append(label)
                continue
            if not metadata.get("participant_unchanged"):
                errors.append(f"{label}: participant mutation during trial")
            score_path = metadata_path.with_name(name + ".score.json")
            freeze_path = metadata_path.with_name(name + ".freeze.json")
            if not score_path.exists() or not freeze_path.exists():
                pending.append(label + ": grading pending")
                continue
            score = json.loads(score_path.read_text())
            freeze = json.loads(freeze_path.read_text())
            snapshot = concept / score["submission_snapshot"]
            recorded_hashes = freeze.get("sha256", {})
            if not recorded_hashes or hashes(snapshot, include_bytecode=True) != recorded_hashes:
                errors.append(f"{label}: snapshot hash mismatch or missing manifest")
            at_finish = metadata.get("submission_hashes", {})
            for relative, expected in recorded_hashes.items():
                if "__pycache__" not in Path(relative).parts and at_finish.get(relative) != expected:
                    errors.append(f"{label}: frozen file differs from end-of-trial record: {relative}")
            if freeze.get("evaluator_sha256"):
                if digest(Path(freeze["evaluator"])) != freeze["evaluator_sha256"]:
                    errors.append(f"{label}: evaluator changed after grading")
            for key in ("core_score", "worst_family_score", "resource_score", "valid", "passed", "reason"):
                if key not in score:
                    errors.append(f"{label}: score lacks {key}")
            trials.append({
                "trial": label,
                "participant": str(participant.relative_to(ROOT)),
                "elapsed_seconds": metadata["elapsed_seconds"],
                "timed_out": metadata["timed_out"],
                "participant_unchanged": metadata["participant_unchanged"],
                "runner_sha256": metadata["runner_sha256"],
                "core_score": score.get("core_score"),
                "worst_family_score": score.get("worst_family_score"),
                "resource_score": score.get("resource_score"),
                "valid": score.get("valid"),
                "passed": score.get("passed"),
                "reason": score.get("reason"),
            })
    construction = ROOT / "concept_3"
    freeze = json.loads((construction / "evaluator/hidden/freeze.json").read_text())
    for relative in ("participant/input/instances.json", "evaluator/hidden/frozen_instances.json"):
        if digest(construction / relative) != freeze["instances_sha256"]:
            errors.append(f"concept_3: instance freeze mismatch at {relative}")
    if digest(construction / "evaluator/hidden/planted_witness.json") != freeze["planted_witness_sha256"]:
        errors.append("concept_3: achievability witness changed")
    commitments = []
    routing_generation = ROOT / "concept_1/adversary/generation_2"
    routing_freeze = routing_generation / "freeze.json"
    if routing_freeze.exists():
        frozen_hashes = json.loads(routing_freeze.read_text())["sha256"]
        selected = {relative: expected for relative, expected in frozen_hashes.items()
                    if relative.startswith(("participant/", "evaluator/"))}
        for relative, expected in selected.items():
            if digest(routing_generation / relative) != expected:
                errors.append(f"routing generation 2 scoring commitment changed: {relative}")
        commitments.append({"generation": "concept_1/generation_2", "files_checked": len(selected)})
    for generation in (1, 2, 3):
        package = ROOT / "concept_2"
        if generation > 1:
            package = package / "adversary" / f"generation_{generation}"
        manifest = package / "adversary/frozen_manifest.json"
        if not manifest.exists():
            continue
        frozen_hashes = json.loads(manifest.read_text())
        selected = {relative: expected for relative, expected in frozen_hashes.items()
                    if isinstance(expected, str) and relative.startswith(("participant/", "evaluator/"))}
        for relative, expected in selected.items():
            if digest(package / relative) != expected:
                errors.append(f"counterexample generation {generation} scoring commitment changed: {relative}")
        commitments.append({"generation": f"concept_2/generation_{generation}", "files_checked": len(selected)})
    result = {
        "valid": not errors,
        "complete": not pending,
        "built_concepts": 3,
        "runner_sha256": runner_hash,
        "errors": errors,
        "pending": pending,
        "scoring_commitments": commitments,
        "trials": trials,
        "scope": "Package layout, launch isolation metadata, immutable public assets, witness snapshots, scoring fields, and construction-instance freeze; mathematical validator tests are separate preserved artifacts.",
    }
    text = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(text)
    print(text)
    if errors or (arguments.require_complete and pending):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
