import numpy as np


def describe_batch(values):
    count, length = values.shape
    values = values - np.mean(values, axis=1, keepdims=True)
    scale = np.sqrt(np.mean(values ** 2, axis=1))
    normal = values / np.maximum(scale[:, None], 1e-12)
    features = [np.full(count, length), scale, np.ptp(values, axis=1),
                np.mean(np.abs(values), axis=1), np.mean(normal ** 4, axis=1),
                np.abs(np.mean(normal ** 3, axis=1))]
    quantiles = np.linspace(0, 1, 7)
    features.extend(np.quantile(np.abs(values), quantiles, axis=1))
    features.extend(np.quantile(np.diff(np.sort(values, axis=1), axis=1), quantiles, axis=1))
    power = np.abs(np.fft.rfft(values, axis=1)) ** 2 / length ** 2
    for harmonic in range(1, 7):
        value = power[:, harmonic] if harmonic < power.shape[1] else np.zeros(count)
        features.extend([value, value / np.maximum(scale ** 2, 1e-12)])
    for distance in range(1, 7):
        shifted_values = np.roll(values, distance, axis=1)
        difference = values - shifted_values
        absolute = np.abs(difference)
        features.extend(np.quantile(absolute, quantiles, axis=1))
        features.extend([np.mean(absolute, axis=1), np.std(absolute, axis=1),
                         np.mean(values * shifted_values, axis=1),
                         np.mean(normal * np.roll(normal, distance, axis=1), axis=1)])
        for broadening in (0.25, 0.5, 1.0, 2.0):
            resonance = broadening ** 2 / (broadening ** 2 + difference ** 2)
            features.extend([np.mean(resonance, axis=1), np.min(resonance, axis=1),
                             np.mean(np.log(resonance), axis=1)])
        shifted = np.minimum.reduce([absolute, np.abs(absolute - 1), np.abs(absolute - 2)])
        features.extend([np.mean(1 / (1 + shifted ** 2), axis=1), np.min(shifted, axis=1)])
    bonds = np.abs(values - np.roll(values, 1, axis=1))
    features.extend(np.sort(bonds, axis=1)[:, -4:].T)
    for window in (2, 3, 4, 5, 6):
        patches = np.stack([np.roll(values, offset, axis=1) for offset in range(window)])
        averages = np.abs(np.mean(patches, axis=0))
        spread = np.std(patches, axis=0)
        features.extend([np.min(spread, axis=1), np.mean(spread, axis=1), np.max(spread, axis=1),
                         np.max(averages, axis=1), np.mean(averages, axis=1)])
        barriers = np.stack([np.roll(bonds, offset, axis=1) for offset in range(window)])
        features.extend([np.max(np.min(barriers, axis=0), axis=1),
                         np.min(np.max(barriers, axis=0), axis=1),
                         np.max(np.sum(np.log1p(barriers ** 2), axis=0), axis=1)])
    for broadening in (0.25, 0.5, 1.0, 2.0):
        weights = broadening ** 2 / (broadening ** 2 + bonds ** 2)
        adjacency = np.zeros((count, length, length))
        sites = np.arange(length)
        adjacency[:, sites, (sites - 1) % length] = weights
        adjacency[:, (sites - 1) % length, sites] = weights
        laplacian = -adjacency
        laplacian[:, sites, sites] = adjacency.sum(axis=2)
        spectrum = np.linalg.eigvalsh(laplacian)
        features.extend(spectrum[:, 1:5].T)
        features.extend([np.mean(weights * np.roll(weights, 1, axis=1), axis=1),
                         np.mean(weights * np.roll(weights, 2, axis=1), axis=1)])
    return np.column_stack(features)


def describe(fields):
    return describe_batch(np.asarray([fields], dtype=float))[0].tolist()


def feature_matrix(cases):
    features = np.empty((len(cases), 250), dtype=np.float64)
    for length in sorted({len(case["fields"]) for case in cases}):
        indices = [index for index, case in enumerate(cases) if len(case["fields"]) == length]
        values = np.asarray([cases[index]["fields"] for index in indices], dtype=float)
        features[indices] = describe_batch(values)
    return features
