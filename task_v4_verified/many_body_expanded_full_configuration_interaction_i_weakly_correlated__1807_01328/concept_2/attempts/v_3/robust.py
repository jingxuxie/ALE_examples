import argparse
import json
import time

import search
import numpy as np
from scipy.optimize import minimize


class RobustObjective:
    def __init__(self, sign=-1, minimum_tail=65e-6, family="full"):
        self.sign = sign
        self.minimum_tail = minimum_tail
        self.active = search.CONTROL if family == "vv" else np.arange(100)
        self.last_controls = None
        self.calls = 0
        self.started = time.monotonic()

    def calculate(self, variables):
        controls = variables[:-1]
        sigma_multiplier = variables[-1]
        if self.last_controls is None or not np.array_equal(controls, self.last_controls):
            self.result = search.evaluate(controls, hessian=True)
            self.last_controls = controls.copy()
            self.calls += 1
        result = self.result
        sensitivity = result["sensitivity"][:, self.active]
        norms = np.maximum(np.linalg.norm(sensitivity, axis=1), 1e-20)
        sigma = 0.001 / np.sqrt(3) * norms
        sigma_gradient = 0.001 / np.sqrt(3) * np.einsum("ab,abc->ac", sensitivity, result["curvature"][:, self.active]) / norms[:, None]
        triple = result["triples"] * 1e6
        triple_gradient = result["triple_gradient"] * 1e6
        sigma *= 1e6
        sigma_gradient *= 1e6
        tail = self.sign * result["tail"] * 1e6
        tail_gradient = self.sign * result["tail_gradient"] * 1e6
        values = []
        derivatives = []
        for limit, limit_gradient in ((1.0, np.zeros(42)), (tail / 100, tail_gradient / 100)):
            for orientation in (-1, 1):
                values.append(limit - orientation * triple - sigma_multiplier * sigma)
                derivatives.append(np.column_stack([limit_gradient - orientation * triple_gradient - sigma_multiplier * sigma_gradient, -sigma]))
        values.append(np.array([tail - self.minimum_tail * 1e6]))
        derivatives.append(np.r_[tail_gradient, 0][None, :])
        physical_scale = np.array([100, 10, 10])
        values.append((result["physical"] - [0.952, 0.41, 0.61]) * physical_scale)
        derivatives.append(np.column_stack([result["physical_gradient"] * physical_scale[:, None], np.zeros(3)]))
        return np.concatenate(values), np.vstack(derivatives)

    def fun(self, variables):
        return self.calculate(variables)[0]

    def jac(self, variables):
        return self.calculate(variables)[1]


def optimize(initial, iterations, label, minimum_tail, family="full"):
    info = search.summary(search.evaluate(initial))
    objective = RobustObjective(-1 if search.evaluate(initial)["tail"] < 0 else 1, minimum_tail, family)
    variables = np.r_[np.clip(initial, -search.BOUND + 0.00101, search.BOUND - 0.00101), 0.0]
    lower = np.r_[-search.BOUND + 0.001, -5]
    upper = np.r_[search.BOUND - 0.001, 12]
    iteration = 0

    def callback(current):
        nonlocal iteration
        iteration += 1
        if iteration % 25 == 0:
            report = search.summary(search.evaluate(current[:-1]))
            report.update(label=label, iteration=iteration, sigma_multiplier=float(current[-1]),
                          constraint_min=float(np.min(objective.fun(current))), calls=objective.calls,
                          seconds=time.monotonic() - objective.started)
            print(json.dumps(report), flush=True)
            search.save(current[:-1], f"robust_{label}_progress.json")

    gradient = np.r_[np.zeros(42), -1]
    fit = minimize(lambda current: -current[-1], variables, jac=lambda current: gradient,
                   constraints={"type": "ineq", "fun": objective.fun, "jac": objective.jac},
                   bounds=list(zip(lower, upper)), method="SLSQP", callback=callback,
                   options={"maxiter": iterations, "ftol": 1e-7, "disp": False})
    report = search.summary(search.evaluate(fit.x[:-1]))
    report.update(label=label, sigma_multiplier=float(fit.x[-1]), success=bool(fit.success),
                  message=fit.message, constraint_min=float(np.min(objective.fun(fit.x))),
                  calls=objective.calls, seconds=time.monotonic() - objective.started)
    print(json.dumps(report), flush=True)
    search.save(fit.x[:-1], f"robust_{label}.json")
    return fit.x[:-1], report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="*")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=350)
    parser.add_argument("--tail", type=float, default=65)
    parser.add_argument("--prefix", default="robust")
    parser.add_argument("--family", choices=["vv", "full"], default="full")
    arguments = parser.parse_args()
    candidates = arguments.files or [path.name for path in search.ROOT.glob("candidate_*.json")]
    ranked = sorted([(search.summary(search.evaluate(search.load(name)))["robust_factor"], name) for name in candidates], reverse=True)
    print("ranked", ranked, flush=True)
    best = -np.inf
    for position, (ranking, name) in enumerate(ranked[:arguments.count]):
        controls, report = optimize(search.load(name), arguments.iterations, f"{arguments.prefix}_{position:02d}", arguments.tail * 1e-6, arguments.family)
        ranking = report["sigma_multiplier"]
        if ranking > best and np.all(np.array(report["physical"]) >= [0.95, 0.4, 0.6]):
            best = ranking
            search.save(controls, f"{arguments.prefix}_best.json")


if __name__ == "__main__":
    main()
