import argparse
import json
from pathlib import Path
import sys

from exact import score_answer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "authoring"))


def aggregate(records):
    families = {}
    for record in records:
        families.setdefault(record["family"], []).append(record["relative_improvement"])
    family_scores = {family: sum(values) / len(values) for family, values in families.items()}
    core = sum(record["relative_improvement"] for record in records) / len(records)
    worst = min(family_scores.values())
    valid = all(record["valid"] for record in records)
    resources_ok = all(record.get("resources_ok", False) for record in records)
    passed = valid and resources_ok and core >= 0.20 - 1e-12 and worst >= 0.10 - 1e-12
    return {"core_score": core, "worst_family_score": worst, "family_scores": family_scores,
            "runtime_resource_score": float(resources_ok), "valid": valid, "passed": passed,
            "reason": ("target met" if passed else "requires valid resource-bounded outputs, mean improvement >=0.20 and each family >=0.10"),
            "instances": records}


def evaluate(submission):
    from sandbox import run_file
    rows = json.loads((ROOT / "evaluator/hidden/baselines.json").read_text())
    records = []
    for row in rows:
        input_path = ROOT / "evaluator/hidden/instances" / (row["name"] + ".json")
        record = {"name": row["name"], "family": row["family"], "valid": False,
                  "resources_ok": False, "relative_improvement": -1.0,
                  "baseline_worst_risk": row["baseline"]["worst_risk"]}
        try:
            answer, execution = run_file(submission, ROOT / "participant", input_path, timeout=45, memory_mb=2048)
            record["execution"] = execution
            if answer is None or execution["returncode"] != 0 or execution["timed_out"] or execution["output_limited"]:
                raise ValueError(execution.get("answer_error") or "solver execution failed")
            scores = score_answer(json.loads(input_path.read_text()), answer)
            record.update(scores)
            record["valid"] = True
            record["resources_ok"] = True
            record["relative_improvement"] = 1 - scores["worst_risk"] / row["baseline"]["worst_risk"]
            record["answer"] = answer
        except Exception as error:
            record["reason"] = str(error)
        records.append(record)
    return aggregate(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = evaluate(arguments.submission.resolve())
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
