import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares, minimize

ASSETS = Path(os.environ.get("ASSETS", "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_2/adversary/ratchet_2/participant"))
sys.path.insert(0, str(ASSETS / "workspace"))
import model
import assay

EDGES = list(itertools.combinations(range(10), 2))
VV = [index for index, edge in enumerate(EDGES) if edge[0] >= 3]
CONTROL = np.array([10 + index for index in VV] + [55 + index for index in VV])
BOUNDS = np.array([0.45] * 21 + [0.6] * 21)
MASKS = [mask for mask in range(128) if mask.bit_count() <= 3] + [127]
TRIPLES = [mask for mask in MASKS if mask.bit_count() == 3]
TRANSFORM = np.zeros((36, len(MASKS)))
for row, mask in enumerate(TRIPLES):
    for column, submask in enumerate(MASKS):
        if submask & mask == submask:
            TRANSFORM[row, column] = (-1) ** (3 - submask.bit_count())
for column, mask in enumerate(MASKS):
    TRANSFORM[-1, column] = {0: 20, 1: -10, 2: 4, 3: -1, 7: 1}[mask.bit_count()]


def coefficients(witness):
    energies, hopping, density = model.full_coefficients(witness)
    return np.r_[energies, [hopping[edge] for edge in EDGES], [density[edge] for edge in EDGES]]


BASE = coefficients(model.load_witness(ASSETS / "input/baseline_witness.json"))


def artifact(controls):
    matrices = []
    for entries in (controls[:21], controls[21:]):
        matrix = np.zeros((7, 7))
        for edge, value in zip(itertools.combinations(range(7), 2), entries):
            matrix[edge] = matrix[edge[::-1]] = float(value)
        matrices.append(matrix.tolist())
    return dict(schema_version=1, virtual_hopping=matrices[0], virtual_density=matrices[1])


def save(path, controls):
    Path(path).write_text(json.dumps(artifact(controls), indent=2, allow_nan=False) + "\n")


class Engine:
    def __init__(self):
        self.parts = []
        for mask in MASKS:
            occupation, (rows, columns, sources, destinations) = model.topology(mask)
            dimension = len(occupation)
            operators = np.zeros((100, dimension, dimension))
            diagonal = np.arange(dimension)
            operators[:10, diagonal, diagonal] = occupation.T
            for edge_index, (source, destination) in enumerate(EDGES):
                selected = ((sources == source) & (destinations == destination)) | ((sources == destination) & (destinations == source))
                operators[10 + edge_index, rows[selected], columns[selected]] = 1
                operators[10 + edge_index, columns[selected], rows[selected]] = 1
                operators[55 + edge_index, diagonal, diagonal] = occupation[:, source] * occupation[:, destination]
            active = np.flatnonzero(np.any(operators != 0, axis=(1, 2)))
            self.parts.append((operators, active, operators[active]))
        self.last = None

    def evaluate(self, controls, hessian=False, theta=None):
        if theta is None:
            theta = BASE.copy()
            theta[CONTROL] = controls
        energies = np.empty(len(MASKS))
        gradients = np.zeros((len(MASKS), 100))
        hessians = np.zeros((len(MASKS), 100, 42)) if hessian else None
        for part_index, (operators, active, compact) in enumerate(self.parts):
            matrix = np.tensordot(theta[active], compact, axes=1)
            if hessian:
                values, vectors = eigh(matrix, check_finite=False, driver="evr")
            else:
                values, vectors = eigh(matrix, subset_by_index=(0, min(1, len(matrix) - 1)), check_finite=False, driver="evr")
            ground = vectors[:, 0]
            energies[part_index] = values[0]
            actions = compact @ ground
            gradients[part_index, active] = actions @ ground
            if hessian and len(values) > 1:
                couplings = actions @ vectors[:, 1:]
                compact_hessian = 2 * (couplings / (values[0] - values[1:])) @ couplings.T
                control_active, active_positions, control_positions = np.intersect1d(active, CONTROL, return_indices=True)
                hessians[part_index][np.ix_(active, control_positions)] = compact_hessian[:, active_positions]
            if part_index == len(MASKS) - 1:
                physical = np.array([ground[0] ** 2, values[1] - values[0], np.min(np.diag(matrix)[1:] - matrix[0, 0])])
                if hessian:
                    physical_jacobian = np.zeros((2, 100))
                    physical_jacobian[0, active] = 2 * ground[0] * (couplings @ (vectors[0, 1:] / (values[0] - values[1:])))
                    excited = vectors[:, 1]
                    physical_jacobian[1, active] = (compact @ excited) @ excited - gradients[part_index, active]
                    self.physical_jacobian = physical_jacobian[:, CONTROL]
        metrics = TRANSFORM @ energies
        jacobian = TRANSFORM @ gradients
        if hessian:
            curvature = np.tensordot(TRANSFORM, hessians, axes=1)
            return metrics, jacobian, physical, curvature
        return metrics, jacobian, physical

    def summary(self, controls):
        metrics, jacobian, physical = self.evaluate(controls)
        sigma = 1e3 / np.sqrt(3) * np.linalg.norm(jacobian[:35], axis=1)
        return dict(parent=float(np.max(np.abs(metrics[:35])) * 1e6), tail=float(metrics[-1] * 1e6), sigma=float(max(sigma)), physical=physical.tolist())


def nominal_search(arguments):
    engine = Engine()
    rng = np.random.default_rng(arguments.seed)
    start = time.monotonic()
    best = np.inf
    for trial in range(arguments.trials):
        if arguments.start:
            center = coefficients(model.load_witness(arguments.start))[CONTROL]
            initial = center if trial == 0 else np.clip(center + rng.normal(0, arguments.spread, 42), -BOUNDS + 1e-7, BOUNDS - 1e-7)
        else:
            initial = np.r_[rng.normal(0, arguments.spread, 21), rng.uniform(-0.5, 0.5, 21)]
            if arguments.structured > 0:
                block = list(itertools.combinations(range(7), arguments.structured))[trial % len(list(itertools.combinations(range(7), arguments.structured)))]
                for edge_index, edge in enumerate(itertools.combinations(range(7), 2)):
                    if not set(edge).issubset(block):
                        initial[edge_index] = 0
            elif arguments.structured == -1:
                initial[:21] = 0
                ordering = rng.permutation(7)
                local_edges = list(itertools.combinations(range(7), 2))
                for position in range(0, 6, 2):
                    edge = tuple(sorted(ordering[position:position+2]))
                    initial[local_edges.index(edge)] = rng.choice([-1, 1]) * rng.uniform(.3, .4488)
            elif arguments.structured == -2:
                for edge_index, edge in enumerate(itertools.combinations(range(7), 2)):
                    if 3 not in edge:
                        initial[edge_index] = 0
            initial = np.clip(initial, -BOUNDS + 0.0012, BOUNDS - 0.0012)
        cached = {}

        def objective(controls):
            if "controls" not in cached or not np.array_equal(controls, cached["controls"]):
                metrics, jacobian, physical = engine.evaluate(controls)
                residual = np.r_[metrics[:35] * 1e6, (metrics[-1] * 1e6 - arguments.tail) * arguments.tail_weight]
                derivative = jacobian[:, CONTROL] * 1e6
                derivative[-1] *= arguments.tail_weight
                cached.update(controls=controls.copy(), residual=residual, derivative=derivative)
            return cached

        result = least_squares(lambda controls: objective(controls)["residual"], initial, jac=lambda controls: objective(controls)["derivative"], bounds=(-BOUNDS + 0.0011, BOUNDS - 0.0011), max_nfev=arguments.iterations, ftol=1e-10, xtol=1e-10, gtol=1e-8)
        summary = engine.summary(result.x)
        quality = np.linalg.norm(result.fun)
        if quality < best:
            best = quality
            save(arguments.output, result.x)
        save(arguments.prefix + "_%03d.json" % trial, result.x)
        print(json.dumps(dict(trial=trial, elapsed=time.monotonic()-start, quality=quality, evaluations=result.nfev, **summary)), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=987)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--spread", type=float, default=0.13)
    parser.add_argument("--tail", type=float, default=-100)
    parser.add_argument("--tail-weight", type=float, default=0.05)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--start")
    parser.add_argument("--output", default="nominal.json")
    parser.add_argument("--prefix", default="trial")
    parser.add_argument("--structured", type=int, default=0)
    nominal_search(parser.parse_args())
