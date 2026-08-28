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


def tail_models(beta, n_tau, count, moments):
    first, second, third = moments
    frequency = 1j * (2 * np.arange(count) + 1) * np.pi / beta
    tau = beta * np.arange(n_tau + 1) / n_tau
    omega_tail = first / frequency + second / frequency**2 + third / frequency**3
    tau_tail = -first / 2 + second * (2 * tau - beta) / 4
    tau_tail += third * tau * (beta - tau) / 4
    return frequency, tau, omega_tail, tau_tail


def backward(beta, n_tau, values, moments):
    first, second, third = moments
    if first == 0 and second == 0 and third:
        return np.zeros(n_tau + 1)
    frequency, tau, omega_tail, tau_tail = tail_models(beta, n_tau, len(values), moments)
    result = tau_tail + 2 / beta * (
        np.exp(-tau[:, None] * frequency) @ (values - omega_tail)
    ).real
    result[-1] = -first - result[0]
    return result


def forward(beta, n_tau, values, moments, count):
    frequency, tau, omega_tail, tau_tail = tail_models(beta, n_tau, count, moments)
    return omega_tail + beta / n_tau * (
        np.exp(frequency[:, None] * tau[None, :-1]) @ (values[:-1] - tau_tail[:-1])
    )


def fourier(case):
    time_values = []
    roundtrip = []
    for channel in case["channels"]:
        omega = unpack(channel["iw"])
        times = backward(case["beta"], case["n_tau"], omega, channel["moments"])
        time_values.append(times.tolist())
        roundtrip.append(
            pack(forward(case["beta"], case["n_tau"], times, channel["moments"], len(omega)))
        )
    return {"g_tau": time_values, "iw_roundtrip": roundtrip}


def afm(case):
    g0 = unpack(case["g0_iw"])
    impurity = unpack(case["g_iw"])
    flavors, count = g0.shape
    frequency = 1j * (2 * np.arange(count) + 1) * np.pi / case["beta"]
    sigma = 1 / g0 - 1 / impurity
    weiss = g0.copy()
    for band in range(0, flavors // 2, 2):
        first = 2 * band
        second = first + 1
        zeta_first = frequency + case["mu"] - case["h"] - sigma[first]
        zeta_second = frequency + case["mu"] + case["h"] - sigma[second]
        energy = np.asarray(case["dos"][band]["energy"])
        weight = np.asarray(case["dos"][band]["weight"])
        integral = np.sum(
            weight / (zeta_first[:, None] * zeta_second[:, None] - energy**2), axis=1
        )
        weiss[first] = 1 / (1 / (zeta_second * integral) + sigma[first])
        weiss[second] = 1 / (1 / (zeta_first * integral) + sigma[second])
    lattice = 1 / (1 / weiss - sigma)
    times = []
    hybridization = []
    for flavor in range(flavors):
        band = flavor // 2
        chemical = case["mu"] + (-case["h"] if flavor % 2 == 0 else case["h"])
        moment = np.dot(case["dos"][band]["weight"], np.square(case["dos"][band]["energy"]))
        times.append(
            backward(case["beta"], case["n_tau"], weiss[flavor], [1, -chemical, chemical**2 + moment]).tolist()
        )
        hybridization.append(frequency + chemical - 1 / weiss[flavor])
    return {
        "lattice_iw": pack(lattice),
        "weiss_iw": pack(weiss),
        "hybridization_iw": pack(hybridization),
        "weiss_tau": times,
    }


def legendre(case):
    degree = case["n_legendre"]
    green = np.zeros(degree)
    auxiliary = np.zeros(degree)
    denominator = sum(config["weight"] * config["sign"] for config in case["configurations"])
    for config in case["configurations"]:
        for annihilator, c_time in enumerate(config["c_times"]):
            for creator, cdagger_time in enumerate(config["cdagger_times"]):
                matrix_element = config["matrix"][creator][annihilator] * config["sign"]
                argument = c_time - cdagger_time
                bubble_sign = config["sign"]
                if argument < 0:
                    bubble_sign *= -1
                    argument += case["beta"]
                location = 2 * argument / case["beta"] - 1
                polynomial = np.polynomial.legendre.legvander(location, degree - 1)[0]
                contribution = -config["weight"] * matrix_element * bubble_sign * polynomial / case["beta"]
                green += contribution
                auxiliary += contribution * config["f_prefactor"][annihilator]
    normalization = np.sqrt(2 * np.arange(degree) + 1) / denominator
    green *= normalization
    auxiliary *= normalization
    nodes, weights = np.polynomial.legendre.leggauss(max(96, 4 * case["n_iw"] + degree))
    polynomial = np.polynomial.legendre.legvander(nodes, degree - 1)
    phase = np.exp(1j * np.pi * (2 * np.arange(case["n_iw"])[:, None] + 1) * (nodes + 1) / 2)
    transform = (phase * weights) @ polynomial * np.sqrt(2 * np.arange(degree) + 1) / 2
    omega = transform @ green
    auxiliary_omega = transform @ auxiliary
    return {
        "g_legendre": green.tolist(),
        "f_legendre": auxiliary.tolist(),
        "g_iw": pack(omega),
        "sigma_iw": pack(auxiliary_omega / omega),
    }


def solve(case):
    return {"fourier": fourier, "afm": afm, "legendre": legendre}[case["family"]](case)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = solve(json.loads(arguments.input.read_text()))
    arguments.output.write_text(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
