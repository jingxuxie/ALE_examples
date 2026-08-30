import argparse
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from physics import observables


def validate_design(document, spec):
    if not isinstance(document, dict) or set(document) != {"layouts"}:
        raise ValueError("Expected a layouts object")
    layouts = document["layouts"]
    if not isinstance(layouts, list) or len(layouts) != len(spec["banks"]):
        raise ValueError("Wrong number of layouts")
    indexed = {}
    banks = {bank["id"]: bank for bank in spec["banks"]}
    for layout in layouts:
        if not isinstance(layout, dict) or set(layout) != {"id", "high", "low"}:
            raise ValueError("Malformed layout")
        identity = layout["id"]
        if not isinstance(identity, str) or identity not in banks or identity in indexed:
            raise ValueError("Unknown or repeated bank id")
        length = len(banks[identity]["fields"])
        for key in ("high", "low"):
            order = layout[key]
            if not isinstance(order, list) or len(order) != length or any(type(index) is not int for index in order):
                raise ValueError("Indices must be integers")
            if sorted(order) != list(range(length)):
                raise ValueError("Not a permutation")
        indexed[identity] = layout
    return indexed


def evaluate_design(document, spec, seeds):
    indexed = validate_design(document, spec)
    metrics = []
    all_passed = True
    for bank in spec["banks"]:
        fields = np.array(bank["fields"])
        layout = indexed[bank["id"]]
        for scale in spec["scales"]:
            records = []
            for seed in seeds:
                perturbation = np.zeros(len(fields)) if seed is None else np.random.default_rng(seed).uniform(-spec["jitter"], spec["jitter"], len(fields))
                perturbed = scale * fields + perturbation
                high = observables(perturbed[layout["high"]])
                low = observables(perturbed[layout["low"]])
                records.append({"r_high": high["r"], "r_low": low["r"],
                                "f_high": high["f"], "f_low": low["f"]})
            matching = np.array([abs(record["r_high"] - record["r_low"]) for record in records])
            separation = np.array([record["f_high"] - record["f_low"] for record in records])
            mean_gap = float(np.mean(matching))
            max_gap = float(np.max(matching))
            mean_separation = float(np.mean(separation))
            min_separation = float(np.min(separation))
            target = spec["targets"]
            margins = [target["mean_abs_r_difference_max"] / max(mean_gap, 1e-15),
                       target["max_abs_r_difference_max"] / max(max_gap, 1e-15),
                       mean_separation / target["mean_f_separation_min"],
                       min_separation / target["min_f_separation_min"]]
            score = max(0.0, min(1.0, min(margins)))
            passed = min(margins) >= 1.0
            all_passed = all_passed and passed
            metrics.append({"bank": bank["id"], "scale": scale, "mean_abs_r_difference": mean_gap,
                            "max_abs_r_difference": max_gap, "mean_f_separation": mean_separation,
                            "min_f_separation": min_separation, "score": score, "passed": bool(passed),
                            "records": records})
    return {"core_score": 100 * float(np.mean([record["score"] for record in metrics])),
            "worst_family_score": 100 * min(record["score"] for record in metrics),
            "passed": bool(all_passed), "valid": True, "families": metrics,
            "reason": "All matching and separation constraints met" if all_passed else "Diagnostic matching or robust separation misses a fixed threshold"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("design", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    spec = json.loads((Path(__file__).resolve().parents[1] / "input/spec.json").read_text())
    with threadpool_limits(1):
        result = evaluate_design(json.loads(arguments.design.read_text()), spec, spec["public_seeds"])
    text = json.dumps(result, indent=2, allow_nan=False)
    if arguments.output:
        arguments.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
