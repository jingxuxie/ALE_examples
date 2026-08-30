"""Permutation-invariant Hamiltonian features, without interacting ED."""

import numpy as np


def summarize(values):
    return np.array([np.mean(values), np.std(values), np.min(values), np.max(values)])


def spectral_values(matrix):
    eigenvalues = np.linalg.eigvalsh(matrix)
    return np.interp(np.linspace(0.0, 1.0, 10), np.linspace(0.0, 1.0, len(matrix)), eigenvalues)


def features(inputs):
    rows = []
    for index, n_sites in enumerate(inputs["n_sites"]):
        hopping = inputs["hopping"][index, :n_sites, :n_sites]
        interaction = inputs["interaction"][index, :n_sites]
        potential = inputs["potential"][index, :n_sites]
        half = n_sites // 2
        one_body = -hopping + np.diag(potential)
        energies, orbitals = np.linalg.eigh(one_body)
        density = np.sum(orbitals[:, :half] ** 2, axis=1)
        holes = orbitals[:, half - 1] ** 2
        electrons = orbitals[:, half] ** 2
        first_charge = energies[half] - energies[half - 1] + np.sum(interaction * density * (electrons - holes))
        first_spin = first_charge - np.sum(interaction * holes * electrons)
        exchange = 8.0 * hopping ** 2 / (interaction[:, None] + interaction[None, :])
        atomic_levels = np.sort(np.concatenate([potential, potential + interaction]))
        bonds = hopping[np.triu(hopping != 0, 1)]
        degrees = hopping.sum(axis=1)
        squared_degrees = (hopping ** 2).sum(axis=1)
        rows.append(np.concatenate([
            [n_sites, first_charge, first_spin, atomic_levels[n_sites] - atomic_levels[n_sites - 1],
             energies[half] - energies[half - 1], np.sum(interaction * density ** 2),
             np.trace(hopping @ hopping @ hopping) / n_sites,
             np.sum(potential * (hopping @ potential)) / n_sites,
             np.sum(interaction * squared_degrees) / n_sites,
             np.sum(potential * interaction) / n_sites],
            summarize(interaction), summarize(potential), summarize(bonds),
            summarize(degrees), summarize(squared_degrees), summarize(density),
            spectral_values(one_body), spectral_values(hopping),
            spectral_values(-hopping + np.diag(potential + 0.5 * interaction)),
            spectral_values(exchange), spectral_values(np.diag(exchange.sum(axis=1)) - exchange)]))
    return np.asarray(rows)


def kernel(left, right, gamma):
    distances = (np.sum(left ** 2, axis=1)[:, None] + np.sum(right ** 2, axis=1)[None, :]
                 - 2.0 * left @ right.T)
    return np.exp(-gamma * np.maximum(distances, 0.0))


def predict(inputs, model):
    descriptors = features(inputs)
    predictions = np.empty((len(descriptors), 2))
    for family in range(4):
        for size in (10, 12):
            selected = (inputs["family"] == family) & (inputs["n_sites"] == size)
            if not np.any(selected):
                continue
            prefix = f"f{family}_n{size}_"
            transformed = (descriptors[selected] - model[prefix + "offset"]) / model[prefix + "scale"]
            predictions[selected] = (kernel(transformed, model[prefix + "train"],
                                             float(model[prefix + "gamma"])) @ model[prefix + "dual"]
                                     + model[prefix + "mean"])
    return predictions
