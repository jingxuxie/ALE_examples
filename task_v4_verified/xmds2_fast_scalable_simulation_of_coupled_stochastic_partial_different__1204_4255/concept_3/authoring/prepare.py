import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from field_control import read_json, references


def make_cases():
    protocol = read_json(ROOT / "evaluator/hidden/protocol.json")
    cases = read_json(ROOT / "participant/input/public_cases.json")
    generator = np.random.default_rng(42551204)
    groups = {"interaction": ("g", "self_ratio", "cross_ratio"), "calibration": ("rf_gain", "bias", "gradient"), "trap": ("trap_x", "trap_y", "gradient"), "joint": tuple(protocol["uncertainty"])}
    for family, keys in groups.items():
        for index in range(4):
            case = dict(protocol["nominal"], id=family + "_%02d" % index, family=family)
            for key in keys:
                lower, upper = protocol["uncertainty"][key]
                fraction = generator.uniform(0.1, 0.9)
                if family == "joint" and index < 2:
                    fraction = float(generator.integers(0, 2))
                case[key] = round(lower + (upper - lower) * fraction, 9)
            cases.append(case)
    (ROOT / "evaluator/hidden/cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    return cases


if __name__ == "__main__":
    cases = make_cases()
    for shape in ((80, 40), (112, 56)):
        initial, target, residual = references(cases, shape, ROOT / "evaluator/hidden/references")
        print(json.dumps({"shape": shape, "cases": len(cases), "residual": residual}), flush=True)
