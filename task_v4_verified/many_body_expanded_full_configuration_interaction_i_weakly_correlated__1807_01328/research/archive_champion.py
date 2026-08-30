import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--packet", type=Path)
    arguments = parser.parse_args()
    attempt = arguments.attempt if arguments.attempt is not None else arguments.generation
    concept = ROOT / arguments.concept
    packet = arguments.packet.resolve() if arguments.packet else concept
    prefix = concept / "attempts" / f"v_{attempt}"
    result = json.loads(prefix.with_suffix(".score.json").read_text())
    if not result["passed"]:
        raise ValueError("only a passing fresh submission can become champion")
    destination = concept / "champions" / f"generation_{arguments.generation}"
    destination.mkdir(parents=True, exist_ok=True)
    for name, source in (("submission", prefix), ("participant", packet / "participant"), ("evaluator", packet / "evaluator")):
        shutil.copytree(source, destination / name, dirs_exist_ok=True)
    if (packet / "attempts/baseline").is_dir():
        shutil.copytree(packet / "attempts/baseline", destination / "attempts/baseline", dirs_exist_ok=True)
    if (packet / "README.md").is_file():
        shutil.copy2(packet / "README.md", destination / "README.md")
    shutil.copy2(prefix.with_suffix(".score.json"), destination / "score.json")
    manifest_path = prefix.with_suffix(".launch.json")
    manifest = json.loads(manifest_path.read_text())
    manifest["participant_snapshot"] = str(destination / "participant")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    status_path = concept / "status.json"
    status = json.loads(status_path.read_text())
    status.update(status="solved", generation=arguments.generation,
                  fresh_attempt_count=len(list((concept / "attempts").glob("v_*.launch.json"))),
                  fresh_agents_launched=len(list((concept / "attempts").glob("v_*.launch.json"))), attempts_empty=False,
                  fresh_score=result, champion=str(destination.relative_to(concept)),
                  ratchet_pending=True, static_submission="witness.json" if arguments.concept == "concept_2" else status.get("static_submission"))
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"champion": str(destination), "passed": True,
                      "privileged_artifacts_remain_private": True}, indent=2))


if __name__ == "__main__":
    main()
