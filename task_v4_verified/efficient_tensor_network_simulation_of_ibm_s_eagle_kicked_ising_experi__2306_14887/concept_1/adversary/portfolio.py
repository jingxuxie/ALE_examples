import concurrent.futures
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from contraction import assess, baseline_plan


def search(case):
    started = time.monotonic()
    plan = baseline_plan(case["instance"], trials=512, seed_offset=5172389)
    cost = assess(case["instance"], plan)
    ratio = case["baseline_work"] / cost["work"]
    print(case["id"], ratio, flush=True)
    return {"id": case["id"], "family": case["family"], "speedup": ratio,
            "plan": plan, "work": cost["work"], "runtime_seconds": time.monotonic() - started}


if __name__ == "__main__":
    cases = json.loads((ROOT / "evaluator" / "hidden" / "challenge.json").read_text())["cases"]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(search, cases))
    family_scores = {family: math.exp(sum(math.log(row["speedup"]) for row in results if row["family"] == family) /
                                    sum(row["family"] == family for row in results))
                     for family in {row["family"] for row in results}}
    core = math.exp(sum(math.log(row["speedup"]) for row in results) / len(results))
    payload = {"method": "512 additional randomized greedy+slicing restarts per hidden case",
               "core_score": core, "worst_family_score": min(family_scores.values()),
               "family_scores": family_scores, "minimum_case_speedup": min(row["speedup"] for row in results),
               "runtime_seconds": sum(row["runtime_seconds"] for row in results), "cases": results}
    (ROOT / "adversary" / "portfolio.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({key: value for key, value in payload.items() if key != "cases"}, indent=2))
