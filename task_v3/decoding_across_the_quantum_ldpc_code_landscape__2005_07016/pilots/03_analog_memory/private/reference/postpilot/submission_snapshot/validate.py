import argparse
import os
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

from solve import build_model, solve_arrays


def row_basis(matrix):
    basis = {}
    for row in matrix:
        word = sum(1 << int(column) for column in np.flatnonzero(row))
        while word:
            pivot = word.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = word
                break
            word ^= basis[pivot]
    return basis


def in_row_space(row, basis):
    word = sum(1 << int(column) for column in np.flatnonzero(row))
    while word:
        pivot = word.bit_length() - 1
        if pivot not in basis:
            return False
        word ^= basis[pivot]
    return True


def toric3d(length):
    vertices = length**3
    count = 3 * vertices
    checks = np.zeros((count, count), dtype=np.uint8)
    stabilizers = np.zeros((vertices, count), dtype=np.uint8)
    metachecks = np.zeros((vertices, count), dtype=np.uint8)
    coordinates = list(np.ndindex(length, length, length))
    lookup = {coordinate: index for index, coordinate in enumerate(coordinates)}

    def shift(vertex, axis, direction=1):
        coordinate = list(coordinates[vertex])
        coordinate[axis] = (coordinate[axis] + direction) % length
        return lookup[tuple(coordinate)]

    planes = [(0, 1), (0, 2), (1, 2)]
    for vertex in range(vertices):
        for plane, (first, second) in enumerate(planes):
            face = 3 * vertex + plane
            for edge in (3 * vertex + first, 3 * shift(vertex, second) + first,
                         3 * vertex + second, 3 * shift(vertex, first) + second):
                checks[edge, face] ^= 1
            normal = 3 - first - second
            stabilizers[vertex, face] ^= 1
            stabilizers[vertex, 3 * shift(vertex, normal) + plane] ^= 1
        for axis in range(3):
            metachecks[vertex, 3 * vertex + axis] ^= 1
            metachecks[vertex, 3 * shift(vertex, axis, -1) + axis] ^= 1
    return checks, stabilizers, metachecks


def toric2d(length):
    count = length**2
    checks = np.zeros((count, 2 * count), dtype=np.uint8)
    stabilizers = np.zeros((count, 2 * count), dtype=np.uint8)
    for first in range(length):
        for second in range(length):
            vertex = first * length + second
            right = first * length + (second + 1) % length
            below = ((first + 1) % length) * length + second
            checks[vertex, 2 * vertex:2 * vertex + 2] = 1
            checks[right, 2 * vertex] = 1
            checks[below, 2 * vertex + 1] = 1
            stabilizers[vertex, [2 * vertex, 2 * vertex + 1, 2 * below, 2 * right + 1]] = 1
    return checks, stabilizers, np.ones((1, count), dtype=np.uint8)


def hypergraph_product(seed=195):
    random = np.random.default_rng(seed)
    classical = np.zeros((12, 20), dtype=np.uint8)
    for column in range(20):
        selected = random.choice(12, 3, replace=False)
        classical[selected, column] = 1
    checks = np.concatenate((np.kron(classical, np.eye(20, dtype=np.uint8)),
                             np.kron(np.eye(12, dtype=np.uint8), classical.T)), axis=1)
    stabilizers = np.concatenate((np.kron(np.eye(20, dtype=np.uint8), classical),
                                  np.kron(classical.T, np.eye(12, dtype=np.uint8))), axis=1)
    return checks, stabilizers, np.zeros((0, 240), dtype=np.uint8)


def generate(code, shots, rounds, probability, noise, seed):
    checks, stabilizers, metachecks = code
    assert not np.any((checks @ stabilizers.T) & 1)
    assert not np.any((metachecks @ checks) & 1)
    random = np.random.default_rng(seed)
    num_checks, num_qubits = checks.shape
    probabilities = probability * random.uniform(0.75, 1.25, (rounds, num_qubits))
    increments = (random.random((shots, rounds, num_qubits)) < probabilities).astype(np.uint8)
    history = (np.bitwise_xor.accumulate(increments, axis=1) @ checks.T) & 1
    offset = random.normal(0, 0.2, (rounds, num_checks))
    gain = random.uniform(0.7, 1.3, (rounds, num_checks))
    orientation = random.choice([-1, 1], (rounds, num_checks))
    mean0 = offset + gain * orientation
    mean1 = offset - gain * orientation
    sigma = noise * random.uniform(0.8, 1.2, (rounds, num_checks))
    readout = np.where(history, mean1, mean0) + random.normal(size=history.shape) * sigma
    case = dict(schema_version=np.array(1), case_id=np.array("authored-validation"),
                checks=checks, stabilizers=stabilizers, metachecks=metachecks,
                readout=readout, mean0=mean0, mean1=mean1, sigma=sigma,
                data_error_prob=probabilities, terminal_syndrome=history[:, -1])
    return case, increments, history


def verify(case, answer):
    increments = answer["increments"]
    history = answer["syndrome_history"]
    assert set(answer) == {"increments", "syndrome_history"}
    assert increments.dtype.kind in "biu" and history.dtype.kind in "biu"
    assert np.all((increments == 0) | (increments == 1))
    assert np.all((history == 0) | (history == 1))
    expected = (np.bitwise_xor.accumulate(increments, axis=1) @ case["checks"].T) & 1
    np.testing.assert_array_equal(history, expected)
    np.testing.assert_array_equal(history[:, -1], case["terminal_syndrome"])
    assert not np.any((history @ case["metachecks"].T) & 1)


def metrics(case, answer, increments, history):
    difference = np.bitwise_xor.reduce(answer["increments"] ^ increments, axis=1)
    basis = row_basis(case["stabilizers"])
    logical = np.mean([in_row_space(row, basis) for row in difference])
    actual = history[:, :-1]
    predicted = answer["syndrome_history"][:, :-1]
    accuracy = np.mean(predicted == actual)
    sensitivity = np.mean(predicted[actual == 1] == 1) if np.any(actual == 1) else 1.0
    specificity = np.mean(predicted[actual == 0] == 0) if np.any(actual == 0) else 1.0
    return logical, (sensitivity + specificity) / 2, accuracy


def exact_tests():
    checks = np.array([[1, 1, 0, 1], [0, 1, 1, 0], [1, 0, 1, 1]], dtype=np.uint8)
    stabilizers = np.array([[1, 0, 0, 1]], dtype=np.uint8)
    metachecks = np.ones((1, 3), dtype=np.uint8)
    case, actual, history = generate((checks, stabilizers, metachecks), 32, 2, 0.13, 1.15, 17)
    answer, statistics = solve_arrays(case, runs=8, refine=False)
    verify(case, answer)
    possibilities = ((np.arange(256)[:, None] >> np.arange(8)) & 1).astype(np.uint8).reshape(-1, 2, 4)
    all_history = (np.bitwise_xor.accumulate(possibilities, axis=1) @ checks.T) & 1
    data_prior = np.log((1 - case["data_error_prob"]) / case["data_error_prob"])
    likelihood = ((case["mean0"] - case["mean1"]) *
                  (case["readout"] - (case["mean0"] + case["mean1"]) / 2) / case["sigma"]**2)
    for shot in range(32):
        eligible = np.all(all_history[:, -1] == case["terminal_syndrome"][shot], axis=1)
        costs = (possibilities * data_prior).sum(axis=(1, 2)) + (all_history[:, :-1] * likelihood[shot, :-1]).sum(axis=(1, 2))
        result_cost = (answer["increments"][shot] * data_prior).sum() + (answer["syndrome_history"][shot, :-1] * likelihood[shot, :-1]).sum()
        assert abs(result_cost - costs[eligible].min()) < 1e-8, (shot, result_cost, costs[eligible].min())
    matrix, base_rows, pointers, columns = build_model(checks, stabilizers, metachecks, 2)
    for start, stop in zip(pointers[:-1], pointers[1:]):
        vector = np.zeros(matrix.shape[1], dtype=np.uint8)
        vector[columns[start:stop]] = 1
        assert not np.any((matrix @ vector) & 1)
    altered = dict(case)
    altered["readout"] = case["readout"].copy()
    altered["readout"][:, -1] += 100000
    alternative, _ = solve_arrays(altered, runs=8, refine=False)
    np.testing.assert_array_equal(answer["increments"], alternative["increments"])
    refined, _ = solve_arrays(case, runs=8, refine=True)
    verify(case, refined)
    np.testing.assert_array_equal(np.bitwise_xor.reduce(answer["increments"], axis=1),
                                  np.bitwise_xor.reduce(refined["increments"], axis=1))
    print("Exact enumeration: all 32 MAP solutions correct; kernel, boundary, and final-state invariance pass", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=["example", "toric3d", "toric2d", "hgp"], default="example")
    parser.add_argument("--size", type=int, default=3)
    parser.add_argument("--shots", type=int, default=64)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--probability", type=float, default=0.06)
    parser.add_argument("--noise", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=793)
    parser.add_argument("--runs", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=70)
    parser.add_argument("--order", type=int, default=40)
    parser.add_argument("--save")
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--sweeps", type=int, default=800)
    arguments = parser.parse_args()
    if arguments.exact:
        exact_tests()
    if arguments.family == "example":
        with np.load("../participant/input/example.npz") as supplied:
            code = tuple(supplied[key] for key in ("checks", "stabilizers", "metachecks"))
    elif arguments.family == "toric3d":
        code = toric3d(arguments.size)
    elif arguments.family == "toric2d":
        code = toric2d(arguments.size)
    else:
        code = hypergraph_product()
    case, actual, history = generate(code, arguments.shots, arguments.rounds, arguments.probability, arguments.noise, arguments.seed)
    if arguments.save:
        np.savez_compressed(arguments.save, **case)
    start = time.process_time()
    answer, statistics = solve_arrays(case, runs=arguments.runs, iterations=arguments.iterations, order=arguments.order,
                                      refine=arguments.refine, refine_sweeps=arguments.sweeps)
    elapsed = time.process_time() - start
    verify(case, answer)
    logical, balanced, accuracy = metrics(case, answer, actual, history)
    print("family", arguments.family, "shape", code[0].shape, "shots", arguments.shots,
          "logical", round(logical, 5), "balanced", round(balanced, 5), "accuracy", round(accuracy, 5),
          "cpu", round(elapsed, 3), "cost", round(statistics[:, 0].mean(), 3),
          "runs", statistics[:, 1].mean(), "converged", statistics[:, 2].mean(), flush=True)


if __name__ == "__main__":
    main()
