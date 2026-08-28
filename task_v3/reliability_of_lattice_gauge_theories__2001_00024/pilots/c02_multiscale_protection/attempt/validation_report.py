import json
from pathlib import Path

import numpy as np


def load(name):
    with open(name) as stream:
        return json.load(stream)


def difference(first, second):
    result = {}
    for name in ["density", "violation", "correlation"]:
        residual = np.asarray(first[name]) - np.asarray(second[name])
        result[name] = {
            "max_absolute": float(np.max(np.abs(residual))),
            "rms": float(np.sqrt(np.mean(residual ** 2))),
            "final_time_rms": float(np.sqrt(np.mean(residual[-1] ** 2))),
        }
    return result


def main():
    report = {}
    full = load("chain_24_half_256.json")
    randomized = load("chain_24_half_randomized.json")
    report["randomized_versus_full_svd_at_bond_256"] = difference(randomized, full)
    if Path("chain_24_half_128.json").exists():
        report["bond_128_versus_256"] = difference(load("chain_24_half_128.json"), randomized)
    report["stress_tests"] = []
    for name, budget in [("chain_64_one_linear.json", 240), ("chain_64_half_unprotected.json", 900)]:
        if not Path(name).exists():
            continue
        data = load(name)
        report["stress_tests"].append({
            "length": data["settings"]["length"],
            "spin": data["settings"]["spin"],
            "V": data["settings"]["V"],
            "protection": data["settings"]["protection"],
            "final_time": data["times"][-1],
            "requested_budget_seconds": budget,
            "elapsed_seconds": data["elapsed"],
            "peak_memory_mib": data["peak_memory_mib"],
            "all_finite": all(bool(np.isfinite(data[block]).all()) for block in ["density", "violation", "correlation"]),
        })
    with open("validation.json", "w") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
