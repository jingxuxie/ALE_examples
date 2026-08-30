import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "concept_1/generations/generation_2"
SPECIFICATION = importlib.util.spec_from_file_location("concept1_repeat", GENERATION / "evaluator/evaluate.py")
EVALUATOR = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(EVALUATOR)


def main():
    output = GENERATION / "adversary/fresh_runtime_reproduction"
    output.mkdir(exist_ok=False)
    report = json.loads((GENERATION / "attempts/v_1_run/score.json").read_text())
    manifest = json.loads((GENERATION / "evaluator/hidden/manifest.json").read_text())
    failed = {case["id"] for case in report["cases"] if not case["valid"]}
    (output / "protocol.json").write_text(json.dumps({"repetitions": 2, "cases": sorted(failed),
        "source_changed": False, "resources_changed": False, "original_score_overwritten": False,
        "purpose": "Distinguish reproducible scientific/resource failure from transient wall-time behavior before retaining hardness."}, indent=2))
    records = []
    submission = EVALUATOR.validate_submission(GENERATION / "attempts/v_1")
    for case in manifest["cases"]:
        if case["id"] not in failed:
            continue
        instance = json.loads((GENERATION / "evaluator/hidden" / case["file"]).read_text())
        for repetition in range(2):
            record = {"id": case["id"], "repetition": repetition, "valid": False}
            try:
                model, elapsed = EVALUATOR.run_case(submission, instance, "repeat_" + case["id"])
                (output / (case["id"] + "_" + str(repetition) + ".json")).write_text(json.dumps(model))
                record.update(EVALUATOR.exact_score(instance, model), valid=True, wall_seconds=elapsed)
            except Exception as error:
                record["reason"] = type(error).__name__ + ":" + str(error)
            records.append(record)
            (output / "results.json").write_text(json.dumps(records, indent=2))
            print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
