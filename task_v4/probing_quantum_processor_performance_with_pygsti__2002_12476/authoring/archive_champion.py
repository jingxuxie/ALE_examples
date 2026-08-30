import argparse
import hashlib
import json
from pathlib import Path
import shutil

from run_fresh import ROOT, hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--generation", required=True, type=int)
    args = parser.parse_args()
    if not 1 <= args.generation <= 3:
        raise ValueError("at most three champion-ratchet generations")
    concept = ROOT / args.concept
    record_path = concept / "attempts" / (args.attempt + ".run.json")
    record = json.loads(record_path.read_text())
    score = json.loads((concept / "attempts" / (args.attempt + ".score.json")).read_text())
    if record["status"] != "finished" or not score["passed"] or not score["valid"]:
        raise ValueError("only a completed, valid passing fresh submission becomes champion")
    if hashes(concept / "participant") != record["participant_sha256"] or hashes(concept / "evaluator") != record["evaluator_sha256"]:
        raise ValueError("the champion generation is not frozen")
    snapshot = concept / "generations" / ("generation_" + str(args.generation - 1))
    champion = concept / "champions" / ("generation_" + str(args.generation))
    if snapshot.exists() or champion.exists():
        raise ValueError("generation archive already exists")
    snapshot.mkdir(parents=True)
    for name in ("participant", "evaluator", "adversary"):
        ignored = shutil.ignore_patterns("resilience") if name == "adversary" else None
        shutil.copytree(concept / name, snapshot / name, ignore=ignored)
    for name in ("freeze_manifest.json", "status.json"):
        if (concept / name).exists():
            shutil.copy2(concept / name, snapshot / name)
    filenames = {"concept_1": "design.json", "concept_2": "witness.json", "concept_3": "predictions.json"}
    filename = filenames[args.concept]
    artifact = concept / "attempts" / args.attempt / filename
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError("champion must be a self-contained regular artifact")
    champion.mkdir(parents=True)
    shutil.copy2(artifact, champion / filename)
    provenance = dict(source_attempt=args.attempt, source_model=record["model"], generation=args.generation,
                      artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(), score=score,
                      snapshot_root=str(snapshot.relative_to(ROOT)), submission_type="static artifact")
    (champion / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    status_path = snapshot / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    status.update(status="solved", hardness_decision="solved", fresh_score=score, fresh_attempt=args.attempt,
                  solvability="demonstrated_by_fresh_champion", solvability_demonstrated=True,
                  ratchet_generations=args.generation - 1)
    if "known_passing_data_only_solution" in status:
        status["known_passing_data_only_solution"] = True
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    record["snapshot_root"] = str(snapshot.relative_to(ROOT))
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
