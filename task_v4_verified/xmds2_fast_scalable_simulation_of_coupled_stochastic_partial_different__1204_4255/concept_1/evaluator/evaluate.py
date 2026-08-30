import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT.parent / "authoring"))
from isolation import run_submission
from model import check


def evaluate(submission, cases_path=None):
    cases = json.loads(Path(cases_path or ROOT / "evaluator" / "hidden" / "cases.json").read_text())
    run = run_submission(submission, ROOT / "participant", "".join(json.dumps(case["instance"], separators=(",", ":")) + "\n" for case in cases))
    lines = run.pop("stdout").splitlines()
    rows = []
    failure = None
    if run["timed_out"] or run.get("resource_violation") or run["returncode"] != 0 or len(lines) != len(cases):
        failure = "planner failed, exceeded resources, or returned the wrong number of JSON lines"
    if failure is None:
        for case, line in zip(cases, lines):
            try:
                result = check(case["instance"], json.loads(line))
                baseline_cost = case["baseline"]["cost"]
                if baseline_cost == 0:
                    if result["cost"] != 0:
                        raise ValueError("nonzero cost on zero-cost baseline instance")
                    ratio = 1.0
                else:
                    ratio = result["cost"] / baseline_cost
                    if ratio <= 0:
                        raise ValueError("inconsistent positive-cost baseline")
                rows.append({"id": case["id"], "family": case["family"], "ratio": ratio, **result})
            except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as error:
                failure = f"invalid plan for {case['id']}: {error}"
                break
    families = {}
    core_score = 0.0
    worst_family_score = 0.0
    if failure is None:
        for family in sorted({row["family"] for row in rows}):
            ratios = [row["ratio"] for row in rows if row["family"] == family]
            families[family] = 1 - math.exp(sum(math.log(value) for value in ratios) / len(ratios))
        core_score = 1 - math.exp(sum(math.log(row["ratio"]) for row in rows) / len(rows))
        worst_family_score = min(families.values())
    passed = failure is None and core_score >= 0.20 and worst_family_score >= 0.08
    return {"core_score": core_score, "worst_family_score": worst_family_score, "runtime_resource_score": max(0.0, 1 - run["elapsed_seconds"] / 120), "passed": passed, "valid": failure is None, "reason": failure or ("fixed improvement targets met" if passed else "below fixed overall or worst-family improvement target"), "target": {"core_score_min": 0.20, "worst_family_score_min": 0.08}, "family_scores": families, "resources": run, "cases": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--cases")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    result = evaluate(arguments.submission, arguments.cases)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
