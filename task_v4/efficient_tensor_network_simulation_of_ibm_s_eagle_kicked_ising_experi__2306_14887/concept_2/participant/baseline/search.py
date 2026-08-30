"""Reproducible coarse-grid/random search; improve or replace this baseline."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))

from simulator import compare_waveforms
from protocol import load_spec, metrics, waveforms
import numpy as np


def assess(witness, spec, robust=False, corners=False, workers=1):
    records = {}
    selected = {family: angles for family, angles in waveforms(witness, spec).items()
                if (robust and (corners or "/" not in family)) or family == "nominal"}
    for family, result in compare_waveforms(selected, tuple(spec["chis"]), workers).items():
        observable = spec["observable"]
        estimates = [result["mps"][str(chi)][observable] for chi in spec["chis"]]
        records[family] = metrics(result["exact"][observable], estimates, spec)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=48)
    parser.add_argument("--seed", type=int, default=14887)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    options = parser.parse_args()
    if options.trials < 1:
        parser.error("--trials must be positive")
    spec = load_spec()
    random = np.random.default_rng(options.seed)
    candidates = []
    for trial in range(options.trials):
        if trial < 18:
            depth = [16, 28, 40][trial // 6]
            knots = np.full(spec["knot_count"], 0.4 + 0.2 * (trial % 6))
        else:
            depth = int(random.integers(spec["depth_min"], spec["depth_max"] + 1))
            center = random.uniform(0.3, 1.35)
            knots = np.clip(center + random.normal(0, 0.045, spec["knot_count"]),
                            spec["knot_min"], spec["knot_max"])
        witness = {"schema_version": 1, "depth": depth, "knots": knots.tolist(), "observable": spec["observable"]}
        try:
            record = assess(witness, spec)["nominal"]
        except ValueError:
            continue
        candidates.append((record["margin"], witness))
        candidates.sort(key=lambda item: item[0], reverse=True)
        candidates = candidates[:4]
        print(json.dumps({"trial": trial, "nominal_margin": record["margin"]}), flush=True)
    best = None
    for _, witness in candidates:
        records = assess(witness, spec, robust=True)
        margin = min(record["margin"] for record in records.values())
        if best is None or margin > best[0]:
            best = (margin, witness, records)
    if best is None:
        raise SystemExit("no valid candidate")
    complete = assess(best[1], spec, robust=True, corners=True, workers=options.workers)
    margin = min(record["margin"] for record in complete.values())
    options.submission.mkdir(parents=True, exist_ok=True)
    (options.submission / "witness.json").write_text(json.dumps(best[1], indent=2) + "\n")
    (options.submission / "search_report.json").write_text(json.dumps(
        {"seed": options.seed, "trials": options.trials, "screening_policy": "original grid/random proposals and five-family finalist ranking",
         "family_count": len(complete), "worst_margin": margin, "families": complete}, indent=2) + "\n")
    print(json.dumps({"worst_margin": margin, "family_count": len(complete), "submission": str(options.submission)}))


if __name__ == "__main__":
    main()
