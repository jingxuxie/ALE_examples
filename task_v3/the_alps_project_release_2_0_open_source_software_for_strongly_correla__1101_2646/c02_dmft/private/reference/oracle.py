import numpy as np
from scipy.special import eval_legendre, spherical_jn


def unpack(values):
    array = np.asarray(values, dtype=float)
    return array[..., 0] + 1j * array[..., 1]


def pack(values):
    array = np.asarray(values)
    return np.stack((array.real, array.imag), axis=-1).tolist()


def inverse_transform(beta, intervals, values, moments):
    frequency = 1j * (2 * np.arange(len(values)) + 1) * np.pi / beta
    powers = np.arange(1, 4)
    residual = values - np.sum(np.asarray(moments) / frequency[:, None]**powers, axis=1)
    paired_values = np.concatenate((residual.conj()[::-1], residual))
    paired_frequency = np.concatenate((-frequency[::-1], frequency))
    times = np.linspace(0, beta, intervals + 1)
    basis = np.stack((-np.ones_like(times) / 2, (2 * times - beta) / 4, times * (beta - times) / 4))
    result = (np.exp(-times[:, None] * paired_frequency) @ paired_values / beta).real
    result += np.asarray(moments) @ basis
    result[-1] = -moments[0] - result[0]
    return result


def fourier(case):
    return {
        "g_tau": [inverse_transform(case["beta"], case["n_tau"], unpack(channel["iw"]), channel["moments"]).tolist() for channel in case["channels"]],
        "iw_roundtrip": [channel["iw"] for channel in case["channels"]],
    }


def afm(case):
    initial = unpack(case["g0_iw"])
    self_energy = 1 / initial - 1 / unpack(case["g_iw"])
    flavors, count = initial.shape
    frequencies = 1j * (2 * np.arange(count) + 1) * np.pi / case["beta"]
    field = np.tile([-case["h"], case["h"]], flavors // 2)
    chemical = case["mu"] + field
    lattice = np.zeros_like(initial)
    moments = []
    for band, density in enumerate(case["dos"]):
        energies = np.asarray(density["energy"])
        weights = np.asarray(density["weight"])
        inverse_resolvent = np.zeros((count, len(energies), 2, 2), dtype=complex)
        inverse_resolvent[:, :, 0, 0] = (frequencies + chemical[2 * band] - self_energy[2 * band])[:, None]
        inverse_resolvent[:, :, 1, 1] = (frequencies + chemical[2 * band + 1] - self_energy[2 * band + 1])[:, None]
        inverse_resolvent[:, :, 0, 1] = -energies
        inverse_resolvent[:, :, 1, 0] = -energies
        resolvents = np.linalg.inv(inverse_resolvent)
        local = np.einsum("q,nqij->nij", weights, resolvents)
        lattice[2 * band:2 * band + 2] = np.diagonal(local, axis1=1, axis2=2).T
        for flavor in (2 * band, 2 * band + 1):
            moments.append([1, -chemical[flavor], chemical[flavor]**2 + np.sum(weights * energies**2)])
    weiss = np.reciprocal(np.reciprocal(lattice) + self_energy)
    hybridization = frequencies + chemical[:, None] - np.reciprocal(weiss)
    return {
        "lattice_iw": pack(lattice), "weiss_iw": pack(weiss),
        "hybridization_iw": pack(hybridization),
        "weiss_tau": [inverse_transform(case["beta"], case["n_tau"], values, moment).tolist() for values, moment in zip(weiss, moments)],
    }


def legendre(case):
    orders = np.arange(case["n_legendre"])
    green = np.zeros(len(orders))
    auxiliary = np.zeros(len(orders))
    denominator = 0.0
    for config in case["configurations"]:
        differences = np.subtract.outer(config["c_times"], config["cdagger_times"])
        coordinates = 2 * np.remainder(differences, case["beta"]) / case["beta"] - 1
        signed_weight = config["weight"] * config["sign"]
        denominator += signed_weight
        pair_weights = signed_weight * np.where(differences < 0, -1, 1) * np.asarray(config["matrix"]).T
        basis = eval_legendre(orders[:, None, None], coordinates[None, :, :])
        green -= np.sum(basis * pair_weights, axis=(1, 2))
        auxiliary -= np.sum(basis * pair_weights * np.asarray(config["f_prefactor"])[:, None], axis=(1, 2))
    normalization = np.sqrt(2 * orders + 1) / (case["beta"] * denominator)
    green *= normalization
    auxiliary *= normalization
    indices = np.arange(case["n_iw"])
    arguments = (2 * indices + 1) * np.pi / 2
    transform = (-1.0)**indices[:, None] * (1j**(orders + 1)) * np.sqrt(2 * orders + 1)
    transform *= spherical_jn(orders[None, :], arguments[:, None])
    omega = transform @ green
    auxiliary_omega = transform @ auxiliary
    return {"g_legendre": green.tolist(), "f_legendre": auxiliary.tolist(),
            "g_iw": pack(omega), "sigma_iw": pack(auxiliary_omega / omega)}


def solve(case):
    return {"fourier": fourier, "afm": afm, "legendre": legendre}[case["family"]](case)
