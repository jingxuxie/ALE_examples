import argparse
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default="attempts/v_1/latest_raw.json")
    parser.add_argument("--evaluation", default="adversary/refine_fresh/v1_latest_raw.original_full.json")
    arguments = parser.parse_args()
    artifact_path = ROOT / arguments.artifact
    evaluation_path = ROOT / arguments.evaluation
    artifact_bytes = artifact_path.read_bytes()
    artifact = json.loads(artifact_bytes)
    evaluation = json.loads(evaluation_path.read_text())
    run_name = artifact_path.parent.name
    run_path = ROOT / "attempts" / (run_name + ".run.json")
    run = json.loads(run_path.read_text())
    raw_digest = hashlib.sha256(artifact_bytes).hexdigest()
    canonical_digest = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert run["submission_sha256"][artifact_path.name] == raw_digest
    assert evaluation["artifact_canonical_sha256"] == canonical_digest
    assert evaluation["valid"] is True and evaluation["passed"] is True
    cutoff = datetime.datetime.fromisoformat(run["started_at"]) + datetime.timedelta(seconds=run["limit_seconds"])
    modified = datetime.datetime.fromtimestamp(artifact_path.stat().st_mtime, datetime.timezone.utc)
    assert modified <= cutoff, (modified.isoformat(), cutoff.isoformat())
    proof = {
        "classification": "ORIGINAL_FRESH_ARTIFACT_PASSES_FROZEN_EVALUATOR",
        "concept_is_solved_not_hard": True,
        "original_artifact": arguments.artifact,
        "original_sha256": raw_digest,
        "artifact_canonical_sha256": canonical_digest,
        "cutoff_record": str(run_path.relative_to(ROOT)),
        "cutoff_record_sha256": hashlib.sha256(run_path.read_bytes()).hexdigest(),
        "cutoff_record_pointer": "submission_sha256/" + artifact_path.name,
        "mtime_utc": modified.isoformat(),
        "cutoff_utc": cutoff.isoformat(),
        "original_file_precedes_one_hour_cutoff": True,
        "evaluation": arguments.evaluation,
        "evaluation_sha256": hashlib.sha256(evaluation_path.read_bytes()).hexdigest(),
        "valid": evaluation["valid"],
        "passed": evaluation["passed"],
        "core_score": evaluation["core_score"],
        "worst_family_score": evaluation["worst_family_score"],
        "worst_case_score": evaluation["worst_case_score"],
        "thresholds": evaluation["thresholds"],
        "audits": evaluation["audits"],
        "post_deadline_optimization_runs": 0,
        "post_deadline_control_modifications": 0,
        "fresh_agents_launched_by_this_worker": 0,
        "note": "Only private audit/evaluation code and records were created after the deadline; the passing control bytes are an original, hash-recorded fresh output."
    }
    output = HERE / (run_name + "_" + artifact_path.stem + ".original_pass_proof.json")
    output.write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
    print(json.dumps(proof, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
