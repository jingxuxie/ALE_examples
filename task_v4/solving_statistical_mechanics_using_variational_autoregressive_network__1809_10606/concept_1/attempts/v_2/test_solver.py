import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import time
import unittest

import numpy as np
from scipy.optimize import check_grad
from scipy.special import expit, logsumexp

import solve


def target(instance):
    spins = solve.configurations(instance["n"])
    couplings = np.asarray(instance["couplings"])
    fields = np.asarray(instance["fields"])
    log_probability = np.sum((spins @ couplings) * spins, axis=1) / 2 + spins @ fields
    return spins, log_probability - logsumexp(log_probability)


def metrics(instance, model):
    spins, log_target = target(instance)
    logs = []
    for mass, weights, biases in zip(model["mixing"], model["weights"], model["biases"]):
        logits = spins @ np.array(weights).T + biases
        logs.append(np.log(mass) - np.logaddexp(0, -spins * logits).sum(axis=1))
    log_model = logsumexp(logs, axis=0)
    return {"kl": float(np.exp(log_model) @ (log_model - log_target)),
            "ess": float(np.exp(-logsumexp(2 * log_target - log_model))),
            "normalization": float(np.exp(logsumexp(log_model)))}


def random_instance(count, seed=11):
    rng = np.random.default_rng(seed)
    couplings = np.tril(rng.normal(size=(count, count)) * 0.4, -1)
    couplings += couplings.T
    return {"n": count, "couplings": couplings.tolist(), "fields": (rng.normal(size=count) * 0.2).tolist()}


def validate(model, count):
    assert set(model) == {"mixing", "weights", "biases", "orders"}
    mixing = np.asarray(model["mixing"])
    components = len(mixing)
    assert 1 <= components <= 8
    assert np.all(np.isfinite(mixing)) and np.all(mixing > 0)
    assert abs(mixing.sum() - 1) < 1e-10
    weights = np.asarray(model["weights"])
    biases = np.asarray(model["biases"])
    orders = np.asarray(model["orders"])
    assert weights.shape == (components, count, count)
    assert biases.shape == (components, count)
    assert orders.shape == (components, count)
    assert np.all(np.isfinite(weights)) and np.all(np.isfinite(biases))
    assert np.max(np.abs(biases) + np.abs(weights).sum(axis=2)) <= 60
    for component in range(components):
        order = orders[component]
        assert sorted(order.tolist()) == list(range(count))
        permuted = weights[component][np.ix_(order, order)]
        assert np.all(np.triu(permuted) == 0)
    assert len(json.dumps(model).encode()) <= 1024 * 1024


class SolverTests(unittest.TestCase):
    def test_logistic_projection(self):
        basis = solve.Basis(5)
        design = basis.design[4]
        coefficients = np.array([0.4, -0.7, 0.2, 0.8, -0.3])
        probability = expit(design @ coefficients)
        mass = np.arange(1, len(design) + 1, dtype=float)
        mass /= mass.sum()
        fitted = solve.fit_logistic(design, mass * probability, mass * (1 - probability), np.zeros(5))
        np.testing.assert_allclose(fitted, coefficients, atol=2e-7)

    def test_logistic_projection_from_saturated_initialization(self):
        basis = solve.Basis(5)
        design = basis.design[4]
        coefficients = np.array([0.4, -0.7, 0.2, 0.8, -0.3])
        probability = expit(design @ coefficients)
        mass = np.full(len(design), 1 / len(design))
        initial = np.array([15.0, -10.0, 10.0, -5.0, 5.0])
        fitted = solve.fit_logistic(design, mass * probability, mass * (1 - probability), initial)
        np.testing.assert_allclose(fitted, coefficients, atol=2e-6)

    def test_expired_budget_still_produces_valid_parameters(self):
        instance = random_instance(8)
        spins, log_target = target(instance)
        cells = solve.partition(log_target, np.asarray(instance["couplings"]), np.asarray(instance["fields"]),
                                [0, 1, 2], solve.Basis(5, deadline=time.monotonic() - 1))
        model = solve.artifact(cells, 8)
        validate(model, 8)
        self.assertLess(abs(metrics(instance, model)["normalization"] - 1), 2e-13)

    def test_six_spin_exactness_and_artifact(self):
        instance = random_instance(6)
        model = solve.solve_instance(instance, seconds=5)
        validate(model, 6)
        result = metrics(instance, model)
        self.assertLess(abs(result["normalization"] - 1), 2e-13)
        self.assertLess(result["kl"], 1e-9)
        self.assertGreater(result["ess"], 1 - 1e-8)

    def test_independent_spins(self):
        instance = {"n": 8, "couplings": np.zeros((8, 8)).tolist(), "fields": np.linspace(-2, 2, 8).tolist()}
        model = solve.solve_instance(instance, seconds=5)
        validate(model, 8)
        result = metrics(instance, model)
        self.assertLess(result["kl"], 1e-9)
        self.assertGreater(result["ess"], 1 - 1e-8)

    def test_exact_refinement_gradient(self):
        instance = random_instance(8)
        spins, log_target = target(instance)
        cell = solve.Cell(log_target, np.asarray(instance["couplings"]), np.asarray(instance["fields"]),
                          {0: -1, 3: 1, 6: -1}, solve.Basis(5))
        candidate = cell.fit(cell.free[::-1])
        objective = solve.Refinement(candidate, time.monotonic() + 20)
        vector = np.random.default_rng(33).normal(size=objective.size) * 0.01
        error = check_grad(lambda vector: objective.evaluate(vector)[0], lambda vector: objective.evaluate(vector)[1], vector)
        self.assertLess(error, 2e-6)

    def test_partition_certificate(self):
        instance = random_instance(8, seed=42)
        spins, log_target = target(instance)
        cells = solve.partition(log_target, np.asarray(instance["couplings"]), np.asarray(instance["fields"]),
                                [6, 2, 4], solve.Basis(5))
        model = solve.artifact(cells, 8)
        validate(model, 8)
        score, reverse, ess = solve.summary(cells)
        result = metrics(instance, model)
        self.assertLess(abs(reverse - result["kl"]), 1e-12)
        self.assertLess(abs(ess - result["ess"]), 1e-12)

    def test_refinement_preserves_finite_parameters(self):
        instance = random_instance(9, seed=913)
        spins, log_target = target(instance)
        cell = solve.Cell(log_target, np.asarray(instance["couplings"]), np.asarray(instance["fields"]),
                          {0: 1, 1: -1, 8: 1}, solve.Basis(6))
        candidate = cell.fit(cell.free)
        refined = solve.Refinement(candidate, time.monotonic() + 20).fit()
        self.assertTrue(all(np.all(np.isfinite(parameters)) for parameters in refined.parameters))
        self.assertLessEqual(max(np.abs(parameters).sum() for parameters in refined.parameters), 59)
        self.assertLessEqual(refined.reverse + 0.03 * refined.forward + 0.002 * np.expm1(refined.log_chi),
                             candidate.reverse + 0.03 * candidate.forward + 0.002 * np.expm1(candidate.log_chi) + 1e-10)


if __name__ == "__main__":
    unittest.main()
