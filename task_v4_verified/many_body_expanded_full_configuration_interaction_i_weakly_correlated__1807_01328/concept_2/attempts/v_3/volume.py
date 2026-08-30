import argparse
import json
import time

import search
import probability
import numpy as np
from scipy.linalg import solve
from scipy.optimize import minimize


class Volume:
    def __init__(self, controls, beta):
        self.base = probability.Objective(controls, samples=1024, seed=816365, vv_rate=.95)
        self.beta = beta
        self.last = None

    def calculate(self, controls):
        if self.last is not None and np.array_equal(controls, self.last):
            return
        self.last = controls.copy()
        self.base.calculate(controls)
        result = self.base.result
        factor = 1000 / np.sqrt(3)
        sensitivity = result["sensitivity"] * factor
        mean = result["triples"] * 1e6
        covariance = sensitivity @ sensitivity.T + np.eye(35) * self.beta ** 2
        inverse = solve(covariance, np.eye(35), assume_a="pos", check_finite=False)
        weighted_mean = inverse @ mean
        weighting = inverse - np.outer(weighted_mean, weighted_mean)
        self.value = .5 * np.linalg.slogdet(covariance)[1] + .5 * mean @ weighted_mean
        self.gradient = factor * np.einsum("ab,abc->c", weighting @ sensitivity, result["curvature"]) + weighted_mean @ result["triple_gradient"] * 1e6

    def fun(self, controls):
        self.calculate(controls)
        return self.value

    def jac(self, controls):
        self.calculate(controls)
        return self.gradient

    def constraints(self, controls):
        self.calculate(controls)
        values, derivatives = self.base.constraints(controls)
        result = self.base.result
        return np.r_[values, self.base.sign * result["tail"] * 1e6 - 100], np.vstack([derivatives, self.base.sign * result["tail_gradient"] * 1e6])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--iterations", type=int, default=220)
    arguments = parser.parse_args()
    started = time.monotonic()
    for position, name in enumerate(arguments.files):
        for beta in [.3, .7]:
            controls = search.load(name)
            objective = Volume(controls, beta)
            fit = minimize(objective.fun, controls, jac=objective.jac,
                           constraints={"type": "ineq", "fun": lambda current: objective.constraints(current)[0],
                                        "jac": lambda current: objective.constraints(current)[1]},
                           bounds=list(zip(-search.BOUND + .001, search.BOUND - .001)), method="SLSQP",
                           options={"maxiter": arguments.iterations, "ftol": 1e-6, "disp": False})
            objective.calculate(fit.x)
            report = search.summary(search.evaluate(fit.x))
            report.update(source=name, beta=beta, predicted=objective.base.predicted,
                          constraint_min=float(np.min(objective.constraints(fit.x)[0])),
                          nit=fit.nit, seconds=time.monotonic()-started)
            search.save(fit.x, f"volume_{position:02d}_{int(beta*10)}.json")
            print(json.dumps(report), flush=True)
