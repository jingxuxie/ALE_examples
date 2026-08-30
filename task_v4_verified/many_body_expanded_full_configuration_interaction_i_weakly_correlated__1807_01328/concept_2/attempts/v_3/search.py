import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares, minimize

PARTICIPANT = Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_2/adversary/ratchet_2/participant")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PARTICIPANT / "workspace"))
import assay
import model

EDGES = list(itertools.combinations(range(10), 2))
VIRTUAL_EDGES = list(itertools.combinations(range(7), 2))
CONTROL = np.array([offset + EDGES.index((source + 3, destination + 3))
                    for offset in (10, 55) for source, destination in VIRTUAL_EDGES])
BOUND = np.array([0.45] * 21 + [0.60] * 21)
ZERO = {"schema_version": 1, "virtual_hopping": np.zeros((7, 7)).tolist(),
        "virtual_density": np.zeros((7, 7)).tolist()}


def pack(coefficients):
    energies, hopping, density = coefficients
    return np.r_[energies, [hopping[source, destination] for source, destination in EDGES],
                 [density[source, destination] for source, destination in EDGES]]


BASE = pack(model.full_coefficients(ZERO))


def witness(controls):
    matrices = []
    for block in (controls[:21], controls[21:]):
        matrix = np.zeros((7, 7))
        for value, (source, destination) in zip(block, VIRTUAL_EDGES):
            matrix[source, destination] = matrix[destination, source] = float(value)
        matrices.append(matrix.tolist())
    return dict(schema_version=1, virtual_hopping=matrices[0], virtual_density=matrices[1])


def save(controls, name):
    (ROOT / name).write_text(json.dumps(witness(controls), indent=2, allow_nan=False) + "\n")


def load(name):
    return pack(model.full_coefficients(model.load_witness(ROOT / name)))[CONTROL]


class Space:
    def __init__(self, mask):
        occupation, (rows, columns, sources, destinations) = model.topology(mask)
        orbitals = np.flatnonzero(occupation.sum(axis=0))
        active_edges = [index for index, (source, destination) in enumerate(EDGES)
                        if source in orbitals and destination in orbitals]
        self.active = np.r_[orbitals, np.array(active_edges) + 10, np.array(active_edges) + 55].astype(int)
        dimension = len(occupation)
        self.features = np.zeros((len(self.active), dimension, dimension))
        diagonal = np.arange(dimension)
        for position, coordinate in enumerate(self.active):
            if coordinate < 10:
                self.features[position, diagonal, diagonal] = occupation[:, coordinate]
            elif coordinate < 55:
                source, destination = EDGES[coordinate - 10]
                selected = ((sources == source) & (destinations == destination)) | ((sources == destination) & (destinations == source))
                self.features[position, rows[selected], columns[selected]] = 1
                self.features[position, columns[selected], rows[selected]] = 1
            else:
                source, destination = EDGES[coordinate - 55]
                self.features[position, diagonal, diagonal] = occupation[:, source] * occupation[:, destination]
        self.features_flat = self.features.reshape(len(self.active), -1)
        self.dimension = dimension

    def evaluate(self, coefficients, hessian=False, physical=False):
        matrix = (coefficients[self.active] @ self.features_flat).reshape(self.dimension, self.dimension)
        if hessian or physical:
            values, vectors = eigh(matrix, check_finite=False, driver="evr")
        else:
            values, vectors = eigh(matrix, subset_by_index=(0, 0), check_finite=False, driver="evr")
        ground = vectors[:, 0]
        action = self.features @ ground
        gradient = np.zeros(100)
        gradient[self.active] = action @ ground
        result = [values[0], gradient]
        if hessian:
            response = action @ vectors[:, 1:]
            curvature = (response * (2.0 / (values[0] - values[1:]))) @ response.T
            expanded = np.zeros((100, 100))
            expanded[np.ix_(self.active, self.active)] = curvature
            result.append(expanded[:, CONTROL])
        if physical:
            excited = vectors[:, 1]
            gap_gradient = np.zeros(100)
            gap_gradient[self.active] = (self.features @ excited) @ excited - gradient[self.active]
            weight_gradient = np.zeros(100)
            weight_gradient[self.active] = 2 * ground[0] * ((action @ vectors[:, 1:]) @ (vectors[0, 1:] / (values[0] - values[1:])))
            diagonals = np.diag(matrix) - matrix[0, 0]
            smallest = 1 + np.argmin(diagonals[1:])
            margin_gradient = np.zeros(100)
            margin_gradient[self.active] = self.features[:, smallest, smallest] - self.features[:, 0, 0]
            result.append((np.array([ground[0] ** 2, values[1] - values[0], diagonals[smallest]]),
                           np.array([weight_gradient, gap_gradient, margin_gradient])[:, CONTROL]))
        return result


MASKS = [mask for mask in range(128) if mask.bit_count() <= 3]
SPACES = [Space(mask) for mask in MASKS]
FULL = Space(127)
MOBIUS = np.zeros((len(MASKS), len(MASKS)))
for position, mask in enumerate(MASKS):
    for child_position, child in enumerate(MASKS):
        if child & mask == child:
            MOBIUS[position, child_position] = (-1) ** (mask.bit_count() - child.bit_count())
TRIPLES = MOBIUS[[position for position, mask in enumerate(MASKS) if mask.bit_count() == 3]]
TRUNCATION = MOBIUS.sum(axis=0)


def evaluate(controls, hessian=False, coefficients=None):
    center = BASE.copy() if coefficients is None else np.array(coefficients, copy=True)
    center[CONTROL] = controls
    results = [space.evaluate(center, hessian=hessian) for space in SPACES]
    energies = np.array([result[0] for result in results])
    gradients = np.array([result[1] for result in results])
    full_results = FULL.evaluate(center, hessian=hessian, physical=True)
    full_energy, full_gradient, physical = full_results[0], full_results[1], full_results[-1]
    increments = TRIPLES @ energies
    increment_gradient = TRIPLES @ gradients
    tail = full_energy - TRUNCATION @ energies
    tail_sensitivity = full_gradient - TRUNCATION @ gradients
    tail_gradient = tail_sensitivity[CONTROL]
    result = dict(triples=increments, triple_gradient=increment_gradient[:, CONTROL],
                  sensitivity=increment_gradient, tail=tail, tail_gradient=tail_gradient,
                  tail_sensitivity=tail_sensitivity, physical=physical[0], physical_gradient=physical[1])
    if hessian:
        curvatures = np.array([row[2] for row in results])
        result["curvature"] = np.einsum("ab,bcd->acd", TRIPLES, curvatures)
        result["tail_curvature"] = full_results[2] - np.einsum("a,abc->bc", TRUNCATION, curvatures)
    return result


def summary(result):
    parent = float(np.max(np.abs(result["triples"])))
    tail = abs(float(result["tail"]))
    sensitivity = result["sensitivity"]
    uncertainty = 0.001 / np.sqrt(3) * np.linalg.norm(sensitivity, axis=1)
    robust = np.max(np.abs(result["triples"]) + 3.5 * uncertainty)
    return dict(parent_micro=parent * 1e6, tail_micro=tail * 1e6,
                ratio=tail / max(parent, 1e-10), physical=result["physical"].tolist(),
                robust_parent_micro=float(robust * 1e6),
                robust_factor=float(min(1e-6, tail / 100) / max(robust, 1e-12)))


class NominalObjective:
    def __init__(self, target, regularization=0.0):
        self.target = target
        self.regularization = regularization
        self.last_controls = None

    def calculate(self, controls):
        if self.last_controls is not None and np.array_equal(controls, self.last_controls):
            return self.residual, self.jacobian
        self.last_controls = controls.copy()
        result = evaluate(controls)
        violation = np.minimum(result["physical"] - [0.952, 0.405, 0.605], 0)
        physical_scale = np.array([2000, 100, 100])
        self.residual = np.r_[result["triples"] * 1e6,
                              (result["tail"] - self.target) * 1e6,
                              violation * physical_scale,
                              controls * self.regularization]
        self.jacobian = np.vstack([result["triple_gradient"] * 1e6,
                                   result["tail_gradient"] * 1e6,
                                   result["physical_gradient"] * (physical_scale * (violation < 0))[:, None],
                                   np.eye(42) * self.regularization])
        return self.residual, self.jacobian

    def fun(self, controls):
        return self.calculate(controls)[0]

    def jac(self, controls):
        return self.calculate(controls)[1]


def nominal_search(count, iterations, seed=83021, prefix="candidate", scale=0.18, tail=100):
    random = np.random.default_rng(seed)
    best = -np.inf
    started = time.monotonic()
    for run in range(count):
        initial = random.uniform(-1, 1, 42) * np.r_[np.full(21, scale), np.full(21, 0.55)]
        if run == 0:
            initial[:] = 0
        elif run % 3 == 1:
            initial[:21] *= 0.1
            for position, (source, destination) in enumerate(VIRTUAL_EDGES):
                if 3 in (source, destination):
                    initial[position] = random.uniform(-0.4, 0.4)
        target_tail = tail if tail > 0 else random.choice([60, 80, 100, 150, 250, 500, 1000])
        objective = NominalObjective((-1 if run % 4 != 3 else 1) * target_tail * 1e-6)
        fit = least_squares(objective.fun, initial, jac=objective.jac, bounds=(-BOUND, BOUND),
                            max_nfev=iterations, ftol=1e-9, xtol=1e-10, gtol=1e-8)
        result = evaluate(fit.x)
        info = summary(result)
        info.update(run=run, nfev=fit.nfev, cost=float(fit.cost), seconds=time.monotonic() - started)
        save(fit.x, f"{prefix}_{run:03d}.json")
        admissible = np.all(result["physical"] >= [0.95, 0.4, 0.6])
        ranking = info["robust_factor"] if admissible else -1
        if ranking > best:
            best = ranking
            save(fit.x, f"{prefix}_best.json")
        print(json.dumps(info), flush=True)


def check_engine():
    random = np.random.default_rng(410)
    controls = random.uniform(-0.1, 0.1, 42)
    result = evaluate(controls, hessian=True)
    official = model.compute(witness(controls), complete=False)
    expected = np.array([official["increments_eh"][str(mask)] for mask in model.TRIPLE_MASKS])
    assert np.max(np.abs(result["triples"] - expected)) < 1e-12
    assert abs(result["tail"] - official["signed_tail_eh"]) < 1e-12
    direction = random.normal(size=42)
    shift = 1e-5
    upper = evaluate(controls + shift * direction)
    lower = evaluate(controls - shift * direction)
    print("gradient_error", np.max(np.abs((upper["triples"] - lower["triples"]) / (2 * shift) - result["triple_gradient"] @ direction)), flush=True)
    print("hessian_error", np.max(np.abs((upper["sensitivity"] - lower["sensitivity"]) / (2 * shift) - result["curvature"] @ direction)), flush=True)
    print("physical_gradient_error", np.max(np.abs((upper["physical"] - lower["physical"]) / (2 * shift) - result["physical_gradient"] @ direction)), flush=True)
    print("baseline", summary(evaluate(np.zeros(42))), flush=True)
    started = time.monotonic()
    for repeat in range(30):
        evaluate(controls, hessian=True)
    print("hessian_seconds", (time.monotonic() - started) / 30, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--iterations", type=int, default=180)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--seed", type=int, default=83021)
    parser.add_argument("--prefix", default="candidate")
    parser.add_argument("--scale", type=float, default=0.18)
    parser.add_argument("--tail", type=float, default=100)
    arguments = parser.parse_args()
    if arguments.check:
        check_engine()
    nominal_search(arguments.count, arguments.iterations, arguments.seed, arguments.prefix, arguments.scale, arguments.tail)
