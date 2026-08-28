import copy
import json
import sys
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

import solver


PARTICIPANT = Path(__file__).resolve().parent.parent / "participant"
sys.path.insert(0, str(PARTICIPANT / "workspace"))
import dense_cluster


def settings(length=4, spin=0.5, potential=4.0, protection="full"):
    return {
        "length": length, "spin": spin, "J": 1.0, "mass": 0.23,
        "electric": 0.5, "V": potential, "protection": protection,
        "coefficients": [(-1.0) ** site * (1.0 + 0.1 * (site % 3)) for site in range(length)],
        "profile": [0.2 * np.sin(1.3 * site) for site in range(length)],
    }


def small_tests():
    parameters = np.array([0.13, 0.17, -0.11])
    for spin, length in [(0.5, 4), (1.0, 3)]:
        for protection in ["full", "linear"]:
            configuration = settings(length, spin, 3.2, protection)
            pairs = [[0, length - 1], [0, 1], [1, 1]]
            times = [0.0, 0.21, 0.7]
            reference = dense_cluster.simulate(configuration, parameters, times, pairs)
            exact = solver.ExactModel(configuration, pairs).simulate(parameters, times)
            error = max(np.max(np.abs(block - reference[name])) for name, block in zip(["density", "violation", "correlation"], exact))
            print("exact agreement", spin, protection, error, flush=True)
            assert error < 2e-12
            evolution = solver.MatrixProductEvolution(configuration, parameters, max_bond=1000, cutoff=1e-15)
            for _ in range(14):
                evolution.step(0.05)
            values = evolution.measure(pairs)
            errors = [np.max(np.abs(block - expected[-1])) for block, expected in zip(values, exact)]
            print("MPS agreement", spin, protection, errors, "discarded", evolution.discarded, flush=True)
            assert max(errors) < 3e-5
    with open(PARTICIPANT / "input" / "example.json") as stream:
        case = json.load(stream)
    start = time.monotonic()
    result = solver.solve(case)
    print("example parameters", result["parameters"], "seconds", time.monotonic() - start, flush=True)
    for name in ["density", "violation", "correlation"]:
        assert np.isfinite(result[name]).all()
    print(json.dumps(result), flush=True)


def convergence_tests():
    parameters = np.array([0.19, 0.21, 0.08])
    for potential in [0.0, 4.0, 12.0]:
        configuration = settings(4, 0.5, potential)
        pairs = [[0, 1], [0, 3]]
        exact = solver.ExactModel(configuration, pairs).simulate(parameters, [2.0])
        previous_error = None
        for timestep in [0.12 / (1 + 0.16 * potential), 0.06 / (1 + 0.16 * potential)]:
            steps = int(np.ceil(2 / timestep))
            evolution = solver.MatrixProductEvolution(configuration, parameters, 128, 1e-14)
            start = time.monotonic()
            for _ in range(steps):
                evolution.step(2 / steps)
            errors = [np.max(np.abs(actual - target[0])) for actual, target in zip(evolution.measure(pairs), exact)]
            print("convergence", potential, 2 / steps, errors, "seconds", time.monotonic() - start, flush=True)
            if previous_error is not None:
                assert max(errors) < previous_error / 8
            previous_error = max(errors)


def medium_sparse_tests():
    parameters = [0.16, 0.16, 0.03]
    for length, spin, potential, duration in [(8, 0.5, 0.0, 4.0), (6, 1.0, 4.0, 3.0)]:
        configuration = settings(length, spin, potential)
        pairs = [[0, 1], [length // 2 - 1, length // 2], [0, length - 1]]
        exact = solver.ExactModel(configuration, pairs).simulate(parameters, [duration])
        steps = int(np.ceil(duration / (0.24 / (1 + 0.16 * potential))))
        evolution = solver.MatrixProductEvolution(configuration, parameters, 512, 1e-13)
        for step in range(steps):
            evolution.step(duration / steps, order=5)
        errors = [np.max(np.abs(actual - target[0])) for actual, target in zip(evolution.measure(pairs), exact)]
        print("medium sparse comparison", length, spin, errors, flush=True)
        assert max(errors) < 1e-5


def recovery_and_symmetry_tests():
    random = np.random.default_rng(953)
    for truth in ([0.027, 0.29, -0.23], [0.28, 0.032, 0.24], [0.16, 0.19, -0.07]):
        records = []
        for potential, spin, protection in [(0.0, 0.5, "full"), (1.4, 1.0, "linear"), (3.1, 0.5, "full")]:
            configuration = settings(2, spin, potential, protection)
            times = [0.0, 0.17, 0.4, 0.8, 1.3, 1.9]
            pairs = [[0, 1]]
            values = solver.ExactModel(configuration, pairs).simulate(truth, times)
            observed = {}
            for name, block in zip(["density", "violation", "correlation"], values):
                observed[name] = (block + random.normal(scale=2e-6, size=block.shape)).tolist()
            records.append({"settings": configuration, "times": times, "pairs": pairs,
                            "observed": observed, "noise_sigma": 2e-6})
        fitted = solver.fit_parameters(records)
        print("recovery", truth, fitted, "error", np.max(np.abs(fitted - truth)), flush=True)
        assert np.max(np.abs(fitted - truth)) < 5e-5
    for spin in [0.5, 1.0]:
        configuration = settings(8, spin, 12.0)
        evolution = solver.MatrixProductEvolution(configuration, [0.0, 0.0, 0.03], 128, 1e-13)
        for step in range(12):
            evolution.step(0.1, order=5)
        density, violation, correlation = evolution.measure([[0, 7], [2, 3]])
        print("fault-free gauge conservation", spin, np.max(violation), flush=True)
        assert np.max(violation) < 1e-9
        unprotected = dict(configuration, V=0.0)
        reference = solver.MatrixProductEvolution(unprotected, [0.0, 0.0, 0.03], 128, 1e-13)
        for step in range(12):
            reference.step(0.1, order=5)
        reference_density, _, _ = reference.measure([[0, 7], [2, 3]])
        protection_error = np.max(np.abs(reference_density - density))
        print("fault-free protection independence", spin, protection_error, flush=True)
        assert protection_error < 1e-9


def irregular_chain_test():
    configuration = settings(24, 0.5, 0.0)
    times = [0.0, 0.11, 0.111, 0.23, 0.4]
    pairs = [[0, 1], [11, 12], [23, 23], [12, 11]]
    density, violation, correlation = solver.simulate_chain(configuration, [0.16, 0.16, 0.03], times, pairs)
    assert density.shape == (5, 24) and violation.shape == (5, 24)
    assert correlation.shape == (5, 4)
    assert all(np.isfinite(block).all() for block in [density, violation, correlation])
    assert np.max(np.abs(correlation[:, 1] - correlation[:, 3])) < 1e-12
    assert np.max(np.abs(correlation[:, 2] - density[:, 23] * (1 - density[:, 23]))) < 1e-12
    print("irregular-time full-chain and pair-order tests passed", flush=True)


def benchmark(length=24, spin=0.5, potential=0.0, duration=3.0):
    configuration = settings(length, spin, potential)
    parameters = [0.16, 0.16, 0.03]
    timestep = 0.12 / (1 + 0.16 * potential)
    evolution = solver.MatrixProductEvolution(configuration, parameters, 128 if spin == 0.5 else 96, 1e-11)
    steps = int(np.ceil(duration / timestep))
    start = time.monotonic()
    for index in range(steps):
        before = time.monotonic()
        evolution.step(duration / steps)
        if index % 4 == 0 or index == steps - 1:
            print("benchmark", length, spin, potential, "time", (index + 1) * duration / steps,
                  "wall", time.monotonic() - start, "step", time.monotonic() - before,
                  "bond", max(tensor.shape[-1] for tensor in evolution.tensors),
                  "discarded", evolution.discarded, flush=True)
    values = evolution.measure([[0, 1], [length // 2, length // 2 + 1], [0, length - 1]])
    print("observables", [value.tolist() for value in values], flush=True)


if __name__ == "__main__":
    with threadpool_limits(1):
        if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
            benchmark(int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
        else:
            small_tests()
            convergence_tests()
            recovery_and_symmetry_tests()
            medium_sparse_tests()
            irregular_chain_test()
