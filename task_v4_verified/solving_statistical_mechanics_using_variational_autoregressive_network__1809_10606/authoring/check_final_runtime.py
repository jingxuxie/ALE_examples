import importlib.util
import json
from pathlib import Path

from run_fresh import digest_tree


ROOT = Path(__file__).resolve().parents[1]
GENERATION = ROOT / "concept_1/generations/generation_3"


def main():
    destination = GENERATION / "adversary/final_runtime_boundary"
    destination.mkdir(exist_ok=False)
    specification = importlib.util.spec_from_file_location("final_runtime", GENERATION / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    submission = evaluator.validate_submission(GENERATION / "attempts/v_1")
    before = digest_tree(submission)
    original = json.loads((GENERATION / "attempts/v_1_run/score.json").read_text())
    instance = json.loads((GENERATION / "evaluator/hidden/mixed_2.json").read_text())
    protocol = {
        "case": "mixed_2", "repetitions": 2, "source_changed": False,
        "resources_changed": False, "original_score_overwritten": False,
        "original_passed": original["passed"],
        "original_case": next(case for case in original["cases"] if case["id"] == "mixed_2"),
        "timer_semantics": "The recorded timer starts before Popen; the frozen hard process.wait(timeout=120) deadline starts after Popen. The original 120.004-second recorded measurement and zero auxiliary runtime score are retained without changing any gate.",
    }
    (destination / "protocol.json").write_text(json.dumps(protocol, indent=2))
    records = []
    for repetition in range(2):
        record = {"repetition": repetition, "valid": False}
        try:
            model, elapsed = evaluator.run_case(submission, instance, "final_repeat_mixed_2")
            (destination / ("model_" + str(repetition) + ".json")).write_text(json.dumps(model))
            record.update(evaluator.exact_score(instance, model), valid=True, wall_seconds=elapsed)
        except Exception as error:
            record["reason"] = type(error).__name__ + ":" + str(error)
        records.append(record)
        assert digest_tree(submission) == before
        (destination / "results.json").write_text(json.dumps(records, indent=2))
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
