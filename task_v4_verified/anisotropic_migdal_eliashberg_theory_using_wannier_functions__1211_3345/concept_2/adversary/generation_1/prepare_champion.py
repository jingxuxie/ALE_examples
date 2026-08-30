import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PENDING = Path(__file__).resolve().parent
RUNS = ROOT.parent / "authoring" / "runs" / "concept_2"


def manifest(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("archive source contains a symlink: " + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def copy_frozen(source, destination):
    expected = manifest(source)
    if not destination.exists():
        shutil.copytree(source, destination)
    if manifest(destination) != expected:
        raise ValueError("existing archive differs from source: " + str(destination))
    return expected


def main():
    candidates = []
    for name in ("v_1", "v_2"):
        directory = RUNS / name
        evaluation = json.loads((directory / "evaluation.json").read_text())
        if not evaluation.get("valid"):
            continue
        candidates.append((float(evaluation["score"]), -float(evaluation.get("elapsed_seconds", 0)), name, directory, evaluation))
    if not candidates:
        raise RuntimeError("no independently valid fresh champion")
    selected = max(candidates)
    score, negative_elapsed, name, source, evaluation = selected
    destination = ROOT / "champions" / "generation_1"
    destination.mkdir(parents=True, exist_ok=True)
    frozen_manifest = copy_frozen(source / "frozen_submission", destination / "frozen_submission")
    for filename in ("evaluation.json", "evaluation_audit.json", "evaluation_complete.json", "launch.json", "result.json"):
        original = source / filename
        if original.exists():
            copied = destination / filename
            if copied.exists() and copied.read_bytes() != original.read_bytes():
                raise ValueError("refusing to overwrite an archived result")
            if not copied.exists():
                shutil.copyfile(original, copied)
    archive = PENDING / "archived_originals"
    archive.mkdir(parents=True, exist_ok=True)
    archived = {}
    for directory_name in ("participant", "evaluator"):
        archived[directory_name] = copy_frozen(ROOT / directory_name, archive / directory_name)
    metadata = {
        "selected_fresh_attempt": name, "selection_rule": "highest unrounded valid score, then lower evaluator elapsed time",
        "score": score, "original_verdict_unchanged": evaluation,
        "source": str(source), "frozen_submission_manifest": frozen_manifest,
        "all_initial_results": {candidate[2]: candidate[4] for candidate in candidates},
        "launch_participant_manifest": json.loads((source / "launch.json").read_text()).get("participant_manifest"),
        "launch_evaluator_manifest": json.loads((source / "launch.json").read_text()).get("evaluator_manifest"),
    }
    (destination / "archive_manifest.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (archive / "archive_manifest.json").write_text(json.dumps(archived, indent=2, sort_keys=True) + "\n")
    (PENDING / "champion_selection.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"selected": name, "score": score, "destination": str(destination), "archived_originals": str(archive)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
