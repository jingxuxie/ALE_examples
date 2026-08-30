"""Pre-freeze distribution checks, independent of release splits."""

import json
import sys
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input/workspace"))
from generator import FAMILIES, accepted_sample, full_order_sums


def main():
    rng = np.random.default_rng(903144)
    report = {}
    with threadpool_limits(limits=1):
        for family, name in enumerate(FAMILIES):
            rows = []
            for index in range(16):
                model, features, truth, rejections = accepted_sample(
                    rng, 2 + index % 2, 6 + index % 4, family)
                sums = full_order_sums(model) if index < 2 else None
                rows.append({**truth, "rejections": rejections,
                             "order_sums": None if sums is None else sums.tolist()})
            report[name] = rows
            print(name, "tail_abs_quantiles", np.quantile([abs(row["tail"]) for row in rows],
                  [0, .5, 1]).tolist(), "min_ref_weight", min(row["reference_weight"] for row in rows),
                  "rejections", sum(row["rejections"] for row in rows), flush=True)
    destination = ROOT / "adversary/pilot_distribution.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
