import argparse
import json
import time

import search
import numpy as np
from scipy.optimize import minimize


class Objective:
    def __init__(self, sign, sigma, limit):
        self.sign = sign
        self.sigma = sigma
        self.limit = limit
        self.last = None

    def calculate(self, controls):
        if self.last is None or not np.array_equal(controls, self.last):
            self.result = search.evaluate(controls, hessian=True)
            self.last = controls.copy()
        return self.result

    def fun(self, controls):
        return -self.sign * self.calculate(controls)["tail"] * 1e6

    def jac(self, controls):
        return -self.sign * self.calculate(controls)["tail_gradient"] * 1e6

    def constraints(self, controls):
        result = self.calculate(controls)
        sensitivity = result["sensitivity"]
        norms = np.maximum(np.linalg.norm(sensitivity, axis=1), 1e-20)
        uncertainty = 0.001 / np.sqrt(3) * self.sigma * norms * 1e6
        uncertainty_gradient = 0.001 / np.sqrt(3) * self.sigma * np.einsum("ab,abc->ac", sensitivity, result["curvature"]) / norms[:, None] * 1e6
        scale = np.array([100, 10, 10])
        values = np.r_[self.limit - result["triples"] * 1e6 - uncertainty,
                       self.limit + result["triples"] * 1e6 - uncertainty,
                       (result["physical"] - [0.952, 0.41, 0.61]) * scale]
        derivatives = np.vstack([-result["triple_gradient"] * 1e6 - uncertainty_gradient,
                                  result["triple_gradient"] * 1e6 - uncertainty_gradient,
                                  result["physical_gradient"] * scale[:, None]])
        return values, derivatives


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--sigma", type=float, default=3.5)
    parser.add_argument("--limit", type=float, default=0.9)
    parser.add_argument("--prefix", default="grow")
    parser.add_argument("--files", nargs="*")
    arguments = parser.parse_args()
    random = np.random.default_rng(258294)
    started = time.monotonic()
    best = 0
    for run in range(arguments.count):
        if arguments.files:
            initial = search.load(arguments.files[run % len(arguments.files)])
        else:
            initial = random.uniform(-1, 1, 42) * np.r_[np.full(21, 0.005), np.full(21, 0.599)]
            if run == 0:
                initial[:] = 0
            if run % 3 == 2:
                position = random.integers(21)
                initial[position] = random.uniform(-0.44, 0.44)
        sign = -1 if run % 4 != 3 else 1
        objective = Objective(sign, arguments.sigma, arguments.limit)
        fit = minimize(objective.fun, initial, jac=objective.jac,
                       constraints={"type": "ineq", "fun": lambda controls: objective.constraints(controls)[0],
                                    "jac": lambda controls: objective.constraints(controls)[1]},
                       bounds=list(zip(-search.BOUND + 0.001, search.BOUND - 0.001)), method="SLSQP",
                       options={"maxiter": arguments.iterations, "ftol": 1e-8, "disp": False})
        result = search.evaluate(fit.x)
        info = search.summary(result)
        info.update(run=run, nit=fit.nit, nfev=fit.nfev, success=bool(fit.success),
                    constraint_min=float(np.min(objective.constraints(fit.x)[0])), seconds=time.monotonic() - started)
        search.save(fit.x, f"{arguments.prefix}_{run:03d}.json")
        ranking = min(info["tail_micro"] / 50, info["robust_factor"])
        if ranking > best and np.all(result["physical"] >= [0.95, 0.4, 0.6]):
            best = ranking
            search.save(fit.x, f"{arguments.prefix}_best.json")
        print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
