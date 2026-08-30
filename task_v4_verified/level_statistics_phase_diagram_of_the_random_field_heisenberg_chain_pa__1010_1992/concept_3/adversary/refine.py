import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import numpy as np
from exact import symmetry_distance
from calibrate import generate, measure, robust


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=6000)
    parser.add_argument("--label", default="refine")
    arguments = parser.parse_args()
    started = time.monotonic()
    random = np.random.default_rng(431992)
    pilot = [json.loads(line) for line in (ROOT / "adversary" / "pilot_robust.jsonl").read_text().splitlines()]
    seeds = sorted(pilot, key=lambda record: abs(record["robust"]["center_128"]["mean"]), reverse=True)[:12]
    print(json.dumps({"seed_leaders": [{"index": record["index"], "fields": record["fields"],
                                       "metric": record["robust"]["center_128"]} for record in seeds[:5]]}), flush=True)
    candidates = generate(7771992, arguments.count // 2)
    while len(candidates) < arguments.count:
        parent = seeds[int(random.integers(len(seeds)))]
        fields = np.array(parent["fields"]) * random.uniform(0.85, 1.15)
        fields += random.normal(0, random.choice([0.03, 0.08, 0.2, 0.4]), 12)
        fields -= fields.mean()
        if max(abs(fields)) > 7.8 or np.std(fields) < 0.65 or symmetry_distance(fields) < 0.12:
            continue
        candidates.append({"index": len(candidates), "kind": "mutant", "parent": parent["index"], "fields": fields.tolist()})
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        records = []
        with (ROOT / "adversary" / (arguments.label + ".jsonl")).open("w") as output:
            for record in executor.map(measure, candidates, chunksize=1):
                records.append(record)
                output.write(json.dumps(record) + "\n")
                if len(records) % 1000 == 0:
                    output.flush()
                    print(json.dumps({"measured": len(records), "seconds": time.monotonic() - started}), flush=True)
        selected = {}
        for metric in ("triple_128", "triple_96", "center_128", "energy_0.2000"):
            for record in sorted(records, key=lambda record: abs(record["statistics"][metric]), reverse=True)[:70]:
                selected[record["index"]] = record
        print(json.dumps({"shortlist": len(selected)}), flush=True)
        checked = []
        with (ROOT / "adversary" / (arguments.label + "_robust.jsonl")).open("w") as output:
            for record in executor.map(robust, selected.values(), chunksize=1):
                checked.append(record)
                output.write(json.dumps(record) + "\n")
                output.flush()
        summary = {}
        for metric in ("triple_128", "triple_96", "center_128", "energy_0.2000"):
            def strength(record):
                values = record["robust"][metric]
                sign = 1 if values["mean"] > 0 else -1
                return min(sign * value for value in values["families"] + [np.mean(values["scale"])])
            leaders = sorted(checked, key=strength, reverse=True)[:8]
            summary[metric] = leaders
            print(json.dumps({"metric": metric, "leaders": [{"index": record["index"], "kind": record["kind"],
                               "base": record["statistics"][metric], "worst": strength(record),
                               **record["robust"][metric]} for record in leaders]}, indent=2), flush=True)
        (ROOT / "adversary" / (arguments.label + "_summary.json")).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
