import argparse
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
sys.path.insert(0, str(ROOT.parent / "authoring"))
from generate import generate
from routing import validate
from sandbox import run_python
from solve import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("champion")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--per-family", type=int, default=12)
    arguments = parser.parse_args()
    destination = ROOT / "adversary" / f"champion_search_{arguments.generation}"
    destination.mkdir(exist_ok=True)
    families = ["chain", "ring", "grid", "ladder", "tree", "modular"]
    records = []
    cases = []
    started = time.monotonic()
    for family_index, family in enumerate(families):
        for case_index in range(arguments.per_family):
            identifier = f"challenge_{arguments.generation}_{family}_{case_index}"
            seed = 149284001 + 100031 * arguments.generation + 7919 * family_index + 151 * case_index
            case = generate(family, seed, identifier)
            cases.append(case)
            reference = validate(case, solve(case))
            record = {"id": identifier, "family": family, "baseline_cost": reference["cost"], "valid": False}
            try:
                execution = run_python(arguments.champion, "solve.py", case, 8)
                record["seconds"] = execution["seconds"]
                if execution["returncode"] or execution["timed_out"]:
                    raise ValueError("execution failure: " + execution["stderr"][-500:])
                answer = json.loads(execution["stdout"])
                record.update(validate(case, answer))
                record["ratio"] = record["cost"] / reference["cost"]
                record["regression"] = record["ratio"] > 1.0
                record["misses_15pct"] = record["ratio"] > 0.85
            except Exception as error:
                record["reason"] = str(error)
            records.append(record)
            print(json.dumps(record), flush=True)
            (destination / "progress.json").write_text(json.dumps(records, indent=2) + "\n")
    grouped = {}
    for family in families:
        selected = [record for record in records if record["family"] == family]
        grouped[family] = 1 - math.exp(sum(math.log(record["ratio"]) for record in selected) / len(selected)) if all(record["valid"] for record in selected) else -1
    valid = all(record["valid"] for record in records)
    core = 1 - math.exp(sum(math.log(record["ratio"]) for record in records) / len(records)) if valid else -1
    results = {"cases": len(records), "families": len(families), "core_score": core,
               "worst_family_score": min(grouped.values()), "family_scores": grouped, "valid": valid,
               "passed": valid and core >= 0.15 and min(grouped.values()) >= 0.08,
               "regressions": sum(record.get("regression", False) for record in records),
               "misses_15pct": sum(record.get("misses_15pct", True) for record in records),
               "wall_seconds": time.monotonic() - started, "records": records}
    (destination / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    (destination / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


if __name__ == "__main__":
    main()
