import numpy as np


def pair_rotations(one_body, factors, samples=65):
    dimension = len(one_body)
    matrices = np.concatenate((one_body[None], factors), axis=0)
    weights = abs(matrices).sum(axis=(1, 2))
    base_cost = weights[0] + .5 * (weights[1:] @ weights[1:])
    angles = np.linspace(-np.pi / 4, np.pi / 4, samples)
    cosine = np.cos(angles)[:, None]
    sine = np.sin(angles)[:, None]
    choices = []
    for first in range(dimension):
        for second in range(first + 1, dimension):
            others = [index for index in range(dimension) if index != first and index != second]
            first_row = matrices[:, first, others]
            second_row = matrices[:, second, others]
            first_diagonal = matrices[:, first, first]
            second_diagonal = matrices[:, second, second]
            off_diagonal = matrices[:, first, second]
            rest = weights - 2 * (abs(first_row).sum(axis=1) + abs(second_row).sum(axis=1))
            rest -= abs(first_diagonal) + abs(second_diagonal) + 2 * abs(off_diagonal)
            new_weights = rest + abs(cosine ** 2 * first_diagonal + sine ** 2 * second_diagonal + 2 * cosine * sine * off_diagonal)
            new_weights += abs(sine ** 2 * first_diagonal + cosine ** 2 * second_diagonal - 2 * cosine * sine * off_diagonal)
            new_weights += 2 * abs((cosine ** 2 - sine ** 2) * off_diagonal + cosine * sine * (second_diagonal - first_diagonal))
            new_weights += 2 * abs(cosine[:, :, None] * first_row + sine[:, :, None] * second_row).sum(axis=2)
            new_weights += 2 * abs(-sine[:, :, None] * first_row + cosine[:, :, None] * second_row).sum(axis=2)
            values = new_weights[:, 0] + .5 * (new_weights[:, 1:] ** 2).sum(axis=1)
            for angle_index in range(samples - 1):
                previous = values[angle_index - 1] if angle_index else values[-2]
                following = values[angle_index + 1]
                angle = angles[angle_index]
                if values[angle_index] <= previous and values[angle_index] <= following and abs(angle) > .12:
                    rotation = np.eye(dimension)
                    cosine_value, sine_value = np.cos(angle), np.sin(angle)
                    rotation[first, first] = cosine_value
                    rotation[second, second] = cosine_value
                    rotation[second, first] = sine_value
                    rotation[first, second] = -sine_value
                    choices.append((values[angle_index] / max(base_cost, 1e-30) - 1, (first, second, angle), rotation))
    choices.sort(key=lambda entry: entry[0])
    return choices
