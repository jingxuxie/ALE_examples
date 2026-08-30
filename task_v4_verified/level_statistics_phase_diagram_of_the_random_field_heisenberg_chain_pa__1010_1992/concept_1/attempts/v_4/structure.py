import numpy as np


def structure_batch(values):
    count, length = values.shape
    values = values - values.mean(axis=1, keepdims=True)
    sites = np.arange(length)
    scale = np.sqrt(np.mean(values ** 2, axis=1))
    transform = np.fft.rfft(values, axis=1) / length
    stagger = transform[:, -1].real
    smooth = 2 * np.real(transform[:, 1, None] * np.exp(2j * np.pi * sites / length))
    residual = values - stagger[:, None] * (-1.) ** sites - smooth
    outputs = [scale, np.abs(stagger), 2 * np.abs(transform[:, 1]),
               np.sqrt(np.mean(residual ** 2, axis=1)), np.max(np.abs(residual), axis=1),
               np.abs(stagger) / np.maximum(scale, 1e-12),
               np.sqrt(np.mean(residual ** 2, axis=1)) / np.maximum(scale, 1e-12)]
    for blocks in (2, 3):
        groups = np.array_split(sites, blocks)
        partitions = []
        errors = []
        for offset in range(length):
            shifted = np.roll(values, offset, axis=1)
            centers = np.stack([shifted[:, group].mean(axis=1) for group in groups], axis=1)
            deviations = np.stack([shifted[:, group].std(axis=1) for group in groups], axis=1)
            slopes = np.stack([np.mean(shifted[:, group] * np.linspace(-1, 1, len(group)), axis=1)
                               / np.mean(np.linspace(-1, 1, len(group)) ** 2) for group in groups], axis=1)
            errors.append(sum(np.sum((shifted[:, group] - centers[:, group_index, None]) ** 2, axis=1)
                              for group_index, group in enumerate(groups)))
            partitions.append((centers, deviations, slopes))
        errors = np.stack(errors, axis=1)
        best = errors.argmin(axis=1)
        centers = np.stack([partition[0] for partition in partitions], axis=1)[np.arange(count), best]
        deviations = np.stack([partition[1] for partition in partitions], axis=1)[np.arange(count), best]
        slopes = np.abs(np.stack([partition[2] for partition in partitions], axis=1)[np.arange(count), best])
        detuning = np.abs(centers - np.roll(centers, 1, axis=1))
        outputs.extend([np.sqrt(errors.min(axis=1) / length),
                        errors.min(axis=1) / np.maximum(length * scale ** 2, 1e-12)])
        for feature in (np.abs(centers), deviations, slopes, detuning):
            outputs.extend([feature.min(axis=1), feature.mean(axis=1), feature.max(axis=1)])
    order = np.argsort(values, axis=1)
    sorted_values = np.take_along_axis(values, order, axis=1)
    mismatch = sorted_values[:, 1::2] - sorted_values[:, ::2]
    pair_distance = np.abs(order[:, 1::2] - order[:, ::2])
    pair_distance = np.minimum(pair_distance, length - pair_distance)
    outputs.extend([mismatch.mean(axis=1), mismatch.max(axis=1),
                    mismatch.mean(axis=1) / np.maximum(scale, 1e-12)])
    for width in (.1, .3, 1.):
        paired = width ** 2 / (width ** 2 + mismatch ** 2)
        outputs.extend([paired.mean(axis=1), (paired * pair_distance).mean(axis=1),
                        (paired * np.sin(np.pi * pair_distance / length) ** 2).mean(axis=1)])
    bonds = values - np.roll(values, 1, axis=1)
    for separation in (2, 3, 4, 5, 6):
        other = np.roll(bonds, separation, axis=1)
        detuning = np.minimum(np.abs(bonds - other), np.abs(bonds + other))
        coupling = 1 / np.sqrt((1 + bonds ** 2) * (1 + other ** 2))
        for width in (.25, .5, 1., 2.):
            resonances = width ** 2 / (width ** 2 + detuning ** 2)
            outputs.extend([resonances.mean(axis=1), (coupling * resonances).mean(axis=1),
                            np.max(coupling * resonances, axis=1)])
    return np.column_stack(outputs)


def structure_features(cases):
    output = np.empty((len(cases), 107))
    for length in sorted({len(case['fields']) for case in cases}):
        indices = [index for index, case in enumerate(cases) if len(case['fields']) == length]
        values = np.asarray([cases[index]['fields'] for index in indices])
        output[indices] = structure_batch(values)
    return output
