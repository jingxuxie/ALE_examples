import argparse
import json
from pathlib import Path

import numpy as np


def unpack(values):
    array = np.asarray(values, dtype=float)
    return array[..., 0] + 1j * array[..., 1]


def pack(values):
    array = np.asarray(values)
    return np.stack((array.real, array.imag), axis=-1).tolist()


def backward(beta, intervals, values, moments):
    first, second, third = moments
    frequency = (2 * np.arange(len(values)) + 1) * np.pi / beta
    times = np.arange(intervals + 1) * beta / intervals
    residual = values - first / (1j * frequency) - second / (1j * frequency)**2 - third / (1j * frequency)**3
    model = -first / 2 + second * (2 * times - beta) / 4 + third * times * (beta - times) / 4
    result = model + 2 / beta * (
        np.cos(times[:, None] * frequency) @ residual.real
        + np.sin(times[:, None] * frequency) @ residual.imag
    )
    result[-1] = -first - result[0]
    return result


def fourier(case):
    time_output = []
    frequency_output = []
    for channel in case["channels"]:
        values = unpack(channel["iw"])
        transformed = backward(case["beta"], case["n_tau"], values, channel["moments"])
        first, second, third = channel["moments"]
        times = np.arange(case["n_tau"]) * case["beta"] / case["n_tau"]
        model = -first / 2 + second * (2 * times - case["beta"]) / 4
        model += third * times * (case["beta"] - times) / 4
        frequencies = 1j * (2 * np.arange(len(values)) + 1) * np.pi / case["beta"]
        restored = np.exp(frequencies[:, None] * times) @ (transformed[:-1] - model)
        restored *= case["beta"] / case["n_tau"]
        restored += first / frequencies + second / frequencies**2 + third / frequencies**3
        time_output.append(transformed.tolist())
        frequency_output.append(pack(restored))
    return {"g_tau": time_output, "iw_roundtrip": frequency_output}


def afm(case):
    initial = unpack(case["g0_iw"])
    impurity = unpack(case["g_iw"])
    sigma = 1 / initial - 1 / impurity
    flavors, count = initial.shape
    frequency = 1j * (2 * np.arange(count) + 1) * np.pi / case["beta"]
    lattice = np.empty_like(initial)
    weiss = np.empty_like(initial)
    delta = np.empty_like(initial)
    time_output = []
    for first in range(0, flavors, 2):
        second = first + 1
        band = case["dos"][first // 2]
        energies = np.asarray(band["energy"])
        weights = np.asarray(band["weight"])
        zeta_first = frequency + case["mu"] - case["h"] - sigma[first]
        zeta_second = frequency + case["mu"] + case["h"] - sigma[second]
        integral = (1 / (zeta_first[:, None] * zeta_second[:, None] - energies**2)) @ weights
        lattice[first] = zeta_second * integral
        lattice[second] = zeta_first * integral
        moment = weights @ energies**2
        for flavor in (first, second):
            chemical = case["mu"] + (-case["h"] if flavor % 2 == 0 else case["h"])
            weiss[flavor] = 1 / (1 / lattice[flavor] + sigma[flavor])
            delta[flavor] = frequency + chemical - 1 / weiss[flavor]
            time_output.append(backward(case["beta"], case["n_tau"], weiss[flavor], [1, -chemical, chemical**2 + moment]).tolist())
    return {
        "lattice_iw": pack(lattice),
        "weiss_iw": pack(weiss),
        "hybridization_iw": pack(delta),
        "weiss_tau": time_output,
    }


def legendre(case):
    degree = case["n_legendre"]
    green = np.zeros(degree)
    auxiliary = np.zeros(degree)
    denominator = sum(config["weight"] * config["sign"] for config in case["configurations"])
    for config in case["configurations"]:
        for annihilator, c_time in enumerate(config["c_times"]):
            for creator, cdagger_time in enumerate(config["cdagger_times"]):
                elapsed = c_time - cdagger_time
                sign = config["sign"]
                if elapsed < 0:
                    elapsed += case["beta"]
                    sign = -sign
                coordinate = 2 * elapsed / case["beta"] - 1
                previous = 1.0
                current = coordinate
                for order in range(degree):
                    if order == 0:
                        polynomial = 1.0
                    elif order == 1:
                        polynomial = coordinate
                    else:
                        polynomial = ((2 * order - 1) * coordinate * current - (order - 1) * previous) / order
                        previous, current = current, polynomial
                    value = -config["weight"] * config["matrix"][creator][annihilator] * sign * polynomial / case["beta"]
                    green[order] += value
                    auxiliary[order] += value * config["f_prefactor"][annihilator]
    normalization = np.sqrt(2 * np.arange(degree) + 1) / denominator
    green *= normalization
    auxiliary *= normalization
    nodes, weights = np.polynomial.legendre.leggauss(max(160, 6 * case["n_iw"] + degree))
    times = case["beta"] * (nodes + 1) / 2
    time_green = np.polynomial.legendre.legval(nodes, np.sqrt(2 * np.arange(degree) + 1) * green) / case["beta"]
    time_auxiliary = np.polynomial.legendre.legval(nodes, np.sqrt(2 * np.arange(degree) + 1) * auxiliary) / case["beta"]
    phase = np.exp(1j * (2 * np.arange(case["n_iw"])[:, None] + 1) * np.pi * times / case["beta"])
    omega = case["beta"] / 2 * phase @ (weights * time_green)
    auxiliary_omega = case["beta"] / 2 * phase @ (weights * time_auxiliary)
    return {
        "g_legendre": green.tolist(),
        "f_legendre": auxiliary.tolist(),
        "g_iw": pack(omega),
        "sigma_iw": pack(auxiliary_omega / omega),
    }


def solve(case):
    return {"fourier": fourier, "afm": afm, "legendre": legendre}[case["family"]](case)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    arguments.output.write_text(json.dumps(solve(json.loads(arguments.input.read_text())), allow_nan=False))
