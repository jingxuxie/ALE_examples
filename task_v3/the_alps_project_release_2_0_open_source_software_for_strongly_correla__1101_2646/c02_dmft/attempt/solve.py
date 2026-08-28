"""Deterministic Fourier, AFM, and signed Legendre integration adapter."""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import spherical_jn


REAL = np.longdouble
COMPLEX = np.clongdouble
PI = np.arccos(REAL(-1))


def unpack(values):
    array = np.asarray(values, dtype=REAL)
    return array[..., 0] + COMPLEX(1j) * array[..., 1]


def pack(values):
    array = np.asarray(values)
    return np.stack((array.real, array.imag), axis=-1).astype(float).tolist()


def real_list(values):
    return np.asarray(values, dtype=float).tolist()


def frequencies(beta, count):
    return COMPLEX(1j) * (2 * np.arange(count, dtype=REAL) + 1) * PI / beta


class FermionicTransform:
    """Finite positive-frequency transform with analytic three-moment tails."""

    def __init__(self, beta, n_tau, count):
        self.beta = REAL(beta)
        self.n_tau = n_tau
        fractions = np.arange(n_tau, dtype=REAL) / n_tau
        self.tau = self.beta * fractions
        self.frequency = frequencies(self.beta, count)
        phase = PI * fractions[:, None] * (2 * np.arange(count) + 1)
        self.backward_phase = np.exp(-COMPLEX(1j) * phase)

    def tails(self, moments):
        first, second, third = np.asarray(moments, dtype=REAL)
        frequency_tail = (
            first / self.frequency
            + second / self.frequency**2
            + third / self.frequency**3
        )
        time_tail = (
            -first / 2
            + second * (2 * self.tau - self.beta) / 4
            + third * self.tau * (self.beta - self.tau) / 4
        )
        return frequency_tail, time_tail

    def backward(self, values, moments):
        frequency_tail, time_tail = self.tails(moments)
        result = np.empty(self.n_tau + 1, dtype=REAL)
        result[:-1] = time_tail + (2 / self.beta) * (
            self.backward_phase @ (values - frequency_tail)
        ).real
        result[-1] = -REAL(moments[0]) - result[0]
        return result

    def forward(self, values, moments):
        frequency_tail, time_tail = self.tails(moments)
        return frequency_tail + (self.beta / self.n_tau) * (
            self.backward_phase.conj().T @ (values[:-1] - time_tail)
        )


def fourier(case):
    channels = case["channels"]
    if not channels:
        return {"g_tau": [], "iw_roundtrip": []}
    transform = FermionicTransform(
        case["beta"], case["n_tau"], len(channels[0]["iw"])
    )
    time_values = []
    roundtrip = []
    for channel in channels:
        times = transform.backward(unpack(channel["iw"]), channel["moments"])
        time_values.append(real_list(times))
        roundtrip.append(pack(transform.forward(times, channel["moments"])))
    return {"g_tau": time_values, "iw_roundtrip": roundtrip}


def afm(case):
    beta = REAL(case["beta"])
    chemical_potential = REAL(case["mu"])
    field_strength = REAL(case["h"])
    initial_weiss = unpack(case["g0_iw"])
    impurity = unpack(case["g_iw"])
    flavors, count = initial_weiss.shape
    transform = FermionicTransform(beta, case["n_tau"], count)
    frequency = transform.frequency
    sigma = 1 / initial_weiss - 1 / impurity
    lattice = np.empty_like(initial_weiss)
    second_moments = np.empty(flavors // 2, dtype=REAL)
    chemical = chemical_potential + np.where(
        np.arange(flavors) % 2 == 0, -field_strength, field_strength
    )
    for band, measure in enumerate(case["dos"]):
        first = 2 * band
        second = first + 1
        energy = np.asarray(measure["energy"], dtype=REAL)
        weight = np.asarray(measure["weight"], dtype=REAL)
        energy_squared = energy**2
        second_moments[band] = np.sum(weight * energy_squared)
        zeta_first = frequency + chemical[first] - sigma[first]
        zeta_second = frequency + chemical[second] - sigma[second]
        integral = np.sum(
            weight[None, :]
            / (zeta_first[:, None] * zeta_second[:, None] - energy_squared),
            axis=1,
        )
        lattice[first] = zeta_second * integral
        lattice[second] = zeta_first * integral
    inverse_weiss = 1 / lattice + sigma
    weiss = 1 / inverse_weiss
    hybridization = frequency[None, :] + chemical[:, None] - inverse_weiss
    time_values = []
    for flavor in range(flavors):
        moments = [
            1,
            -chemical[flavor],
            chemical[flavor] ** 2 + second_moments[flavor // 2],
        ]
        time_values.append(real_list(transform.backward(weiss[flavor], moments)))
    return {
        "lattice_iw": pack(lattice),
        "weiss_iw": pack(weiss),
        "hybridization_iw": pack(hybridization),
        "weiss_tau": time_values,
    }


def legendre(case):
    beta = REAL(case["beta"])
    degree = case["n_legendre"]
    count = case["n_iw"]
    configurations = case["configurations"]
    signed_weights = np.asarray(
        [REAL(config["weight"]) * config["sign"] for config in configurations],
        dtype=REAL,
    )
    denominator = np.sum(signed_weights)
    green = np.zeros(degree, dtype=REAL)
    auxiliary = np.zeros(degree, dtype=REAL)
    for config, signed_weight in zip(configurations, signed_weights):
        annihilation = np.asarray(config["c_times"], dtype=REAL)
        creation = np.asarray(config["cdagger_times"], dtype=REAL)
        size = len(annihilation)
        if size == 0:
            continue
        differences = annihilation[:, None] - creation[None, :]
        wrapped = differences < 0
        differences = np.where(wrapped, differences + beta, differences)
        locations = (2 * differences / beta - 1).ravel()
        matrix = np.asarray(config["matrix"], dtype=REAL).T
        event_weights = (
            signed_weight * np.where(wrapped, -1, 1) * matrix
        ).ravel()
        prefactor = np.asarray(config["f_prefactor"], dtype=REAL)
        auxiliary_weights = event_weights * np.repeat(prefactor, size)
        polynomials = np.polynomial.legendre.legvander(locations, degree - 1)
        green += event_weights @ polynomials
        auxiliary += auxiliary_weights @ polynomials
    normalization = np.sqrt(2 * np.arange(degree, dtype=REAL) + 1)
    green *= -normalization / (beta * denominator)
    auxiliary *= -normalization / (beta * denominator)
    orders = np.arange(degree)
    arguments = (np.arange(count, dtype=float) + 0.5) * np.pi
    bessel = spherical_jn(orders[None, :], arguments[:, None]).astype(REAL)
    phases = np.asarray([1j, -1, -1j, 1], dtype=COMPLEX)[orders % 4]
    parity = np.where(np.arange(count) % 2 == 0, 1, -1)
    transform = (
        parity[:, None] * phases[None, :] * normalization[None, :] * bessel
    )
    green_iw = transform @ green
    auxiliary_iw = transform @ auxiliary
    return {
        "g_legendre": real_list(green),
        "f_legendre": real_list(auxiliary),
        "g_iw": pack(green_iw),
        "sigma_iw": pack(auxiliary_iw / green_iw),
    }


def solve(case):
    return {"fourier": fourier, "afm": afm, "legendre": legendre}[case["family"]](case)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    case = json.loads(arguments.input.read_text(encoding="utf-8"))
    result = solve(case)
    arguments.output.write_text(
        json.dumps(result, allow_nan=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
