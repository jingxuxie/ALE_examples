import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import FREQUENCIES, basis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=60)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--seed", type=int, default=442)
    arguments = parser.parse_args()
    count = arguments.count
    half = count // 2
    first, second = np.triu_indices(half)
    size = len(first)
    multiplicity = np.where(first == second, 1, 2)
    angles = np.arange(count) * 2 * np.pi / count
    features = basis(angles)
    velocity = features[:half, :2] / np.sqrt(2)
    equality = np.zeros((half + 3, 2 * size))
    for index in range(size):
        equality[first[index], index] += 1
        if first[index] != second[index]:
            equality[second[index], index] += 1
    equality[:half, size:] = equality[:half, :size]
    equality[half, :size] = multiplicity * velocity[first, 0] * velocity[second, 0]
    equality[half + 1, :size] = multiplicity * velocity[first, 1] * velocity[second, 1]
    equality[half + 2, :size] = multiplicity * (velocity[first, 0] * velocity[second, 1] + velocity[first, 1] * velocity[second, 0]) / 2
    equality[half:, size:] = -equality[half:, :size]
    target = np.concatenate((np.full(half, count), np.zeros(3)))
    generator = np.random.default_rng(arguments.seed)
    seeds = []
    for restart in range(arguments.restarts):
        harmonics = np.zeros((18, 2))
        harmonics[FREQUENCIES % 2 == 1] = generator.normal(size=(10, 2)) / FREQUENCIES[FREQUENCIES % 2 == 1, None]
        if restart % 3 == 0:
            harmonics[:] = 0
            harmonics[0, 0] = generator.uniform(1., 2.5)
            harmonics[4, 0] = 1
            harmonics[1, 1] = generator.uniform(0., 2.)
            harmonics[5, 1] = generator.choice([-1, 1])
        response = features[:half] @ harmonics
        response = np.tanh(response * generator.uniform(.5, 4.))
        old_value = 0
        for iteration in range(35):
            derivative = response @ response.T
            gradient = derivative[first, second] * multiplicity
            result = linprog(np.concatenate((-gradient, gradient)),
                             A_eq=equality, b_eq=target, bounds=(.08, 6), method="highs")
            if not result.success:
                print("failure", result.message, flush=True)
                break
            direct = np.zeros((half, half))
            opposite = np.zeros((half, half))
            direct[first, second] = direct[second, first] = result.x[:size]
            opposite[first, second] = opposite[second, first] = result.x[size:]
            response = np.linalg.solve(np.eye(half) - (direct - opposite) / count, velocity)
            value = np.trace(velocity.T @ response) / half
            if value - old_value < 1e-7:
                break
            old_value = value
        kernel = np.block([[direct, opposite], [opposite, direct]])
        coefficients = features.T @ kernel @ features / count ** 2
        coefficients = (coefficients + coefficients.T) / 2
        coefficients[:2, :2] = 0
        coefficients[(FREQUENCIES[:, None] - FREQUENCIES[None, :]) % 2 != 0] = 0
        projected = np.trace(np.linalg.solve(np.eye(18) - coefficients, np.eye(18)[:, :2])[:2]) / 2
        seeds.append(coefficients)
        print("seed", restart, "discrete", value, "projected", projected, flush=True)
    np.save("discrete_seeds.npy", np.array(seeds))


if __name__ == "__main__":
    main()
