import numpy as np


def linear_logits(parameters):
    result = np.array([parameters[0] - np.sum(parameters[1:])])
    for weight in parameters[1:]:
        result = np.concatenate((result, result + 2 * weight))
    return result


def linear_moments(values):
    count = len(values).bit_length() - 1
    result = np.empty(count + 1)
    for position in range(count):
        negative = values[::2]
        positive = values[1::2]
        result[position + 1] = positive.sum() - negative.sum()
        values = negative + positive
    result[0] = values[0]
    return result


def quadratic_moments(values):
    count = len(values).bit_length() - 1
    transformed = values.copy()
    for position in range(count):
        width = 1 << position
        pairs = transformed.reshape(-1, 2, width)
        first = pairs[:, 0, :].copy()
        second = pairs[:, 1, :].copy()
        pairs[:, 0, :] = first + second
        pairs[:, 1, :] = first - second
    indices = np.concatenate(([0], 1 << np.arange(count)))
    signs = np.ones(count + 1)
    signs[1:] = -1
    return transformed[indices[:, None] ^ indices[None, :]] * signs[:, None] * signs[None, :]
