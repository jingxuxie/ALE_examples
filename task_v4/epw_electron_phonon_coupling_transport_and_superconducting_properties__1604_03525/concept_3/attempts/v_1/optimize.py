import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog


DIMENSION = 18
FREQUENCIES = np.repeat(np.arange(1, 10), 2)
PAIRS = [(row, column) for row in range(DIMENSION)
         for column in range(row, DIMENSION)
         if (FREQUENCIES[row] - FREQUENCIES[column]) % 2 == 0
         and not (row < 2 and column < 2)]
ROWS = np.array([pair[0] for pair in PAIRS])
COLUMNS = np.array([pair[1] for pair in PAIRS])
MULTIPLICITY = np.where(ROWS == COLUMNS, 1, 2)
ERROR_WEIGHTS = (2 * np.pi / 1024) ** 2 / 4 * MULTIPLICITY * (
    FREQUENCIES[ROWS] ** 2 + FREQUENCIES[COLUMNS] ** 2)


def basis(angles):
    result = np.empty((len(angles), DIMENSION))
    result[:, 0::2] = np.sqrt(2) * np.cos(angles[:, None] * np.arange(1, 10))
    result[:, 1::2] = np.sqrt(2) * np.sin(angles[:, None] * np.arange(1, 10))
    return result


def matrix(coefficients):
    result = np.zeros((DIMENSION, DIMENSION))
    result[ROWS, COLUMNS] = coefficients
    result[COLUMNS, ROWS] = coefficients
    return result


def objective(coefficients):
    response = np.linalg.solve(np.eye(DIMENSION) - matrix(coefficients), np.eye(DIMENSION)[:, :2])
    value = np.trace(response[:2]) / 2
    derivative = response @ response.T / 2
    return value, derivative[ROWS, COLUMNS] * MULTIPLICITY


def grid_constraints(size):
    angles = np.arange(size) * (2 * np.pi / size)
    features = basis(angles)
    first, second = np.triu_indices(size)
    selected = (first < size // 2) & ((second < size // 2) | (first <= second - size // 2))
    first, second = first[selected], second[selected]
    design = features[first[:, None], ROWS] * features[second[:, None], COLUMNS]
    off_diagonal = ROWS != COLUMNS
    design[:, off_diagonal] += (features[first[:, None], COLUMNS] * features[second[:, None], ROWS])[:, off_diagonal]
    return design


def certify(coefficients, safety=1e-7):
    features = basis(np.arange(1024) * (2 * np.pi / 1024))
    kernel_minus_one = features @ matrix(coefficients) @ features.T
    error = ERROR_WEIGHTS @ np.abs(coefficients)
    lower_deviation = -kernel_minus_one.min() + error
    upper_deviation = kernel_minus_one.max() + error
    factor = min(1.0, (0.92 - safety) / lower_deviation,
                 (5.0 - safety) / upper_deviation)
    scaled = coefficients * factor
    return scaled, dict(scale=float(factor), error=float(error * factor),
                        minimum=float(1 + kernel_minus_one.min() * factor - error * factor),
                        maximum=float(1 + kernel_minus_one.max() * factor + error * factor),
                        trace=float(objective(scaled)[0]))


def save(coefficients, destination):
    certified, report = certify(coefficients)
    witness = dict(schema_version=1, kernel_a=np.zeros((18, 18)).tolist(),
                   kernel_b=matrix(certified).tolist())
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(witness, separators=(",", ":")))
    temporary.replace(destination)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=64)
    parser.add_argument("--restarts", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--margin", type=float, default=0.005)
    parser.add_argument("--initial", type=Path)
    parser.add_argument("--structured", action="store_true")
    parser.add_argument("--targeted", action="store_true")
    parser.add_argument("--algebraic", action="store_true")
    parser.add_argument("--directional", action="store_true")
    parser.add_argument("--pool", type=Path)
    parser.add_argument("--shaped", action="store_true")
    parser.add_argument("--method", default="highs")
    parser.add_argument("--output", type=Path, default=Path("witness.json"))
    arguments = parser.parse_args()
    design = grid_constraints(arguments.grid)
    constraints = np.concatenate((-design, design))
    upper = np.concatenate((np.full(len(design), .92 - arguments.margin),
                            np.full(len(design), 5.0 - arguments.margin)))
    generator = np.random.default_rng(arguments.seed)
    best = 1.0
    start = time.monotonic()
    pool = np.load(arguments.pool) if arguments.pool else None
    print("setup", design.shape, flush=True)
    if arguments.output.exists():
        previous = np.array(json.loads(arguments.output.read_text())["kernel_b"])
        best = objective(previous[ROWS, COLUMNS])[0]
    for restart in range(arguments.restarts):
        if pool is not None:
            coefficients = pool[restart % len(pool)][ROWS, COLUMNS]
        elif restart == 0 and arguments.initial:
            initial = np.array(json.loads(arguments.initial.read_text())["kernel_b"])
            coefficients = initial[ROWS, COLUMNS]
        else:
            coefficients = generator.normal(size=len(PAIRS)) * 0.003
        if arguments.structured or arguments.targeted or arguments.algebraic or arguments.shaped:
            angles = np.arange(2048) * (2 * np.pi / 2048)
            features = basis(angles)
            if arguments.shaped:
                shapes = np.zeros((len(angles), 2))
                for direction in range(2):
                    order = 3 if restart % 5 != 4 else 5
                    low_phase = generator.uniform(0, 2 * np.pi)
                    high_phase = generator.uniform(0, 2 * np.pi)
                    amplitude = generator.uniform(.5, 2.6)
                    shapes[:, direction] = np.tanh(generator.uniform(1., 8.) * (
                        np.cos(order * angles + high_phase) + amplitude * np.cos(angles + low_phase)))
                if restart % 2 == 0:
                    shapes[:, 1] = 0
                response = features.T @ shapes / len(angles)
            elif arguments.algebraic:
                amplitude = [.5, .75, 1., 1.25, 1.5, 2.][(restart // 4) % 6]
                response = np.zeros((18, 2))
                response[0, 0] = 1
                response[4, 0] = amplitude
                response[1, 1] = 1 if restart % 4 < 2 else 0
                response[5, 1] = amplitude * (1 if restart % 2 == 0 else -1) if restart % 4 < 2 else 0
                response[8, 0] = .25 * amplitude if restart % 4 == 3 else 0
            elif arguments.targeted:
                amplitude = 1.4 + .1 * (restart // 2)
                first_shape = np.tanh(6 * (np.cos(3 * angles) + amplitude * np.cos(angles)))
                second_shape = np.tanh(6 * (np.sin(3 * angles) - amplitude * np.sin(angles)))
                shapes = first_shape[:, None] if restart % 2 == 0 else np.column_stack((first_shape, second_shape))
                response = features.T @ shapes / len(angles)
            elif restart % 4 < 2:
                order = 3 if restart % 4 == 0 else 5
                amplitude = generator.uniform(.2, 1.8)
                shape = np.tanh(6 * (np.cos(order * angles) + amplitude * np.cos(angles)))
                response = (features.T @ shape / len(angles))[:, None]
            else:
                response = generator.normal(size=(18, 2))
                response[FREQUENCIES % 2 == 0] = 0
                response /= FREQUENCIES[:, None] ** .5
                response[:2] *= generator.uniform(.1, 1.5)
            derivative = response @ response.T
            seed_gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
            result = linprog(-seed_gradient, A_ub=constraints, b_ub=upper,
                             bounds=(-1, 1), method="highs")
            if result.success:
                coefficients = result.x
        for iteration in range(arguments.iterations):
            value, gradient = objective(coefficients)
            if arguments.directional:
                response = np.linalg.solve(np.eye(18) - matrix(coefficients), np.eye(18)[:, 0])
                value = response[0] / 2
                derivative = np.outer(response, response) / 2
                gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
            result = linprog(-gradient, A_ub=constraints, b_ub=upper,
                             bounds=(-1, 1), method=arguments.method,
                             options={"dual_feasibility_tolerance": 1e-8,
                                      "primal_feasibility_tolerance": 1e-8})
            if not result.success:
                result = linprog(-gradient, A_ub=constraints, b_ub=upper,
                                 bounds=(-1, 1), method="highs-ipm")
            if not result.success:
                print("LP failure", result.message, flush=True)
                break
            coefficients = result.x
            new_value = objective(coefficients)[0]
            trace_value = new_value
            if arguments.directional:
                new_value = np.linalg.solve(np.eye(18) - matrix(coefficients), np.eye(18)[:, 0])[0] / 2
            if iteration % 5 == 0:
                print("iterate", restart, iteration, round(new_value, 9),
                      round(time.monotonic() - start, 1), flush=True)
            if trace_value > best:
                certified, report = certify(coefficients)
                if report["trace"] > best:
                    best = report["trace"]
                    save(coefficients, arguments.output)
                    np.save(arguments.output.with_suffix(".raw.npy"), coefficients)
                    print("BEST", restart, iteration, json.dumps(report), flush=True)
            if iteration > 0 and new_value - value < 1e-7:
                break
        print("restart done", restart, "raw", new_value, "best", best, flush=True)


if __name__ == "__main__":
    main()
