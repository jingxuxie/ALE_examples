import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from measure import HERE, ROOT, check, scores


def main():
    cases = json.loads((ROOT / "evaluator" / "hidden" / "cases.json").read_text())
    selected = {}
    reports = []
    for path in sorted((HERE / "results").glob("*.json")):
        report = json.loads(path.read_text())
        if "spec" not in report:
            continue
        reports.append({key: report.get(key) for key in ["spec", "valid", "core_score", "worst_family_score", "cost", "elapsed_seconds", "cpu_seconds"]})
        if not report["valid"]:
            continue
        answers = [json.loads(line) for line in path.with_suffix(".plans.jsonl").read_text().splitlines()]
        for case, row, answer in zip(cases, report["cases"], answers):
            exact = check(case["instance"], answer)
            if exact["cost"] != row["cost"]:
                raise AssertionError("Score mismatch")
            if case["id"] not in selected or exact["cost"] < selected[case["id"]][0]:
                selected[case["id"]] = (exact["cost"], path.stem, answer)
    output = {"variants": reports}
    if len(selected) == len(cases):
        rows = [{"id": case["id"], "family": case["family"], "baseline_cost": case["baseline"]["cost"], "cost": selected[case["id"]][0], "ratio": selected[case["id"]][0] / case["baseline"]["cost"], "source": selected[case["id"]][1]} for case in cases]
        output["oracle_union"] = {**scores(rows), "cases": rows, "classification": "Cost potential only; a generic portfolio must actually rerun selected configurations within the runtime budget."}
    (HERE / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({**output, "oracle_union": {key: value for key, value in output.get("oracle_union", {}).items() if key != "cases"}}, indent=2))


if __name__ == "__main__":
    main()
