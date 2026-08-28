import numpy as np
from scipy.linalg import eigh


def local_operators(spin):
    link_dim = int(round(2 * spin + 1))
    flux = np.arange(link_dim, dtype=float) - spin
    raising = np.zeros((link_dim, link_dim))
    for index in range(link_dim - 1):
        raising[index + 1, index] = np.sqrt(spin * (spin + 1) - flux[index] * (flux[index] + 1))
    matter_lower = np.array([[0.0, 1.0], [0.0, 0.0]])
    identity = np.eye(2 * link_dim)
    return {
        "identity": identity,
        "number": np.kron(np.diag([0.0, 1.0]), np.eye(link_dim)),
        "flux": np.kron(np.eye(2), np.diag(flux)),
        "lower": np.kron(matter_lower, np.eye(link_dim)),
        "assisted": np.kron(matter_lower, raising),
        "flip": np.kron(np.eye(2), raising + raising.T) / np.sqrt(spin * (spin + 1)),
    }


def local_terms(settings, parameters):
    length = settings["length"]
    spin = settings["spin"]
    pair_error, link_error, mass_shift = parameters
    operators = local_operators(spin)
    identity = operators["identity"]
    number = operators["number"]
    flux = operators["flux"]
    sites = {}
    bonds = {}
    gauss = {}
    for site in range(length):
        sites[site] = (settings["mass"] + settings["profile"][site] + mass_shift) * number
        sites[site] = sites[site] + settings["electric"] * flux @ flux / 2
        sites[site] = sites[site] + link_error * operators["flip"]
        if site == 0:
            generator = flux + number - spin * identity
        else:
            generator = (-1) ** site * (np.kron(flux, identity) + np.kron(identity, flux + number))
        gauss[site] = generator @ generator
        protection = gauss[site] if settings["protection"] == "full" else settings["coefficients"][site] * generator
        if site == 0:
            sites[site] = sites[site] + settings["V"] * protection
        else:
            bonds[site - 1, site] = settings["V"] * protection
    for site in range(length - 1):
        hopping = -settings["J"] / np.sqrt(spin * (spin + 1)) * np.kron(operators["assisted"], operators["lower"])
        hopping = hopping + pair_error * np.kron(operators["lower"], operators["lower"])
        bonds[site, site + 1] = bonds[site, site + 1] + hopping + hopping.T
    return sites, bonds, gauss, operators


def initial_indices(settings):
    link_dim = int(round(2 * settings["spin"] + 1))
    return [link_dim - 1 if site % 2 == 0 else 0 for site in range(settings["length"])]


def embed(operator, first, width, length, local_dim):
    return np.kron(np.kron(np.eye(local_dim ** first), operator), np.eye(local_dim ** (length - first - width)))


def simulate(settings, parameters, times, pairs):
    length = settings["length"]
    sites, bonds, gauss, operators = local_terms(settings, parameters)
    local_dim = len(operators["identity"])
    dimension = local_dim ** length
    if dimension > 4096:
        raise ValueError("This starting point is only a small-cluster solver.")
    hamiltonian = np.zeros((dimension, dimension))
    for site, term in sites.items():
        hamiltonian += embed(term, site, 1, length, local_dim)
    for (left, right), term in bonds.items():
        hamiltonian += embed(term, left, 2, length, local_dim)
    initial = np.zeros(dimension)
    flat_index = 0
    for index in initial_indices(settings):
        flat_index = flat_index * local_dim + index
    initial[flat_index] = 1
    energies, vectors = eigh(hamiltonian)
    states = (np.exp(-1j * np.outer(times, energies)) * (vectors.T @ initial)) @ vectors.T
    probabilities = abs(states) ** 2
    density_diagonals = [np.diag(embed(operators["number"], site, 1, length, local_dim)) for site in range(length)]
    violation_diagonals = [np.diag(embed(gauss[site], max(0, site - 1), 1 if site == 0 else 2, length, local_dim)) for site in range(length)]
    density = probabilities @ np.array(density_diagonals).T
    violation = probabilities @ np.array(violation_diagonals).T
    correlation = np.empty((len(times), len(pairs)))
    for pair_index, (left, right) in enumerate(pairs):
        correlation[:, pair_index] = probabilities @ (density_diagonals[left] * density_diagonals[right]) - density[:, left] * density[:, right]
    return {"density": density.tolist(), "violation": violation.tolist(), "correlation": correlation.tolist()}
