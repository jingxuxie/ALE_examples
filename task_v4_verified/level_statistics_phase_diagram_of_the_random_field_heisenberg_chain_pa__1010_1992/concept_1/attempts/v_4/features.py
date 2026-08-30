import numpy as np
from descriptors import describe_batch


def physics_features(values):
    count, length = values.shape
    values = values - values.mean(axis=1, keepdims=True)
    sites = np.arange(length)
    mode = np.exp(2j * np.pi * sites / length)
    scale = np.sqrt(np.mean(values ** 2, axis=1))
    bonds = values - np.roll(values, 1, axis=1)
    outputs = []
    for hopping in (0.35, 0.5, 0.75, 1., 1.5, 2., 3., 4.):
        matrix = np.zeros((count, length, length))
        matrix[:, sites, sites] = values
        matrix[:, sites, (sites + 1) % length] = hopping
        matrix[:, (sites + 1) % length, sites] = hopping
        energies, vectors = np.linalg.eigh(matrix)
        probabilities = vectors ** 2
        moments = np.einsum('bsa,s->ba', probabilities, mode)
        memory = np.abs(moments) ** 2
        ipr = np.sum(probabilities ** 2, axis=1)
        outputs.extend([memory.mean(axis=1), np.std(memory, axis=1),
                        np.min(memory, axis=1), np.max(memory, axis=1),
                        ipr.mean(axis=1), ipr.max(axis=1), ipr.min(axis=1)])
        overlap = probabilities @ np.swapaxes(probabilities, 1, 2)
        for distance in (1, 2, 3, length // 2):
            overlaps = overlap[:, sites, (sites + distance) % length]
            outputs.extend([overlaps.mean(axis=1), overlaps.min(axis=1), overlaps.max(axis=1)])
        outputs.extend(np.quantile(memory, (0.25, 0.5, 0.75), axis=1))
    for width in (0.25, 0.5, 1., 2.):
        resonance = (width ** 2 / (width ** 2 + bonds ** 2))
        interaction = (2 * resonance + width ** 2 / (width ** 2 + (bonds - 1.) ** 2)
                       + width ** 2 / (width ** 2 + (bonds + 1.) ** 2)) / 4
        for weights in (resonance, interaction):
            adjacency = np.zeros((count, length, length))
            adjacency[:, sites, (sites - 1) % length] = weights
            adjacency[:, (sites - 1) % length, sites] = weights
            laplacian = -adjacency
            laplacian[:, sites, sites] = adjacency.sum(axis=2)
            eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
            projection = np.abs(np.einsum('bsa,s->ba', eigenvectors, mode)) ** 2 / length
            for lifetime in (1., 4., 16., 64., 256., 1024.):
                outputs.append(np.sum(projection / (1 + lifetime * eigenvalues), axis=1))
            outputs.extend([np.mean(weights, axis=1), np.mean(np.log(weights), axis=1),
                            np.mean(1 / weights, axis=1)])
            for window in (2, 3, 4, 6):
                patches = np.stack([np.roll(weights, offset, axis=1) for offset in range(window)])
                products = np.prod(patches, axis=0)
                outputs.extend([products.mean(axis=1), products.max(axis=1), products.min(axis=1)])
    for distance in range(1, length // 2 + 1):
        detuning = np.abs(values - np.roll(values, distance, axis=1))
        path = sum(np.log1p(np.roll(bonds, offset, axis=1) ** 2) for offset in range(distance))
        complementary = np.sum(np.log1p(bonds ** 2), axis=1, keepdims=True) - path
        path = np.minimum(path, complementary)
        attenuation = [np.exp(-factor * path) for factor in (0.25, 0.5, 1.)]
        for width in (0.25, 0.5, 1., 2.):
            resonance = width ** 2 / (width ** 2 + detuning ** 2)
            for factor in attenuation:
                connected = resonance * factor
                outputs.extend([connected.mean(axis=1), connected.max(axis=1)])
    normalized = values / np.maximum(scale[:, None], 1e-12)
    transform = np.fft.fft(normalized, axis=1) / length
    for first in range(1, 5):
        for second in range(first, 5):
            product = transform[:, first] * transform[:, second] * transform[:, (first + second) % length].conj()
            outputs.extend([np.abs(product.real), np.abs(product.imag)])
    return np.column_stack(outputs)


def feature_matrix(cases):
    groups = {}
    for index, case in enumerate(cases):
        groups.setdefault(len(case['fields']), []).append(index)
    output = None
    for length, indices in groups.items():
        values = np.asarray([cases[index]['fields'] for index in indices])
        base = describe_batch(values)
        extra = physics_features(values)
        if length < 14:
            missing = (7 - length // 2) * 24
            extra = np.concatenate([extra[:, :-20], np.zeros((len(indices), missing)), extra[:, -20:]], axis=1)
        block = np.column_stack([base, extra])
        if output is None:
            output = np.empty((len(cases), block.shape[1]))
        output[indices] = block
    return output
