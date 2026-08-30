import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {"concept_1":"model.json","concept_2":"witness.json","concept_3":"design.json"}


def digest(directory):
    return {str(path.relative_to(directory)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts}


def main():
    records = []
    for concept,artifact_name in ARTIFACTS.items():
        base = ROOT/concept
        current = json.loads((base/"status.json").read_text()).get("generation",2)
        for path in sorted((base/"attempts").glob("v_*.run.json")):
            run = json.loads(path.read_text())
            if run.get("status") != "finished":
                raise RuntimeError(f"unfinished attempt: {path}")
            if run["model"] != "ultima-alpha" or not run["initial_output_empty"] or not run["task_read_only"] or not run["ephemeral"] or run["web_search"] != "disabled":
                raise RuntimeError("fresh-attempt configuration mismatch")
            if not run["participant_unchanged"]:
                raise RuntimeError("participant changed during attempt")
            if not run["timed_out"] and run["returncode"] != 0:
                raise RuntimeError("non-timeout infrastructure failure needs review")
            generation = run["generation"]
            if concept == "concept_1" and generation == 2:
                participant = base/"champions/generation_2/legacy_task_snapshot/participant"
            elif generation == current:
                participant = base/"participant"
            else:
                participant = base/f"champions/generation_{generation}/task_snapshot/participant"
            if digest(participant) != run["participant_sha256"]:
                raise RuntimeError(f"launch participant snapshot mismatch: {path}")
            attempt = run["attempt"]
            stem = f"v_{attempt}"
            transcript = (base/"attempts"/(stem+".log")).read_text()
            activity = transcript.count("\nexec\n")
            if "model: ultima-alpha" not in transcript or activity == 0:
                raise RuntimeError("no evidence of meaningful requested-model execution")
            frozen = base/"attempts"/(stem+"_frozen")/artifact_name
            expected = run["submission_sha256"].get(artifact_name)
            capture = None
            if run["timed_out"]:
                capture = json.loads((base/"attempts"/(stem+"_deadline")/"capture.json").read_text())
                expected = capture["sha256"]
                if capture["artifact_present"] and capture["captured_utc_timestamp"] > capture["deadline_utc_timestamp"]:
                    raise RuntimeError("post-deadline artifact was selected")
            observed = hashlib.sha256(frozen.read_bytes()).hexdigest() if frozen.exists() else None
            if observed != expected:
                raise RuntimeError("frozen artifact differs from selected end/deadline bytes")
            score_path = base/"attempts"/(stem+".score.json")
            if concept == "concept_1" and generation == 2:
                score_path = base/"attempts"/(stem+".corrected_score.json")
            score = json.loads(score_path.read_text())
            records.append({"concept":concept,"attempt":attempt,"generation":generation,
                            "model":run["model"],"elapsed_seconds":run["elapsed_seconds"],
                            "timed_out":run["timed_out"],"tool_executions":activity,
                            "participant_snapshot_verified":True,"artifact_sha256":observed,
                            "deadline_snapshot_used":capture is not None,
                            "score_file":str(score_path.relative_to(ROOT)),
                            "core_score":score["core_score"],"worst_family_score":score["worst_family_score"],
                            "passed":score["passed"],"valid":score["valid"]})
    report = {"passed":True,"attempt_count":len(records),"records":records,
              "audited_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "submission_code_executed_by_grading":False}
    (ROOT/"authoring/tournament_audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":True,"attempt_count":len(records)}))


if __name__ == "__main__":
    main()
