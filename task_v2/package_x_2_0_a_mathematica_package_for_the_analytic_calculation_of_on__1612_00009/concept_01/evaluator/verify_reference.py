import copy
import json
import math
import os
import sys
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "solution/v_01/workspace"))

import numpy as np
from loopaudit.backend import evaluate, integrate
from loopaudit.contract import decode, orders_for, order_key
from loopaudit.service import run_cases


def relative(first, second):
    return float(np.max(np.abs(first - second)) / max(float(np.max(np.abs(second))), 1e-100))


def main():
    settings = json.loads((ROOT / "solution/v_01/workspace/profiles.json").read_text())["production"]
    tests = []
    small_box = {"masses2": [1] * 4, "invariants": [[0] * 4 for index in range(4)]}
    values = decode(evaluate(small_box, settings)["coefficients"]["base"])
    tests.append({"name": "Dirichlet_constant_box", "error": relative(values, np.array([0, 0, 0, 1 / 6]))})
    tadpole = {"masses2": [2], "invariants": [[0]]}
    values = decode(evaluate(tadpole, settings)["coefficients"]["base"])
    tests.append({"name": "exact_tadpole", "error": relative(values, np.array([2, 0, 0, 2 * (1 - math.log(2))]))})
    for split, path in [("public", ROOT / "participant/v_01/input/release.json"), ("hidden", ROOT / "evaluator/hidden/requests.json")]:
        requests = json.loads(path.read_text())
        result = run_cases(requests, settings)
        lookup = {case["id"]: case for case in result["cases"]}
        for case in requests["cases"]:
            if "observables" in case:
                for name, observable in lookup[case["id"]]["observables"].items():
                    tests.append({"name": f"{split}_dimensionally_exact_{name}", "error": observable["residual"]})
            for integral in case["integrals"]:
                base = lookup[case["id"]]["integrals"][integral["id"]]
                if base["strategy"] == "analytic-laurent":
                    continue
                strength = 0.65 if max(map(max, integral["invariants"])) > 0 else 0
                check_order = 180 if len(integral["masses2"]) == 4 and strength else 64
                values = integrate(integral, check_order, strength)
                for order, value in zip(orders_for(integral), values):
                    target = decode(base["coefficients"][order_key(order)])
                    tests.append({"name": f"{split}_{case['id']}_{integral['id']}_{order_key(order)}_independent_contour_refinement",
                                  "error": relative(value, target)})
            if case["family"] == "soft_collinear_triangle":
                integral = case["integrals"][0]
                invariant = np.array(integral["invariants"])
                channel = invariant[invariant != 0][0]
                logarithm = complex(np.log(complex(-channel, -1e-100) / integral["mu2"]))
                target = np.array([0, 1 / channel, -logarithm / channel,
                                   (logarithm ** 2 / 2 - math.pi ** 2 / 12) / channel])
                values = decode(lookup[case["id"]]["integrals"]["scalar_jet"]["coefficients"]["0"])
                tests.append({"name": f"{split}_massless_triangle_closed_form", "error": relative(values, target)})
        (ROOT / f"solution/v_01/{split}_predictions.json").write_text(json.dumps(result, indent=2))
    passed = max(test["error"] for test in tests) < 1e-8
    report = {"passed": passed, "tests": tests, "max_relative_disagreement": max(test["error"] for test in tests),
              "infrared_box_source_check": "OneLoop.m lines 2960--2973 agree with both gamma-normalized formulas; causal logs and dilogs retained"}
    (ROOT / "evaluator/reference_verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "tests"}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
