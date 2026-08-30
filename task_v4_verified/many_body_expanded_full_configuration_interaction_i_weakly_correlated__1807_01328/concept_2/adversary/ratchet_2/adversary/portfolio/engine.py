import collections
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh, solve
from scipy.optimize import least_squares


PORTFOLIO = Path(__file__).resolve().parent
ROOT = PORTFOLIO.parents[1]
BUDGET = json.loads((PORTFOLIO / "budget.json").read_text())
DEADLINE = BUDGET["deadline_epoch"]
SEARCH_DEADLINE = DEADLINE - BUDGET["optimization_reserve_seconds"]
EDGES = [(row, column) for row in range(7) for column in range(row + 1, 7)]
FIELDS = ("virtual_hopping", "virtual_density")
BOUNDS = np.array([0.45] * 21 + [0.60] * 21)
PAIR_MASKS = [mask for mask in range(128) if mask.bit_count() == 2]
TRIPLE_MASKS = [mask for mask in range(128) if mask.bit_count() == 3]


def load_module(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


MODEL = load_module("portfolio_public_model", "participant/workspace/model.py")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def encode(parameters):
    candidate = {"schema_version": 1}
    for field_index, field in enumerate(FIELDS):
        matrix = [[0.0] * 7 for row in range(7)]
        for edge_index, (row, column) in enumerate(EDGES):
            matrix[row][column] = matrix[column][row] = float(parameters[field_index * 21 + edge_index])
        candidate[field] = matrix
    return candidate


def decode(candidate):
    return np.array([candidate[field][row][column] for field in FIELDS for row, column in EDGES])


def sample(parameters, uniforms):
    lower = np.maximum(-BOUNDS, parameters - 0.001)
    upper = np.minimum(BOUNDS, parameters + 0.001)
    lower_derivative = (parameters - 0.001 > -BOUNDS).astype(float)
    upper_derivative = (parameters + 0.001 < BOUNDS).astype(float)
    return lower + uniforms * (upper - lower), lower_derivative + uniforms * (upper_derivative - lower_derivative)


class TimeLimit(Exception):
    pass


class Engine:
    def __init__(self, coefficients=None, derivative_cache=None):
        self.diagonalizations = 0
        self.points = 0
        self.cache = {}
        pair_energy, hopping, density = MODEL.full_coefficients(encode(np.zeros(42))) if coefficients is None else coefficients
        for mask in [0] + [1 << index for index in range(7)] + PAIR_MASKS + TRIPLE_MASKS + [127]:
            occupation, (rows, columns, sources, destinations) = MODEL.topology(mask)
            base = MODEL.hamiltonian(mask, hopping, density, pair_energy)
            if derivative_cache is not None:
                indices, derivatives = derivative_cache[mask][1:]
                self.cache[mask] = (base, indices, derivatives)
                continue
            indices, derivatives = [], []
            for edge_index, (row, column) in enumerate(EDGES):
                if not (mask & (1 << row) and mask & (1 << column)):
                    continue
                derivative = np.zeros_like(base)
                selected = ((sources == row + 3) & (destinations == column + 3)) | ((sources == column + 3) & (destinations == row + 3))
                derivative[rows[selected], columns[selected]] = 1.0
                derivative[columns[selected], rows[selected]] = 1.0
                indices.extend((edge_index, 21 + edge_index))
                derivatives.extend((derivative, np.diag(occupation[:, row + 3] * occupation[:, column + 3])))
            self.cache[mask] = (base, np.array(indices, dtype=int), np.array(derivatives))
        self.reference = self.cache[0][0][0, 0]
        self.singles = {1 << index: eigh(self.cache[1 << index][0], eigvals_only=True, subset_by_index=(0, 0))[0] for index in range(7)}
        self.single_sum = math.fsum(value - self.reference for value in self.singles.values())

    def eigensystem(self, mask, parameters, full=False):
        base, indices, derivatives = self.cache[mask]
        matrix = base + np.einsum("a,aij->ij", parameters[indices], derivatives, optimize=False)
        values, vectors = eigh(matrix, subset_by_index=(0, 1 if full else 0), check_finite=False)
        self.diagonalizations += 1
        gradient = np.zeros(42)
        gradient[indices] = np.einsum("aij,i,j->a", derivatives, vectors[:, 0], vectors[:, 0], optimize=False)
        return values, vectors, gradient, matrix, indices, derivatives

    def point(self, parameters):
        self.points += 1
        pair_energies, pair_gradients, pair_increments = {}, {}, []
        for mask in PAIR_MASKS:
            values, vectors, gradient, matrix, indices, derivatives = self.eigensystem(mask, parameters)
            pair_energies[mask], pair_gradients[mask] = values[0], gradient
            pair_increments.append(values[0] - math.fsum(self.singles[1 << index] for index in range(7) if mask & (1 << index)) + self.reference)
        triples, triple_gradients = [], []
        for mask in TRIPLE_MASKS:
            values, vectors, gradient, matrix, indices, derivatives = self.eigensystem(mask, parameters)
            parents = [mask ^ (1 << index) for index in range(7) if mask & (1 << index)]
            triples.append(values[0] - math.fsum(pair_energies[parent] for parent in parents) + math.fsum(self.singles[1 << index] for index in range(7) if mask & (1 << index)) - self.reference)
            triple_gradients.append(gradient - sum((pair_gradients[parent] for parent in parents), np.zeros(42)))
        triples = np.array(triples)
        triple_gradients = np.array(triple_gradients)
        truncation = self.reference + self.single_sum + math.fsum(pair_increments) + math.fsum(triples)
        values, vectors, gradient, matrix, indices, derivatives = self.eigensystem(127, parameters, full=True)
        tail = float(values[0] - truncation)
        tail_gradient = gradient - sum(pair_gradients.values(), np.zeros(42)) - np.sum(triple_gradients, axis=0)
        weight = float(vectors[0, 0] ** 2)
        gap = float(values[1] - values[0])
        gap_gradient = np.zeros(42)
        gap_gradient[indices] = np.einsum("aij,i,j->a", derivatives, vectors[:, 1], vectors[:, 1], optimize=False)
        gap_gradient -= gradient
        weight_gradient = np.zeros(42)
        if weight < 0.962 and gap > 0.02:
            ground = vectors[:, 0]
            right = -(np.einsum("aij,j->ia", derivatives, ground, optimize=False) - np.outer(ground, gradient[indices]))
            response = solve(matrix - values[0] * np.eye(len(matrix)) + np.outer(ground, ground), right, assume_a="pos", check_finite=False)
            weight_gradient[indices] = 2 * ground[0] * response[0]
        diagonal_index = 1 + np.argmin(np.diag(matrix)[1:] - self.reference)
        margin = float(matrix[diagonal_index, diagonal_index] - self.reference)
        margin_gradient = np.zeros(42)
        margin_gradient[indices] = derivatives[:, diagonal_index, diagonal_index]
        return dict(triples=triples, triple_gradients=triple_gradients, tail=tail, tail_gradient=tail_gradient, weight=weight, weight_gradient=weight_gradient, gap=gap, gap_gradient=gap_gradient, margin=margin, margin_gradient=margin_gradient, energy=float(values[0]))


def diagnostic(point):
    parent = float(np.max(np.abs(point["triples"])))
    tail = abs(point["tail"])
    ratio = tail / max(parent, 1e-10)
    valid = point["weight"] >= 0.95 and point["gap"] >= 0.4 and point["margin"] >= 0.6
    passed = valid and parent <= 1e-6 and tail >= 50e-6 and ratio >= 100
    score = min(1.0, 1e-6 / max(parent, 1e-10), tail / 50e-6, ratio / 100) if valid else 0.0
    return dict(valid=valid, passed=passed, core_score=score, max_abs_triple_eh=parent, tail_eh=tail, signed_tail_eh=point["tail"], ratio=ratio, hf_weight=point["weight"], spectral_gap_eh=point["gap"], diagonal_margin_eh=point["margin"])
