import argparse
import json
import time

import search
import numpy as np
from scipy.optimize import least_squares


class Objective:
    def __init__(self, target, sensitivity_weight=3.5):
        self.target = target
        self.sensitivity_weight = sensitivity_weight
        self.last = None

    def calculate(self, controls):
        if self.last is not None and np.array_equal(self.last, controls):
            return self.residual, self.jacobian
        self.last = controls.copy()
        result = search.evaluate(controls, hessian=True)
        self.result = result
        sensitivity = result["sensitivity"]
        norms = np.maximum(np.linalg.norm(sensitivity, axis=1), 1e-20)
        uncertainty = 0.001 / np.sqrt(3) * norms
        uncertainty_gradient = 0.001 / np.sqrt(3) * np.einsum("ab,abc->ac", sensitivity, result["curvature"]) / norms[:, None]
        violation = np.minimum(result["physical"] - [0.952, 0.41, 0.61], 0)
        physical_scale = np.array([2000, 100, 100])
        self.residual = np.r_[result["triples"] * 1e6,
                              uncertainty * (1e6 * self.sensitivity_weight),
                              (result["tail"] - self.target) * 1e6,
                              violation * physical_scale]
        self.jacobian = np.vstack([result["triple_gradient"] * 1e6,
                                   uncertainty_gradient * (1e6 * self.sensitivity_weight),
                                   result["tail_gradient"] * 1e6,
                                   result["physical_gradient"] * (physical_scale * (violation < 0))[:, None]])
        return self.residual, self.jacobian

    def fun(self, controls):
        return self.calculate(controls)[0]

    def jac(self, controls):
        return self.calculate(controls)[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--iterations", type=int, default=160)
    parser.add_argument("--seed", type=int, default=419703)
    parser.add_argument("--weight", type=float, default=3.5)
    parser.add_argument("--prefix", default="smooth")
    parser.add_argument("--files", nargs="*")
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    started = time.monotonic()
    best = 0
    for run in range(arguments.count):
        if arguments.files:
            initial = search.load(arguments.files[run % len(arguments.files)])
            if run >= len(arguments.files):
                initial += random.normal(size=42) * np.r_[np.full(21, 0.015), np.full(21, 0.1)]
        else:
            scale = [0.01, 0.03, 0.07, 0.15, 0.3][run % 5]
            initial = random.uniform(-1, 1, 42) * np.r_[np.full(21, scale), np.full(21, 0.59)]
            if run % 3 == 1:
                initial[:21] *= 0.1
                for position, (source, destination) in enumerate(search.VIRTUAL_EDGES):
                    if 3 in (source, destination):
                        initial[position] = random.uniform(-0.42, 0.42)
        initial = np.clip(initial, -search.BOUND + 0.00101, search.BOUND - 0.00101)
        target = (-1 if run % 5 != 4 else 1) * (100e-6 if run % 7 != 6 else 60e-6)
        if arguments.files:
            target = np.sign(search.evaluate(initial)["tail"]) * 100e-6
        objective = Objective(target, arguments.weight)
        fit = least_squares(objective.fun, initial, jac=objective.jac,
                            bounds=(-search.BOUND + 0.001, search.BOUND - 0.001),
                            max_nfev=arguments.iterations, ftol=1e-8, xtol=1e-9, gtol=1e-7)
        result = search.evaluate(fit.x)
        info = search.summary(result)
        info.update(run=run, nfev=fit.nfev, cost=float(fit.cost), seconds=time.monotonic() - started)
        search.save(fit.x, f"{arguments.prefix}_{run:03d}.json")
        if info["robust_factor"] > best and np.all(result["physical"] >= [0.95, 0.4, 0.6]):
            best = info["robust_factor"]
            search.save(fit.x, f"{arguments.prefix}_best.json")
        print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
