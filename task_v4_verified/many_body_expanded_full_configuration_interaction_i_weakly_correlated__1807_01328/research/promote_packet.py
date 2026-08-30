import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    packet = arguments.packet.resolve(strict=True)
    status_path = concept / "status.json"
    status = json.loads(status_path.read_text())
    current = status.get("canonical_generation", 1)
    if arguments.generation <= current:
        raise ValueError("promotion must advance the canonical generation")
    if not (concept / "attempts" / f"v_{arguments.generation}.score.json").is_file():
        raise ValueError("evaluate the fresh attempt before promotion")
    for launch in (concept / "attempts").glob("*.launch.json"):
        manifest = json.loads(launch.read_text())
        if Path(manifest["participant"]).resolve() == (concept / "participant").resolve():
            snapshot = manifest.get("participant_snapshot")
            expected = manifest["participant_sha256"]
            preserved = {} if not snapshot else {
                name: hashlib.sha256((Path(snapshot) / name).read_bytes()).hexdigest()
                for name in expected if (Path(snapshot) / name).is_file()}
            if preserved != expected:
                raise ValueError("an original participant launch lacks an exact preserved snapshot")
    history = concept / "adversary/canonical_history" / f"generation_{current}"
    if history.exists():
        raise ValueError("canonical history already exists; refusing to overwrite")
    staging = concept / f".generation_{arguments.generation}_staging"
    staging.mkdir()
    source_hashes = {}
    for name in ("participant", "evaluator"):
        source_hashes[name] = hashes(packet / name)
        shutil.copytree(packet / name, staging / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (staging / name).chmod((staging / name).stat().st_mode | 0o200)
        if hashes(staging / name) != source_hashes[name]:
            raise ValueError("staged packet copy differs from the frozen source")
    history.mkdir(parents=True)
    shutil.copy2(status_path, history / "status_before_promotion.json")
    for name in ("participant", "evaluator"):
        (concept / name).rename(history / name)
        (staging / name).rename(concept / name)
    staging.rmdir()
    report = {"previous_canonical_generation": current, "canonical_generation": arguments.generation,
              "source_packet": str(packet.relative_to(concept)), "source_sha256": source_hashes,
              "historical_packet_preserved": str(history.relative_to(concept)),
              "latest_launch_source_packet_unchanged": True}
    (history / "promotion.json").write_text(json.dumps(report, indent=2) + "\n")
    status.update(canonical_generation=arguments.generation,
                  selected_packet=str(packet.relative_to(concept)),
                  participant_root="participant", evaluator="evaluator/evaluate.py")
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "source_sha256"}, indent=2))


if __name__ == "__main__":
    main()
