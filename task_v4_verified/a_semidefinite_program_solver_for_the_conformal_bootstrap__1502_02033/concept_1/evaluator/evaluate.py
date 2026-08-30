import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from hidden_cases import hidden_cases, public_input, suite_digest
from oracle import InvalidResult, LebesgueOracle
from runner import CPU_SECONDS, ROOT, run_solution


def source_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(solution, calibration=False):
    cases = hidden_cases()
    references = None
    if not calibration:
        references = json.loads((ROOT / "evaluator" / "reference.json").read_text())
        if references["suite_sha256"] != suite_digest(cases):
            raise RuntimeError("frozen suite checksum mismatch")
        if references["oracle_sha256"] != source_digest(ROOT / "evaluator" / "oracle.py"):
            raise RuntimeError("frozen oracle checksum mismatch")
    scores = []
    for case in cases:
        item = {"id": case["id"], "family": case["family"], "degree": case["degree"], "valid": False}
        try:
            output, timing = run_solution(solution, json.dumps(public_input(case)))
            measured = LebesgueOracle(case, output).supremum()
            item.update(timing)
            item.update(measured)
            item["valid"] = True
            if calibration:
                item["nodes"] = output["nodes"]
                item["score"] = 1.0
            else:
                baseline = references["cases"][case["id"]]
                item["score"] = math.exp(max(-700, min(700, baseline["log_lower"] - measured["log_upper"])))
            item["reason"] = "valid numerical enclosure"
        except (InvalidResult, OSError, ValueError, OverflowError) as error:
            item["score"] = 0.0
            item["reason"] = str(error)
        scores.append(item)
        print(case["id"], item["reason"], "score=", item["score"], file=sys.stderr, flush=True)
    valid = all(item["valid"] for item in scores)
    families = {}
    for family in sorted({case["family"] for case in cases}):
        selected = [item["score"] for item in scores if item["family"] == family]
        families[family] = math.exp(sum(math.log(score) for score in selected) / len(selected)) if min(selected) > 0 else 0.0
    core = math.exp(sum(math.log(value) for value in families.values()) / len(families)) if valid else 0.0
    worst = min(families.values())
    resource_score = max(0.0, 1.0 - sum(item.get("cpu_seconds", CPU_SECONDS) for item in scores) / (len(cases) * CPU_SECONDS)) if valid else 0.0
    target = references["target"] if references else None
    passed = bool(valid and target and core >= target["core_score"] and worst >= target["worst_family_score"]
                  and min(item["score"] for item in scores) >= target["minimum_case_score"]
                  and resource_score >= target["resource_score"])
    reason = "target met" if passed else ("baseline calibration only" if calibration and valid else
              "invalid case or infrastructure failure" if not valid else "valid but fixed improvement target not met")
    return {"verification_mode": "A_BASELINE_IMPROVEMENT", "core_score": core,
            "worst_family_score": worst, "runtime_score": resource_score, "resource_score": resource_score,
            "valid": valid, "passed": passed, "reason": reason, "family_scores": families,
            "target": target, "cases": scores, "suite_sha256": suite_digest(cases),
            "oracle_sha256": source_digest(ROOT / "evaluator" / "oracle.py"),
            "solution_sha256": source_digest(solution), "candidate_isolation": "bubblewrap-required"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solution", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--calibrate", action="store_true")
    arguments = parser.parse_args()
    report = evaluate(arguments.solution.resolve(), arguments.calibrate)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
