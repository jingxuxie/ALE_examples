import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from model import baseline_order, improvement, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads((args.input / "workloads.json").read_text())["cases"]
    result = json.loads((args.submission / "schedules.json").read_text())["schedules"]
    if set(result) != {case["id"] for case in cases}:
        raise ValueError("case IDs differ")
    families = defaultdict(list)
    records = []
    peak_guard = True
    for case in cases:
        before = metrics(case, baseline_order(case))
        after = metrics(case, result[case["id"]])
        ratio = improvement(before, after)
        families[case["family"]].append(math.log(ratio))
        peak_guard &= 20 * after["peak"] <= 21 * before["peak"]
        records.append({"id": case["id"], "ratio": ratio, **after})
    core = math.exp(sum(math.log(record["ratio"]) for record in records) / len(records))
    worst = min(math.exp(sum(values) / len(values)) for values in families.values())
    print(json.dumps({"core_score": core, "worst_family_score": worst,
                      "peak_guard": peak_guard,
                      "passed": core >= 1.70 and worst >= 1.18 and peak_guard,
                      "cases": records}, indent=2))


if __name__ == "__main__":
    main()
