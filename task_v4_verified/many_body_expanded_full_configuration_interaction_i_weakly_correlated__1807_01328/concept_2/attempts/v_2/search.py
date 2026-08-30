import argparse
import itertools
import json
import os
from pathlib import Path
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares, minimize


ROOT = Path(__file__).resolve().parent
INPUT = Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_2/adversary/ratchet_1/participant/input")
TARGET = json.loads((INPUT / "target.json").read_text())
EDGES = list(itertools.combinations(range(7), 2))
EDGE_INDEX = {edge: index for index, edge in enumerate(EDGES)}
BOUNDS = np.array([0.45] * 21 + [0.60] * 21)
TRIPLES = list(itertools.combinations(range(7), 3))


def witness(coefficients):
    result = {"schema_version": 1}
    for offset, field in [(0, "virtual_hopping"), (21, "virtual_density")]:
        block = np.zeros((7, 7))
        for edge_index, (row, column) in enumerate(EDGES):
            block[row, column] = block[column, row] = float(coefficients[offset + edge_index])
        result[field] = block.tolist()
    return result


def save(coefficients, name):
    (ROOT / name).write_text(json.dumps(witness(coefficients), indent=2, allow_nan=False) + "\n")


def load(name):
    candidate = json.loads(Path(name).read_text())
    return np.array([candidate[field][row][column] for field in ("virtual_hopping", "virtual_density") for row, column in EDGES])


class Block:
    def __init__(self, virtuals):
        orbitals = list(range(3)) + [index + 3 for index in virtuals]
        states = list(itertools.combinations(orbitals, 3))
        lookup = {state: index for index, state in enumerate(states)}
        occupation = np.zeros((len(states), 10))
        for state_index, state in enumerate(states):
            occupation[state_index, list(state)] = 1
        density = np.array(TARGET["background_density"])
        diagonal = occupation @ np.array(TARGET["pair_energy_eh"])
        diagonal += 0.5 * np.sum((occupation @ density) * occupation, axis=1)
        self.base = np.diag(diagonal)
        fixed_hopping = np.zeros((10, 10))
        fixed_hopping[:3, 3:] = np.array(TARGET["occupied_virtual_hopping"])
        fixed_hopping[3:, :3] = fixed_hopping[:3, 3:].T
        rows, columns, parameters = [], [], []
        for row, state in enumerate(states):
            for source in state:
                for destination in orbitals:
                    if destination in state:
                        continue
                    child = tuple(sorted((set(state) - {source}) | {destination}))
                    column = lookup[child]
                    if column >= row:
                        continue
                    self.base[row, column] = self.base[column, row] = fixed_hopping[source, destination]
                    if min(source, destination) >= 3:
                        rows.append(row)
                        columns.append(column)
                        parameters.append(EDGE_INDEX[tuple(sorted((source - 3, destination - 3)))])
        self.rows = np.array(rows, dtype=int)
        self.columns = np.array(columns, dtype=int)
        self.parameters = np.array(parameters, dtype=int)
        self.density = np.array([occupation[:, row + 3] * occupation[:, column + 3] for row, column in EDGES]).T
        self.diagonal_index = np.diag_indices(len(states))
        local_edges = [EDGE_INDEX[edge] for edge in itertools.combinations(virtuals, 2)]
        self.local_parameters = np.array(local_edges + [index + 21 for index in local_edges], dtype=int)
        self.operators = np.zeros((len(self.local_parameters), len(states), len(states)))
        for local_index, parameter in enumerate(self.local_parameters):
            if parameter < 21:
                selected = self.parameters == parameter
                self.operators[local_index, self.rows[selected], self.columns[selected]] = 1
                self.operators[local_index, self.columns[selected], self.rows[selected]] = 1
            else:
                self.operators[local_index][self.diagonal_index] = self.density[:, parameter - 21]

    def solve(self, coefficients, full=False):
        matrix = self.base.copy()
        matrix[self.rows, self.columns] = matrix[self.columns, self.rows] = coefficients[self.parameters]
        matrix[self.diagonal_index] += self.density @ coefficients[21:]
        values, vectors = eigh(matrix, subset_by_index=(0, 1 if full else 0), check_finite=False, overwrite_a=True)
        ground = vectors[:, 0]
        gradient = np.empty(42)
        gradient[:21] = np.bincount(self.parameters, weights=2 * ground[self.rows] * ground[self.columns], minlength=21)
        gradient[21:] = self.density.T @ (ground ** 2)
        if full:
            properties = np.array([ground[0] ** 2, values[1] - values[0], np.min(np.diag(matrix)[1:] - self.base[0, 0])])
            return values[0], gradient, properties
        return values[0], gradient

    def second_order(self, coefficients):
        matrix = self.base.copy()
        matrix[self.rows, self.columns] = matrix[self.columns, self.rows] = coefficients[self.parameters]
        matrix[self.diagonal_index] += self.density @ coefficients[21:]
        values, vectors = eigh(matrix, check_finite=False, overwrite_a=True, driver="evr")
        ground = vectors[:, 0]
        actions = self.operators @ ground
        gradient = np.zeros(42)
        gradient[self.local_parameters] = actions @ ground
        projections = actions @ vectors[:, 1:]
        local_hessian = (projections * (2 / (values[0] - values[1:]))) @ projections.T
        hessian = np.zeros((42, 42))
        hessian[np.ix_(self.local_parameters, self.local_parameters)] = local_hessian
        return values[0], gradient, hessian


class Engine:
    def __init__(self):
        zeros = np.zeros(42)
        self.reference = Block([]).base[0, 0]
        self.single_energies = np.array([Block([index]).solve(zeros)[0] for index in range(7)])
        self.pairs = [Block(edge) for edge in EDGES]
        self.triples = [Block(triple) for triple in TRIPLES]
        self.full = Block(range(7))
        self.parents = np.array([[EDGE_INDEX[edge] for edge in itertools.combinations(triple, 2)] for triple in TRIPLES])
        self.triple_constants = np.array([self.single_energies[list(triple)].sum() - self.reference for triple in TRIPLES])
        self.truncation_constant = -20 * self.reference + 10 * self.single_energies.sum()
        self.count = 0

    def evaluate(self, coefficients, full=True, second_order=False):
        pair_results = [(block.second_order(coefficients) if second_order else block.solve(coefficients)) for block in self.pairs]
        triple_results = [(block.second_order(coefficients) if second_order else block.solve(coefficients)) for block in self.triples]
        pair_energy = np.array([result[0] for result in pair_results])
        pair_gradient = np.array([result[1] for result in pair_results])
        triple_energy = np.array([result[0] for result in triple_results])
        triple_gradient = np.array([result[1] for result in triple_results])
        increments = triple_energy - pair_energy[self.parents].sum(axis=1) + self.triple_constants
        jacobian = triple_gradient - pair_gradient[self.parents].sum(axis=1)
        if second_order:
            pair_hessian = np.array([result[2] for result in pair_results])
            triple_hessian = np.array([result[2] for result in triple_results])
            increment_hessian = triple_hessian - pair_hessian[self.parents].sum(axis=1)
        self.count += 1
        if not full:
            result = increments * 1e6, jacobian * 1e6
            return result + (increment_hessian * 1e6,) if second_order else result
        energy, gradient, properties = self.full.solve(coefficients, full=True)
        truncation = self.truncation_constant - 4 * pair_energy.sum() + triple_energy.sum()
        tail = energy - truncation
        tail_gradient = gradient + 4 * pair_gradient.sum(axis=0) - triple_gradient.sum(axis=0)
        result = increments * 1e6, jacobian * 1e6, tail * 1e6, tail_gradient * 1e6, properties
        return result + (increment_hessian * 1e6,) if second_order else result

    def summary(self, coefficients):
        increments, jacobian, tail, tail_gradient, properties = self.evaluate(coefficients)
        maximum = np.max(np.abs(increments))
        return dict(max_triple=float(maximum), tail=float(tail), ratio=float(abs(tail) / max(maximum, 1e-4)), weight=float(properties[0]), gap=float(properties[1]), margin=float(properties[2]), max_noise_sigma=float(np.max(np.linalg.norm(jacobian, axis=1)) * 0.001 / np.sqrt(3)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="explore")
    parser.add_argument("--seed", type=int, default=147)
    parser.add_argument("--seconds", type=float, default=300)
    parser.add_argument("--start")
    parser.add_argument("--tail", type=float, default=-100)
    arguments = parser.parse_args()
    engine = Engine()
    generator = np.random.default_rng(arguments.seed)
    coefficients = np.zeros(42) if arguments.start is None else load(arguments.start)
    print("Initial", engine.summary(coefficients), flush=True)
    if arguments.mode == "benchmark":
        started = time.monotonic()
        for repeat in range(100):
            engine.evaluate(coefficients)
        print("Seconds per call", (time.monotonic() - started) / 100, flush=True)
        return
    started = time.monotonic()
    attempt = 0
    best_score = np.inf
    while time.monotonic() - started < arguments.seconds:
        if attempt:
            coefficients = generator.uniform(-1, 1, 42) * BOUNDS * generator.uniform(0.15, 0.9)
        cache_coefficients = None
        cache_result = None

        def objective(values, derivative=False):
            nonlocal cache_coefficients, cache_result
            if cache_coefficients is None or not np.array_equal(values, cache_coefficients):
                increments, jacobian, tail, tail_gradient, properties = engine.evaluate(values)
                residual = np.r_[increments, (tail - arguments.tail) * 0.2]
                derivatives = np.vstack([jacobian, tail_gradient * 0.2])
                cache_coefficients = values.copy()
                cache_result = residual, derivatives
            return cache_result[int(derivative)]

        result = least_squares(objective, coefficients, jac=lambda values: objective(values, True), bounds=(-BOUNDS + 1e-9, BOUNDS - 1e-9), max_nfev=400, ftol=1e-10, xtol=1e-10, gtol=1e-8)
        coefficients = result.x
        summary = engine.summary(coefficients)
        score = max(summary["max_triple"], abs(summary["tail"] - arguments.tail) * 0.2)
        print("Attempt", attempt, "calls", result.nfev, "cost", result.cost, "time", time.monotonic() - started, summary, flush=True)
        save(coefficients, "candidate_%03d.json" % attempt)
        if score < best_score:
            best_score = score
            save(coefficients, "best_nominal.json")
        attempt += 1


if __name__ == "__main__":
    main()
