import sys

sys.dont_write_bytecode = True

import importlib.util
import itertools
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parents[1]


def main():
    specification = importlib.util.spec_from_file_location("old_public", ORIGINAL / "participant/workspace/check.py")
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    graph = json.loads((ORIGINAL / "participant/input/graph.json").read_text())
    projection = np.zeros((39, 20))
    for edge in graph["edges"]:
        projection[edge["id"], edge["detectors"]] = 1 / len(edge["detectors"])
    directions = []
    for family, count in (("rows", 4), ("columns", 5)):
        for tail in itertools.product((-1, 1), repeat=count - 1):
            signs = [1, *tail]
            if min(signs) == 1:
                continue
            field = [signs[detector % 4 if family == "rows" else detector // 4] for detector in range(20)]
            directions.append({"name": family + ":" + "".join("+" if sign > 0 else "-" for sign in signs), "field": field})
    output = {}
    for label, relative in (("known", "adversary/known_witness.json"), ("v2", "attempts/v_2/witness.json")):
        data = checker.load_submission(ORIGINAL / relative)
        rates = np.array(data["probabilities"])
        physical = checker.check(data)["physical_class"]
        lines = []
        for direction in directions:
            raw = projection @ direction["field"]
            centered = raw - np.dot(rates, raw) / rates.sum()
            levels = centered / np.max(np.abs(centered))
            for background in (0.95, 1.05):
                derivative = math.fsum(abs(level) / ((1 - 0.05 * abs(level)) * (1 - background * rate * (1 + 0.05 * abs(level)))) for level, rate in zip(levels, rates))
                allowance = derivative * 0.00125 + 1e-10
                values = []
                for amplitude in np.linspace(-0.05, 0.05, 41):
                    joint, costs = checker.frontier(rates * (1 + amplitude * levels), data["syndrome"], background)
                    values.append({"amplitude": float(amplitude), "gap": float(costs[1 - physical] - costs[physical]), "posterior": float(joint[1 - physical] / sum(joint)), "log_odds": math.log(float(joint[1 - physical] / joint[physical])), "mass": float(sum(joint))})
                minima = {name: min(value[name] for value in values) for name in ("gap", "posterior", "log_odds", "mass")}
                certificate = {"gap": minima["gap"] - allowance, "posterior": 1 / (1 + math.exp(-(minima["log_odds"] - allowance))), "mass": minima["mass"] * math.exp(-allowance)}
                lines.append({"name": direction["name"], "background": background, "derivative": derivative, "allowance": allowance, "minima": minima, "certificate": certificate, "anchors": values})
        summary = {"certified": {name: min(line["certificate"][name] for line in lines) for name in ("gap", "posterior", "mass")}, "actual": {name: min(line["minima"][name] for line in lines) for name in ("gap", "posterior", "mass")}}
        output[label] = {"summary": summary, "lines": lines}
        print(label, json.dumps(summary))
    (ROOT / "adversary/calibration_draft.json").write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
