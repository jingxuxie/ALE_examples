"""Independent scalar implementation of the release/v1 five-parton definitions."""

import itertools
import math


NAMES = ("tau", "C", "rho_H", "B_T", "B_W", "y23")


def dot(left, right):
    return math.fsum(first * second for first, second in zip(left, right))


def norm(vector):
    return math.sqrt(dot(vector, vector))


def add(left, right):
    return tuple(first + second for first, second in zip(left, right))


def observables(event):
    energy_sum = math.fsum(row[0] for row in event)
    spatial = [row[1:] for row in event]
    candidates = [(norm(row[1:]), row[0], row[1:]) for row in event]
    for left, right in itertools.combinations(event, 2):
        combined = add(left, right)
        candidates.append((norm(combined[1:]), combined[0], combined[1:]))
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    momentum, energy, vector = candidates[0]
    axis = tuple(component / momentum for component in vector)
    projections = [dot(vector, axis) for vector in spatial]
    broadening = [0.0, 0.0]
    for vector, projection in zip(spatial, projections):
        perpendicular = (
            vector[1] * axis[2] - vector[2] * axis[1],
            vector[2] * axis[0] - vector[0] * axis[2],
            vector[0] * axis[1] - vector[1] * axis[0],
        )
        broadening[int(projection > 0)] += norm(perpendicular) / (2 * energy_sum)
    tensor = [[math.fsum(row[first + 1] * row[second + 1] / row[0]
                          for row in event) / energy_sum
               for second in range(3)] for first in range(3)]
    c_parameter = 3 * math.fsum(
        tensor[first][first] * tensor[second][second] - tensor[first][second] ** 2
        for first, second in itertools.combinations(range(3), 2))
    result = {
        "tau": 1 - 2 * momentum / energy_sum,
        "C": c_parameter,
        "rho_H": (max(energy ** 2, (energy_sum - energy) ** 2) - momentum ** 2)
                 / energy_sum ** 2,
        "B_T": sum(broadening),
        "B_W": max(broadening),
        "thrust_gap": 2 * (momentum - candidates[1][0]) / energy_sum,
        "hemisphere_margin": min(abs(projection) for projection in projections),
        "hemisphere_occupancy": min(sum(projection > 0 for projection in projections), sum(projection <= 0 for projection in projections)),
    }
    jets = [tuple(row) for row in event]
    merge_gaps = []
    norm_min = float("inf")
    for count in (5, 4, 3):
        magnitudes = [norm(row[1:]) for row in jets]
        norm_min = min(norm_min, *magnitudes)
        if min(magnitudes) < 1e-8:
            raise ValueError("pseudojet spatial norm below 1e-8")
        distances = []
        for first, second in itertools.combinations(range(count), 2):
            cosine = dot(jets[first][1:], jets[second][1:]) / (magnitudes[first] * magnitudes[second])
            distance = (2 * min(jets[first][0], jets[second][0]) ** 2
                        * max(0.0, min(2.0, 1 - cosine)) / energy_sum ** 2)
            distances.append((distance, first, second))
        distances.sort()
        distance, first, second = distances[0]
        result[f"y{count - 1}{count}"] = distance
        merge_gaps.append(distances[1][0] - distance)
        jets[first] = add(jets[first], jets[second])
        del jets[second]
    result["merge_gap"] = min(merge_gaps)
    result["pseudojet_norm"] = norm_min
    return result


def physics(event):
    total_energy = math.fsum(row[0] for row in event)
    total_momentum = tuple(math.fsum(row[component] for row in event)
                           for component in (1, 2, 3))
    mass_error = max(abs(row[0] - norm(row[1:])) for row in event)
    pair_min = min(2 * (left[0] * right[0] - dot(left[1:], right[1:]))
                   for left, right in itertools.combinations(event, 2))
    return {"energy_sum_error": abs(total_energy - 1),
            "momentum_residual": norm(total_momentum), "massless_error": mass_error,
            "energy_min": min(row[0] for row in event), "sij_min": pair_min}


def rotate(event, quaternion):
    length = norm(quaternion)
    scalar, first, second, third = [value / length for value in quaternion]
    matrix = (
        (1 - 2 * (second ** 2 + third ** 2), 2 * (first * second - scalar * third),
         2 * (first * third + scalar * second)),
        (2 * (first * second + scalar * third), 1 - 2 * (first ** 2 + third ** 2),
         2 * (second * third - scalar * first)),
        (2 * (first * third - scalar * second), 2 * (second * third + scalar * first),
         1 - 2 * (first ** 2 + second ** 2)),
    )
    return [(row[0], *(dot(axis, row[1:]) for axis in matrix)) for row in event]
