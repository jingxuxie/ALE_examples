import datetime
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
PROBE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / "evaluator/hidden/freeze.json").read_text())
    for relative, expected in manifest["sha256"].items():
        assert digest(ROOT / relative) == expected, relative
    source = ROOT / "attempts/v_2_evidence"
    evaluation = json.loads((source / "evaluation.json").read_text())
    assert evaluation["score"] == 1.0 and evaluation["accepted"]
    champion = ROOT / "champions/generation_2"
    champion.mkdir()
    (champion / "submission").mkdir()
    shutil.copy2(source / "submission_snapshot/witness.json", champion / "submission/witness.json")
    shutil.copy2(source / "evaluation.json", champion / "evaluation.json")
    if (source / "raw_evaluation.json").is_file():
        shutil.copy2(source / "raw_evaluation.json", champion / "raw_evaluation.json")
    shutil.copy2(ROOT / "evaluator/hidden/freeze.json", champion / "freeze.json")
    assert digest(champion / "submission/witness.json") == evaluation["candidate_sha256"]
    provenance = {
        "generation": 2,
        "source_evaluation": "attempts/v_2_evidence/evaluation.json",
        "source_witness": "attempts/v_2_evidence/submission_snapshot/witness.json",
        "witness_sha256": digest(champion / "submission/witness.json"),
        "evaluation_sha256": digest(champion / "evaluation.json"),
        "freeze_id": manifest["freeze_id"],
        "archived_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "score": 1.0,
        "accepted": True,
        "fresh_runtime_seconds_user_report": 1515.85,
        "fresh_agent_launched_by_author": False,
    }
    (champion / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    archive = ROOT.parent / "authoring/generations/concept_3/generation_2"
    archive.mkdir(parents=True, exist_ok=True)
    for relative in ("participant", "evaluator"):
        destination = archive / relative
        if not destination.exists():
            shutil.copytree(ROOT / relative, destination, ignore=shutil.ignore_patterns("__pycache__"))
    for relative, expected in manifest["sha256"].items():
        assert digest(archive / relative) == expected, "archive:" + relative
    shutil.copy2(ROOT / "status.json", PROBE / "generation_2_status_before.json")
    status = json.loads((ROOT / "status.json").read_text())
    status.update(state="solved_pending_search", status="solved_pending_search", ready=False,
                  known_pass=True, solvability="demonstrated", fresh_agent_score=1.0,
                  scientific_agent_attempts=2, current_generation_agent_attempts=1,
                  difficulty_status="Generation 2 scientifically solved; privileged final-ratchet search pending.",
                  reason="Passing fresh generation-2 witness archived with frozen-contract provenance.",
                  generation_2_champion=provenance | {"witness": "champions/generation_2/submission/witness.json", "evaluation": "champions/generation_2/evaluation.json"})
    status["fresh_attempts"] = [entry for entry in status.get("fresh_attempts", []) if entry["generation"] != 2] + [{"generation": 2, "status": "solved", "evaluation": provenance["source_evaluation"], "elapsed_seconds": 1515.85}]
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    (PROBE / "generation_2_frozen_inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
