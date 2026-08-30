import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATIONS = {
    "concept_1": {"v_1": 1, "v_2": 2, "v_3": 3},
    "concept_2": {"v_1": 1, "v_2": 2, "v_3": 3},
    "concept_3": {"v_1": 1, "v_2": 2, "v_3": 3, "v_4": 3},
}


def fingerprints(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def audit():
    records = []
    problems = []
    for concept_name, generation_map in GENERATIONS.items():
        concept = ROOT / concept_name
        required = ["participant/TASK.md", "participant/input", "participant/workspace",
                    "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden",
                    "attempts", "champions", "adversary", "status.json"]
        for relative in required:
            if not (concept / relative).exists():
                problems.append(f"{concept_name}: missing {relative}")
        for version, generation in generation_map.items():
            audit_directory = concept / "attempts" / (version + "_audit")
            metadata_path = audit_directory / "metadata.json"
            if not metadata_path.exists():
                continue
            metadata = json.loads(metadata_path.read_text())
            finished = "finished_unix" in metadata
            record = {"concept": concept_name, "attempt": version, "generation": generation,
                      "finished": finished, "model": metadata["model"],
                      "limit_seconds": metadata["limit_seconds"],
                      "output_initially_empty": metadata["output_initially_empty"],
                      "participant_unchanged": metadata.get("participant_unchanged"),
                      "elapsed_seconds": metadata.get("elapsed_seconds"),
                      "timed_out": metadata.get("timed_out"),
                      "audit": str(audit_directory.relative_to(ROOT))}
            if metadata["model"] != "ultima-alpha" or metadata["limit_seconds"] != 3600:
                problems.append(f"{concept_name}/{version}: model or limit mismatch")
            if not metadata["output_initially_empty"]:
                problems.append(f"{concept_name}/{version}: nonempty initial output")
            if finished:
                record["final_output_unchanged"] = (
                    fingerprints(concept / "attempts" / version) == metadata["submission_sha256"]
                )
                if not metadata["participant_unchanged"] or not record["final_output_unchanged"]:
                    problems.append(f"{concept_name}/{version}: asset or submission mutation")
                evaluation_path = audit_directory / "evaluation.json"
                if evaluation_path.exists():
                    evaluation = json.loads(evaluation_path.read_text())
                    record.update(passed=evaluation["passed"], valid=evaluation["valid"],
                                  core_score=evaluation["core_score"],
                                  worst_family_score=evaluation.get("worst_family_score"),
                                  reason=evaluation["reason"])
                else:
                    problems.append(f"{concept_name}/{version}: evaluation still missing")
            records.append(record)
    return {"valid": not problems, "all_attempts_finished": all(record["finished"] for record in records),
            "problems": problems, "attempts": records,
            "excluded_launches": "Non-v_* infrastructure-only launches are not hardness evidence.",
            "generation_note": "concept_3/v_3 and v_4 independently test the same frozen generation 3."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = audit()
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
