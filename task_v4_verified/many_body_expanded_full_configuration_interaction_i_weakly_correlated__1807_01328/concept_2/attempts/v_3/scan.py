import argparse
import json

import search
import numpy as np


def proxy(controls, pools):
    result = search.evaluate(controls)
    info = search.summary(result)
    if np.any(result["physical"] < [0.95, 0.4, 0.6]):
        return None
    center = search.BASE.copy()
    center[search.CONTROL] = controls
    bounds = np.r_[np.full(10, np.inf), np.full(45, 0.45), np.full(45, 0.6)]
    lower = np.maximum(center - 0.001, -bounds)
    upper = np.minimum(center + 0.001, bounds)
    info["nominal_score"] = min(1, 1 / max(info["parent_micro"], 1e-4), info["tail_micro"] / 50, info["ratio"] / 100)
    for family, uniforms in pools.items():
        active = search.CONTROL if family == "vv" else np.arange(100)
        directions = np.zeros((len(uniforms), 100))
        directions[:, active] = lower[active] + uniforms * (upper[active] - lower[active]) - center[active]
        triples = result["triples"][None, :] + directions @ result["sensitivity"].T
        tail = np.abs(result["tail"] + directions @ result["tail_sensitivity"])
        parents = np.max(np.abs(triples), axis=1)
        passed = (parents <= 1e-6) & (tail >= 50e-6) & (tail >= 100 * parents)
        info[family] = float(np.mean(passed))
    info["score"] = (info["nominal_score"] + min(1, info["vv"] / .95) + min(1, info["full"] / .95)) / 3
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=512)
    parser.add_argument("--seed", type=int, default=438662)
    parser.add_argument("--output", default="scan.json")
    arguments = parser.parse_args()
    pools = search.assay.training_uniforms(arguments.seed, arguments.samples)
    records = []
    for path in sorted(search.ROOT.glob("*.json")):
        try:
            controls = search.load(path.name)
        except (ValueError, TypeError, KeyError):
            continue
        info = proxy(controls, pools)
        if info is not None:
            info["file"] = path.name
            records.append(info)
    records.sort(key=lambda row: row["score"], reverse=True)
    (search.ROOT / arguments.output).write_text(json.dumps(records, indent=2) + "\n")
    for row in records[:30]:
        print(json.dumps(row), flush=True)
