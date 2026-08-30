import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text()) if path.is_file() else None


def record_attempt(concept, launch_path):
    launch = load(launch_path)
    label = launch_path.name.removesuffix(".launch.json")
    prefix = concept / "attempts" / label
    exit_record = load(prefix.with_suffix(".exit.json"))
    score_path = prefix.with_suffix(".score.json")
    score = load(score_path)
    record = {
        "concept": concept.name,
        "generation": launch["generation"],
        "replicate": launch.get("replicate", 1),
        "attempt": label,
        "model": launch["model"],
        "limit_seconds": launch["limit_seconds"],
        "started_utc": launch["started_utc"],
        "participant_manifest_sha256": hashlib.sha256(json.dumps(
            launch["participant_sha256"], sort_keys=True).encode()).hexdigest(),
        "launch_record": str(launch_path.relative_to(ROOT)),
        "completed": exit_record is not None,
        "evaluated": score is not None,
        "hardness_evidence_eligible": concept.name != "concept_1",
    }
    if exit_record:
        for field in ("returncode", "timed_out", "wall_seconds", "finished_utc"):
            record[field] = exit_record[field]
    if score:
        record.update({
            "passed": score.get("passed", score.get("pass", False)),
            "core_score": score.get("core_score", score.get("core", 0.0)),
            "worst_family_score": score.get("worst_family_score", score.get("worst_fidelity")),
            "evaluator_runtime_seconds": score.get("runtime_seconds"),
            "reason": score.get("reason"),
            "score_record": str(score_path.relative_to(ROOT)),
            "score_sha256": hashlib.sha256(score_path.read_bytes()).hexdigest(),
        })
        if concept.name == "concept_2":
            diagnostics = score.get("diagnostics", {})
            record["diagnostics"] = {key: diagnostics[key] for key in (
                "occupation_violation", "rdm_dad", "energy_error", "ground_overlap",
                "worst_population_violation_observed", "max_dad_observed",
                "max_energy_error_observed", "endpoint_feasible", "stencil", "failure_clusters",
            ) if key in diagnostics}
        if concept.name == "concept_3":
            record["case_scores"] = score.get("cases", [])
    if concept.name == "concept_1":
        record["qualification"] = (
            "Generator-cancelled after a universal proof that the frozen target is infeasible; "
            "checkpoint scores are not evidence of model hardness."
        )
    return record


def main():
    records = [record_attempt(concept, launch)
               for concept in sorted(ROOT.glob("concept_*"))
               for launch in sorted((concept / "attempts").glob("v_*.launch.json"))]
    result = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "record_count": len(records),
        "completed_count": sum(record["completed"] for record in records),
        "evaluated_count": sum(record["evaluated"] for record in records),
        "records": records,
    }
    destination = ROOT / "authoring" / "score_ledger.json"
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}))
    for record in records:
        print(record["concept"], record["attempt"], record.get("core_score", "pending"),
              record.get("passed", "pending"), record.get("wall_seconds", "running"))


if __name__ == "__main__":
    main()
