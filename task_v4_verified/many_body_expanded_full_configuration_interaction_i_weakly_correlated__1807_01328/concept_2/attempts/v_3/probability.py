import argparse
import json
import time

import search
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


class Objective:
    def __init__(self, initial, samples=256, seed=376052, mode="hinge", full_weight=1, vv_sigma=0, vv_rate=0, temperature=.16):
        if samples <= 512:
            pools = search.assay.training_uniforms(seed, samples)
        else:
            streams = np.random.SeedSequence(seed).spawn(2)
            pools = {family: np.random.Generator(np.random.PCG64(stream)).random((samples, dimension))
                     for family, dimension, stream in zip(("vv", "full"), (42, 100), streams)}
        self.directions = []
        for family in ("vv", "full"):
            directions = np.zeros((samples, 100))
            active = search.CONTROL if family == "vv" else np.arange(100)
            directions[:, active] = (pools[family] * 2 - 1) * 0.001
            self.directions.append(directions)
        self.directions = np.vstack(self.directions)
        self.weights = np.r_[np.ones(samples), np.full(samples, full_weight)]
        self.weights /= self.weights.sum()
        self.samples = samples
        self.sign = np.sign(search.evaluate(initial)["tail"])
        self.mode = mode
        self.vv_sigma = vv_sigma
        self.vv_rate = vv_rate
        self.temperature = temperature
        self.last = None
        self.calls = 0

    def calculate(self, controls):
        if self.last is not None and np.array_equal(controls, self.last):
            return
        self.last = controls.copy()
        self.calls += 1
        result = search.evaluate(controls, hessian=True)
        self.result = result
        triples = (result["triples"][None, :] + self.directions @ result["sensitivity"].T) * 1e6
        tail = self.sign * (result["tail"] + self.directions @ result["tail_sensitivity"]) * 1e6
        tail_derivative = self.sign * (result["tail_gradient"][None, :] + self.directions @ result["tail_curvature"]) * 1e6
        maximum = np.argmax(np.abs(triples), axis=1)
        selected = triples[np.arange(len(triples)), maximum]
        parent = np.abs(selected)
        parent_derivative = np.sign(selected)[:, None] * (result["triple_gradient"][maximum] + np.einsum("ab,abc->ac", self.directions, result["curvature"][maximum])) * 1e6
        ratio_limit = tail / 100
        parent_violation = parent - np.minimum(0.99, ratio_limit)
        parent_derivative -= np.where((ratio_limit < 0.99)[:, None], tail_derivative / 100, 0)
        tail_violation = (51 - tail) / 50
        choose_tail = tail_violation > parent_violation
        violation = np.maximum(parent_violation, tail_violation)
        derivative = np.where(choose_tail[:, None], -tail_derivative / 50, parent_derivative)
        vv_failures = expit(violation[:self.samples] / 0.05)
        self.vv_chance = float(np.mean(1 - vv_failures))
        self.vv_chance_gradient = -(vv_failures * (1 - vv_failures) / 0.05) @ derivative[:self.samples] / self.samples
        self.predicted = [float(np.mean(violation[section * self.samples:(section + 1) * self.samples] <= 0)) for section in range(2)]
        if self.mode == "hinge":
            temperature = 0.12
            factors = expit(violation / temperature)
            self.value = float(self.weights @ (temperature * np.logaddexp(0, violation / temperature)))
            self.gradient = (self.weights * factors) @ derivative
        else:
            temperature = self.temperature
            factors = expit(violation / temperature)
            self.value = float(self.weights @ factors)
            self.gradient = (self.weights * factors * (1 - factors) / temperature) @ derivative

    def fun(self, controls):
        self.calculate(controls)
        return self.value

    def jac(self, controls):
        self.calculate(controls)
        return self.gradient

    def constraints(self, controls):
        self.calculate(controls)
        result = self.result
        tail = self.sign * result["tail"] * 1e6
        tail_gradient = self.sign * result["tail_gradient"] * 1e6
        values = []
        gradients = []
        for limit, limit_gradient in ((0.98, np.zeros(42)), (tail / 100 - 0.01, tail_gradient / 100)):
            for orientation in (-1, 1):
                values.append(limit - orientation * result["triples"] * 1e6)
                gradients.append(limit_gradient - orientation * result["triple_gradient"] * 1e6)
        if self.vv_sigma:
            sensitivity = result["triple_gradient"]
            norms = np.maximum(np.linalg.norm(sensitivity, axis=1), 1e-20)
            uncertainty = self.vv_sigma * 1000 / np.sqrt(3) * norms
            uncertainty_gradient = self.vv_sigma * 1000 / np.sqrt(3) * np.einsum("ab,abc->ac", sensitivity, result["curvature"][:, search.CONTROL]) / norms[:, None]
            for limit, limit_gradient in ((0.99, np.zeros(42)), (tail / 100 - 0.01, tail_gradient / 100)):
                for orientation in (-1, 1):
                    values.append(limit - orientation * result["triples"] * 1e6 - uncertainty)
                    gradients.append(limit_gradient - orientation * result["triple_gradient"] * 1e6 - uncertainty_gradient)
        if self.vv_rate:
            values.append(np.array([(self.vv_chance - self.vv_rate) * 10]))
            gradients.append(self.vv_chance_gradient[None, :] * 10)
        values.append(np.array([tail - 54]))
        gradients.append(tail_gradient[None, :])
        scale = np.array([100, 10, 10])
        values.append((result["physical"] - [0.952, 0.41, 0.61]) * scale)
        gradients.append(result["physical_gradient"] * scale[:, None])
        return np.concatenate(values), np.vstack(gradients)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--prefix", default="probability")
    parser.add_argument("--full-weight", type=float, default=1)
    parser.add_argument("--vv-sigma", type=float, default=0)
    parser.add_argument("--vv-rate", type=float, default=0)
    parser.add_argument("--mode", choices=["both", "hinge", "probability"], default="both")
    parser.add_argument("--seed", type=int, default=376052)
    parser.add_argument("--temperature", type=float, default=.16)
    arguments = parser.parse_args()
    started = time.monotonic()
    for position, name in enumerate(arguments.files):
        controls = search.load(name)
        modes = ("hinge", "probability") if arguments.mode == "both" else (arguments.mode,)
        for mode in modes:
            objective = Objective(controls, arguments.samples, seed=arguments.seed, mode=mode, full_weight=arguments.full_weight, vv_sigma=arguments.vv_sigma, vv_rate=arguments.vv_rate, temperature=arguments.temperature)
            fit = minimize(objective.fun, controls, jac=objective.jac,
                           constraints={"type": "ineq", "fun": lambda current: objective.constraints(current)[0],
                                        "jac": lambda current: objective.constraints(current)[1]},
                           bounds=list(zip(-search.BOUND + 0.001, search.BOUND - 0.001)), method="SLSQP",
                           options={"maxiter": arguments.iterations, "ftol": 1e-6, "disp": False})
            controls = fit.x
            objective.calculate(controls)
            report = search.summary(search.evaluate(controls))
            report.update(source=name, position=position, mode=mode, predicted=objective.predicted,
                          objective=float(fit.fun), nit=fit.nit, nfev=fit.nfev,
                          constraint_min=float(np.min(objective.constraints(controls)[0])),
                          seconds=time.monotonic() - started)
            search.save(controls, f"{arguments.prefix}_{position:03d}_{mode}.json")
            print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
