import functools
import itertools
import numpy as np
from descriptors import describe_batch


@functools.lru_cache(None)
def occupations(length):
    choices = list(itertools.combinations(range(length), length // 2))
    spins = np.full((len(choices), length), -0.5)
    for row, sites in enumerate(choices):
        spins[row, list(sites)] = 0.5
    first, second = np.triu_indices(length, 1)
    products = spins[:, first] * spins[:, second]
    return spins, first, second, products


def particle_features(values, hoppings=(0.35, 0.65, 1.0, 1.6, 2.5), summary=False):
    count, length = values.shape
    sites = np.arange(length)
    phase = np.exp(2j * np.pi * sites / length)
    spins, first, second, products = occupations(length)
    result = []
    for hopping in hoppings:
        matrix = np.zeros((count, length, length))
        matrix[:, sites, sites] = values
        matrix[:, sites, (sites + 1) % length] = hopping
        matrix[:, (sites + 1) % length, sites] = hopping
        energies, vectors = np.linalg.eigh(matrix)
        if summary:
            diagonal = np.einsum('bja,j->ba', vectors**2, phase)
            result.append(1 - np.mean(np.abs(diagonal)**2, axis=1))
        else:
            transformed = np.einsum('bja,j,bjc->bac', vectors, phase, vectors, optimize=True)
            diagonal = np.diagonal(transformed, axis1=1, axis2=2)
            squared = np.abs(transformed) ** 2
            quantum = length / 4 - np.trace(squared, axis1=1, axis2=2)[None, :] / 4
            quantum = quantum - 2 * products @ squared[:, first, second].T
            classical = np.abs(spins @ diagonal.T) ** 2
            fractions = quantum / np.maximum(quantum + classical, 1e-14)
            total_energy = spins @ energies.T
            order = np.argsort(total_energy, axis=0)
            central = np.take_along_axis(fractions, order[len(spins)//3:2*len(spins)//3], axis=0)
            result.extend([fractions.mean(axis=0), central.mean(axis=0),
                           fractions.std(axis=0), central.std(axis=0),
                           quantum.mean(axis=0) / (quantum + classical).mean(axis=0)])
        result.extend(np.quantile(np.abs(diagonal), (0, .25, .5, .75, 1), axis=1))
        ipr = np.sum(vectors ** 4, axis=1)
        result.extend([ipr.mean(axis=1), ipr.std(axis=1), ipr.max(axis=1)])
    return np.column_stack(result)


@functools.lru_cache(None)
def cluster_basis(width):
    states = np.array([sum(1 << site for site in sites)
                       for sites in itertools.combinations(range(width), width // 2)])
    spins = ((states[:, None] >> np.arange(width)) & 1).astype(float) - .5
    exchange = np.diag(np.sum(spins[:, :-1] * spins[:, 1:], axis=1))
    lookup = {int(state): index for index, state in enumerate(states)}
    for column, state in enumerate(states):
        for site in range(width - 1):
            if ((state >> site) & 1) != ((state >> (site + 1)) & 1):
                exchange[lookup[int(state ^ (3 << site))], column] += .5
    return spins, exchange


def cluster_features(values, couplings=(0.7, 1.0, 1.5), width=6):
    count, length = values.shape
    result = []
    spins, exchange = cluster_basis(width)
    patches = np.stack([np.roll(values, -offset, axis=1) for offset in range(width)], axis=2)
    flat = patches.reshape(-1, width)
    dimension = len(spins)
    mode = spins @ np.exp(2j * np.pi * np.arange(width) / length)
    mode_square = np.abs(mode) ** 2
    for coupling in couplings:
        matrix = np.broadcast_to(exchange * coupling, (len(flat), dimension, dimension)).copy()
        matrix[:, np.arange(dimension), np.arange(dimension)] += flat @ spins.T
        energies, vectors = np.linalg.eigh(matrix)
        probabilities = vectors ** 2
        means = probabilities.transpose(0, 2, 1) @ mode
        denominator = probabilities.transpose(0, 2, 1) @ mode_square
        fractions = 1 - np.abs(means) ** 2 / np.maximum(denominator, 1e-12)
        local_fraction = fractions.mean(axis=1).reshape(count, length)
        central_fraction = fractions[:, dimension//3:2*dimension//3].mean(axis=1).reshape(count, length)
        memory = probabilities.transpose(0, 2, 1) @ spins
        local_memory = (4 * np.mean(memory ** 2, axis=(1, 2))).reshape(count, length)
        for quantity in (local_fraction, central_fraction, local_memory):
            result.extend(np.quantile(quantity, (0, .25, .5, .75, 1), axis=1))
            result.extend([quantity.mean(axis=1), quantity.std(axis=1)])
        result.extend([np.mean(local_fraction * np.roll(local_fraction, offset, axis=1), axis=1)
                       for offset in (1, 2, 3)])
    return np.column_stack(result)


def transport_features(values):
    count, length = values.shape
    sites = np.arange(length)
    phase = np.exp(2j * np.pi * sites / length)
    differences = values - np.roll(values, 1, axis=1)
    result = []
    for broadening in (.3, .6, 1., 2.):
        weights = sum(probability * broadening**2 / (broadening**2 + (differences + shift)**2)
                      for probability, shift in ((.25, -1), (.5, 0), (.25, 1)))
        laplacian = np.zeros((count, length, length))
        laplacian[:, sites, (sites - 1) % length] = -weights
        laplacian[:, (sites - 1) % length, sites] = -weights
        laplacian[:, sites, sites] = weights + np.roll(weights, -1, axis=1)
        spectrum, vectors = np.linalg.eigh(laplacian)
        projected = np.abs(np.einsum('bja,j->ba', vectors, phase)) ** 2 / length
        for duration in (.3, 1, 3, 10, 30, 100):
            result.append(np.sum(projected * (1 - np.exp(-duration * np.maximum(spectrum, 0))), axis=1))
        result.extend(np.quantile(weights, (0, .25, .5, .75, 1), axis=1))
        result.extend([np.mean(weights, axis=1), np.mean(np.log(weights), axis=1)])
    power = np.abs(np.fft.rfft(values, axis=1)) ** 2 / length**2
    result.extend([power[:, -1], power[:, -1] / np.maximum(np.mean(values**2, axis=1), 1e-12)])
    return np.column_stack(result)


def feature_matrix(cases, kind='all'):
    outputs = []
    order = []
    for length in sorted({len(case['fields']) for case in cases}):
        indices = [index for index, case in enumerate(cases) if len(case['fields']) == length]
        values = np.asarray([cases[index]['fields'] for index in indices])
        values = values - values.mean(axis=1, keepdims=True)
        blocks = [describe_batch(values)]
        if kind not in ('base', 'compact', 'quick', 'quick_particle', 'tiny'):
            blocks.append(transport_features(values))
        if kind in ('all', 'particle'):
            blocks.append(particle_features(values))
        if kind in ('compact', 'hybrid'):
            blocks.append(particle_features(values, (.65, 1.6)))
        if kind in ('quick', 'quick_particle'):
            blocks.append(particle_features(values, summary=True))
        if kind in ('all', 'cluster'):
            blocks.append(cluster_features(values))
        if kind in ('compact', 'hybrid', 'fast_cluster', 'quick'):
            blocks.append(cluster_features(values, (1.,)))
        if kind == 'tiny':
            blocks.append(cluster_features(values, width=4))
        outputs.append(np.column_stack(blocks))
        order.extend(indices)
    return np.concatenate(outputs)[np.argsort(order)]
