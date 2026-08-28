"""Independent contract checks; run with python -m unittest -v test_solve."""

import copy
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import numpy as np
from scipy.special import eval_legendre, roots_legendre

import solve


HERE = Path(__file__).resolve().parent


def encode(values):
    values = np.asarray(values)
    return np.stack([values.real, values.imag], axis=-1).tolist()


def decode(values):
    values = np.asarray(values)
    return values[..., 0] + 1j * values[..., 1]


def reference_time(beta, intervals, values, moments):
    first, second, third = moments
    omega = (2 * np.arange(len(values)) + 1) * math.pi / beta
    frequency = 1j * omega
    residual = values - first / frequency - second / frequency**2 - third / frequency**3
    result = []
    for index in range(intervals):
        tau = beta * index / intervals
        tail = -first / 2 + second * (2 * tau - beta) / 4
        tail += third * tau * (beta - tau) / 4
        correction = math.fsum(
            math.cos(angular * tau) * value.real
            + math.sin(angular * tau) * value.imag
            for angular, value in zip(omega, residual)
        )
        result.append(tail + 2 * correction / beta)
    result.append(-first - result[0])
    return np.array(result)


def reference_afm(case):
    g0 = decode(case["g0_iw"])
    impurity = decode(case["g_iw"])
    flavors, count = g0.shape
    lattice = np.zeros_like(g0)
    weiss = np.zeros_like(g0)
    hybridization = np.zeros_like(g0)
    sigma = 1 / g0 - 1 / impurity
    for index in range(count):
        frequency = 1j * (2 * index + 1) * math.pi / case["beta"]
        for band in range(flavors // 2):
            first, second = 2 * band, 2 * band + 1
            zeta_first = frequency + case["mu"] - case["h"] - sigma[first, index]
            zeta_second = frequency + case["mu"] + case["h"] - sigma[second, index]
            integral = sum(
                weight / (zeta_first * zeta_second - energy * energy)
                for weight, energy in zip(case["dos"][band]["weight"], case["dos"][band]["energy"])
            )
            lattice[first, index] = zeta_second * integral
            lattice[second, index] = zeta_first * integral
            for flavor in (first, second):
                weiss[flavor, index] = 1 / (1 / lattice[flavor, index] + sigma[flavor, index])
                field = -case["h"] if flavor % 2 == 0 else case["h"]
                hybridization[flavor, index] = frequency + case["mu"] + field - 1 / weiss[flavor, index]
    times = []
    for flavor in range(flavors):
        measure = case["dos"][flavor // 2]
        moment = sum(weight * energy**2 for weight, energy in zip(measure["weight"], measure["energy"]))
        chemical = case["mu"] + (-case["h"] if flavor % 2 == 0 else case["h"])
        times.append(reference_time(case["beta"], case["n_tau"], weiss[flavor], [1, -chemical, chemical**2 + moment]))
    return {
        "lattice_iw": encode(lattice),
        "weiss_iw": encode(weiss),
        "hybridization_iw": encode(hybridization),
        "weiss_tau": np.array(times),
    }


def reference_legendre(case):
    beta = case["beta"]
    degree = case["n_legendre"]
    denominator = math.fsum(config["weight"] * config["sign"] for config in case["configurations"])
    green, auxiliary = [], []
    for order in range(degree):
        green_terms, auxiliary_terms = [], []
        for config in case["configurations"]:
            for annihilator, c_time in enumerate(config["c_times"]):
                for creator, cdagger_time in enumerate(config["cdagger_times"]):
                    difference = c_time - cdagger_time
                    wrap = -1 if difference < 0 else 1
                    if difference < 0:
                        difference += beta
                    polynomial = eval_legendre(order, 2 * difference / beta - 1)
                    contribution = config["weight"] * config["sign"] * wrap
                    contribution *= config["matrix"][creator][annihilator] * polynomial
                    green_terms.append(contribution)
                    auxiliary_terms.append(contribution * config["f_prefactor"][annihilator])
        normalization = -math.sqrt(2 * order + 1) / (beta * denominator)
        green.append(normalization * math.fsum(green_terms))
        auxiliary.append(normalization * math.fsum(auxiliary_terms))
    nodes, weights = roots_legendre(320)
    polynomials = np.array([eval_legendre(order, nodes) for order in range(degree)])
    normalization = np.sqrt(2 * np.arange(degree) + 1)
    green_time = (normalization * green) @ polynomials / beta
    auxiliary_time = (normalization * auxiliary) @ polynomials / beta
    green_iw, sigma = [], []
    for index in range(case["n_iw"]):
        phase = np.exp(1j * (2 * index + 1) * math.pi * (nodes + 1) / 2)
        green_value = beta / 2 * np.dot(weights * phase, green_time)
        auxiliary_value = beta / 2 * np.dot(weights * phase, auxiliary_time)
        green_iw.append(green_value)
        sigma.append(auxiliary_value / green_value)
    return {
        "g_legendre": green,
        "f_legendre": auxiliary,
        "g_iw": encode(green_iw),
        "sigma_iw": encode(sigma),
    }


def make_afm(seed, flavors=12, count=40, nodes=256):
    random = np.random.default_rng(seed)
    beta = random.uniform(1, 40)
    chemical = random.uniform(-2, 2)
    field = random.uniform(-1, 1)
    frequency = 1j * (2 * np.arange(count) + 1) * np.pi / beta
    g0, impurity, dos = [], [], []
    for flavor in range(flavors):
        effective = chemical + (-field if flavor % 2 == 0 else field)
        inverse_weiss = frequency + effective - random.uniform(0.1, 2) / (frequency - random.uniform(-1, 1))
        self_energy = random.uniform(-1, 1) + random.uniform(0.1, 3) / (frequency - random.uniform(-1, 1))
        g0.append(1 / inverse_weiss)
        impurity.append(1 / (inverse_weiss - self_energy))
    for band in range(flavors // 2):
        positive = random.uniform(0.01, 2 + band, nodes // 2)
        weight = random.uniform(0.1, 1, nodes // 2)
        weight /= 2 * weight.sum()
        dos.append({"energy": np.concatenate([-positive, positive]).tolist(), "weight": np.tile(weight, 2).tolist()})
    return {
        "family": "afm", "beta": beta, "mu": chemical, "h": field,
        "n_tau": 512, "g0_iw": encode(g0), "g_iw": encode(impurity), "dos": dos,
    }


def make_legendre(seed, degree=32, count=40, config_count=24):
    random = np.random.default_rng(seed)
    beta = random.uniform(1, 40)
    configurations = []
    for index in range(config_count):
        size = int(random.integers(1, 7))
        sign = -1 if index % 3 == 2 else 1
        configurations.append({
            "sign": sign, "weight": float(random.uniform(0.1, 1) if sign < 0 else random.uniform(1, 3)),
            "c_times": random.uniform(0, beta, size).tolist(),
            "cdagger_times": random.uniform(0, beta, size).tolist(),
            "matrix": random.normal(size=(size, size)).tolist(),
            "f_prefactor": random.normal(size=size).tolist(),
        })
    return {"family": "legendre", "beta": beta, "n_legendre": degree, "n_iw": count, "configurations": configurations}


class ContractTests(unittest.TestCase):
    def assert_outputs(self, actual, expected, tolerance=2e-10):
        self.assertEqual(set(actual), set(expected))
        json.dumps(actual, allow_nan=False)
        for key in expected:
            with self.subTest(component=key):
                np.testing.assert_allclose(actual[key], expected[key], atol=tolerance, rtol=tolerance)

    def test_fourier_random_and_minimum_grids(self):
        random = np.random.default_rng(541)
        for count, intervals, beta in [(1, 3, 1), (3, 7, 3), (40, 81, 40), (40, 512, 40), (17, 199, 12.7)]:
            channels = []
            for index in range(12):
                moments = [float(index % 3 == 0), *random.normal(size=2)]
                if index % 3 == 1:
                    moments[1] = 0
                if index % 3 == 2:
                    moments = [0, 0, 0]
                values = random.normal(size=count) + 1j * random.normal(size=count)
                channels.append({"sites": [0, index], "moments": moments, "iw": encode(values)})
            case = {"family": "fourier", "beta": beta, "n_tau": intervals, "channels": channels}
            result = solve.solve(case)
            for channel, times, roundtrip in zip(channels, result["g_tau"], result["iw_roundtrip"]):
                expected = reference_time(beta, intervals, decode(channel["iw"]), channel["moments"])
                np.testing.assert_allclose(times, expected, atol=3e-11, rtol=3e-12)
                np.testing.assert_allclose(roundtrip, channel["iw"], atol=2e-13, rtol=2e-13)
                self.assertAlmostEqual(times[-1] + times[0], -channel["moments"][0], places=12)

    def test_fourier_pure_tail(self):
        beta, intervals, count = 7.0, 25, 8
        frequency = 1j * (2 * np.arange(count) + 1) * np.pi / beta
        for moments in ([1, 0.3, 1.7], [0, 0, -2.1], [0, 0, 0]):
            values = moments[0] / frequency + moments[1] / frequency**2 + moments[2] / frequency**3
            result = solve.fourier({"beta": beta, "n_tau": intervals, "channels": [{"iw": encode(values), "moments": moments}]})
            tau = beta * np.arange(intervals + 1) / intervals
            expected = -moments[0] / 2 + moments[1] * (2 * tau - beta) / 4 + moments[2] * tau * (beta - tau) / 4
            np.testing.assert_allclose(result["g_tau"][0], expected, atol=1e-13)

    def test_afm_all_bands_and_exact_dos(self):
        for seed, flavors, count, nodes in [(42, 2, 1, 2), (26, 4, 13, 14), (95, 6, 23, 38), (7, 12, 40, 256)]:
            with self.subTest(flavors=flavors):
                case = make_afm(seed, flavors, count, nodes)
                self.assert_outputs(solve.solve(case), reference_afm(case))

    def test_afm_atomic_limit(self):
        case = make_afm(84, flavors=8, count=40)
        case["dos"] = [{"energy": [0], "weight": [1]} for band in range(4)]
        result = solve.afm(case)
        frequency = 1j * (2 * np.arange(40) + 1) * np.pi / case["beta"]
        for flavor in range(8):
            chemical = case["mu"] + (-case["h"] if flavor % 2 == 0 else case["h"])
            np.testing.assert_allclose(decode(result["weiss_iw"])[flavor], 1 / (frequency + chemical), atol=1e-14)
        np.testing.assert_allclose(result["hybridization_iw"], 0, atol=1e-14)

    def test_afm_pair_and_band_mapping(self):
        case = make_afm(109)
        baseline = solve.afm(case)
        permutation = np.array([11, 10, 3, 2, 7, 6, 1, 0, 9, 8, 5, 4])
        changed = copy.deepcopy(case)
        changed["h"] *= -1
        changed["g0_iw"] = np.asarray(case["g0_iw"])[permutation].tolist()
        changed["g_iw"] = np.asarray(case["g_iw"])[permutation].tolist()
        changed["dos"] = [case["dos"][index] for index in [5, 1, 3, 0, 4, 2]]
        expected = {key: np.asarray(value)[permutation] for key, value in baseline.items()}
        self.assert_outputs(solve.afm(changed), expected, tolerance=1e-13)

    def test_legendre_signed_matrix_estimators_and_quadrature(self):
        for seed, degree, count, configurations in [(13, 1, 1, 2), (9, 2, 40, 3), (25, 7, 12, 7), (31, 32, 40, 24)]:
            with self.subTest(degree=degree):
                case = make_legendre(seed, degree, count, configurations)
                self.assert_outputs(solve.solve(case), reference_legendre(case), tolerance=3e-9)

    def test_legendre_exactly_one_configuration_sign(self):
        case = make_legendre(77, degree=16, count=20, config_count=1)
        baseline = solve.legendre(case)
        positive = copy.deepcopy(case["configurations"][0])
        negative = copy.deepcopy(positive)
        positive["weight"], positive["sign"] = 3, 1
        negative["weight"], negative["sign"] = 1, -1
        case["configurations"] = [positive, negative]
        self.assert_outputs(solve.legendre(case), baseline, tolerance=1e-13)

    def test_legendre_constant_truncation(self):
        case = {"beta": 5, "n_legendre": 1, "n_iw": 40, "configurations": [{
            "sign": 1, "weight": 2, "c_times": [1.1], "cdagger_times": [3.4],
            "matrix": [[0.8]], "f_prefactor": [-1.7],
        }]}
        result = solve.legendre(case)
        np.testing.assert_allclose(result["g_legendre"], [0.8 / 5], atol=1e-15)
        expected = 2j * 0.8 / 5 / ((2 * np.arange(40) + 1) * np.pi)
        np.testing.assert_allclose(decode(result["g_iw"]), expected, atol=1e-15)
        np.testing.assert_allclose(decode(result["sigma_iw"]), -1.7, atol=1e-15)

    def test_legendre_equal_times_and_empty_configuration(self):
        case = {"beta": 4, "n_legendre": 32, "n_iw": 40, "configurations": [{
            "sign": 1, "weight": 3, "c_times": [0], "cdagger_times": [0],
            "matrix": [[2]], "f_prefactor": [0.7],
        }, {"sign": -1, "weight": 1, "c_times": [], "cdagger_times": [], "matrix": [], "f_prefactor": []}]}
        result = solve.legendre(case)
        orders = np.arange(32)
        expected = -0.75 * np.sqrt(2 * orders + 1) * (-1.0)**orders
        np.testing.assert_allclose(result["g_legendre"], expected, atol=2e-15)
        np.testing.assert_allclose(decode(result["sigma_iw"]), 0.7, atol=1e-14)

    def test_legendre_beta_scaling(self):
        case = make_legendre(95)
        baseline = solve.legendre(case)
        changed = copy.deepcopy(case)
        changed["beta"] *= 2
        for config in changed["configurations"]:
            config["c_times"] = [2 * value for value in config["c_times"]]
            config["cdagger_times"] = [2 * value for value in config["cdagger_times"]]
        expected = {key: np.asarray(value) / (1 if key == "sigma_iw" else 2) for key, value in baseline.items()}
        self.assert_outputs(solve.legendre(changed), expected, tolerance=1e-13)

    def test_samples_and_portable_cli(self):
        samples = HERE.parent / "participant" / "input"
        cases = [json.loads((samples / name).read_text()) for name in ["sample_01.json", "sample_02.json"]]
        cases.append(make_afm(812))
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            temporary = Path(directory)
            shutil.copyfile(HERE / "solve.py", temporary / "solve.py")
            elsewhere = temporary / "elsewhere"
            elsewhere.mkdir()
            for index, case in enumerate(cases):
                source = temporary / f"input_{index}.json"
                destination = temporary / f"output_{index}.json"
                source.write_text(json.dumps(case))
                started = time.monotonic()
                completed = subprocess.run(
                    [sys.executable, str(temporary / "solve.py"), "--input", str(source), "--output", str(destination)],
                    cwd=elsewhere, capture_output=True, text=True, timeout=120,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertLess(time.monotonic() - started, 120)
                self.assert_outputs(json.loads(destination.read_text()), solve.solve(case), tolerance=0)


if __name__ == "__main__":
    unittest.main()
