import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def digest_tree(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", choices=["concept_1", "concept_2", "concept_3"])
    parser.add_argument("generation", type=int, choices=[2, 3])
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    for record_path in (concept / "attempts").glob("*.run.json"):
        record = json.loads(record_path.read_text())
        if record["status"] == "running":
            raise RuntimeError(f"cannot promote while {record_path.name} is running")
        attempt_name = record_path.name.removesuffix(".run.json")
        for suffix in ("evaluation.json", "scoring.json"):
            if not (record_path.parent / f"{attempt_name}.{suffix}").is_file():
                raise RuntimeError(f"cannot promote before {attempt_name} grading is complete")
    staged = concept / "generations" / f"generation_{arguments.generation}"
    previous = concept / "generations" / f"generation_{arguments.generation - 1}"
    previous.mkdir(parents=True, exist_ok=True)
    for name in ("participant/TASK.md", "evaluator/evaluate.py"):
        if not (staged / name).is_file():
            raise RuntimeError(f"incomplete staged generation: {name}")
    archive_paths = {}
    for name in ("participant", "evaluator"):
        destination = previous / name
        if destination.exists():
            destination = previous / f"tested_{name}"
        if destination.exists():
            raise RuntimeError(f"refusing to overwrite {destination}")
        archive_paths[name] = destination
    before = {name: digest_tree(concept / name) for name in archive_paths}
    for name, destination in archive_paths.items():
        (concept / name).rename(destination)
        shutil.copytree(staged / name, concept / name)
    for name in ("README.md", "status.json", "RATCHET.md", "PROVENANCE.md", "provenance.md", "READY.md"):
        source = concept / name
        if source.exists():
            destination = previous / (name if not (previous / name).exists() else f"tested_{name}")
            if destination.exists():
                raise RuntimeError(f"refusing to overwrite {destination}")
            source.rename(destination)
    archive_attempts = previous / "attempts"
    archive_attempts.mkdir(exist_ok=True)
    for source in (concept / "attempts").glob("baseline*"):
        if not source.is_file():
            continue
        destination = archive_attempts / source.name
        if destination.exists():
            destination = archive_attempts / f"tested_{source.name}"
        if destination.exists():
            raise RuntimeError(f"refusing to overwrite {destination}")
        source.rename(destination)
    for source in (staged / "attempts").glob("baseline*"):
        if source.is_file():
            shutil.copy2(source, concept / "attempts" / source.name)
    for name in ("README.md", "RATCHET.md", "PROVENANCE.md", "provenance.md", "READY.md"):
        if (staged / name).exists():
            shutil.copy2(staged / name, concept / name)
    status = {
        "concept": arguments.concept,
        "current_generation": arguments.generation,
        "status": "pending_tournament",
        "hardness_finalized": False,
        "known_passing_solution": False,
        "solvability": "unknown",
    }
    (concept / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    record = {
        "published_at": datetime.now(timezone.utc).isoformat(),
        "generation": arguments.generation,
        "previous_archives": {name: str(path.relative_to(ROOT)) for name, path in archive_paths.items()},
        "previous_hashes": before,
        "published_hashes": {name: digest_tree(concept / name) for name in archive_paths},
        "staged_hashes": {name: digest_tree(staged / name) for name in archive_paths},
    }
    if record["published_hashes"] != record["staged_hashes"]:
        raise RuntimeError("published generation differs from sealed staging")
    destination = staged / "publication.json"
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"published": str(concept), "generation": arguments.generation}))


if __name__ == "__main__":
    main()
