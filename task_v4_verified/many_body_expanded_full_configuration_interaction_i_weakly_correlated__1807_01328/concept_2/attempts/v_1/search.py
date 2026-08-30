import os
import sys
import json
import time
import itertools
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
sys.dont_write_bytecode = True
PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_2/participant')
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize, least_squares
import model

EDGES = list(itertools.combinations(range(7), 2))
EDGE_INDEX = {edge: position for position, edge in enumerate(EDGES)}
BOUNDS = np.array([0.45] * 21 + [0.60] * 21)


def witness(parameters):
    blocks = []
    for offset in (0, 21):
        block = np.zeros((7, 7))
        for position, (first, second) in enumerate(EDGES):
            block[first, second] = block[second, first] = float(parameters[offset + position])
        blocks.append(block.tolist())
    return dict(schema_version=1, virtual_hopping=blocks[0], virtual_density=blocks[1])


def parameters_from_witness(data):
    return np.array([data[field][first][second] for field in ('virtual_hopping', 'virtual_density') for first, second in EDGES])


class ExactSearch:
    def __init__(self):
        hopping, density = model.decode_witness(witness(np.zeros(42)))
        self.masks = [mask for mask in range(128) if mask.bit_count() <= 3]
        self.position = {mask: index for index, mask in enumerate(self.masks)}
        self.triples = [mask for mask in self.masks if mask.bit_count() == 3]
        self.transform = np.zeros((len(self.masks), len(self.masks)))
        for row, mask in enumerate(self.masks):
            for column, submask in enumerate(self.masks):
                if submask & mask == submask:
                    self.transform[row, column] = (-1) ** (mask.bit_count() - submask.bit_count())
        self.triple_transform = self.transform[[self.position[mask] for mask in self.triples]]
        self.truncation_weights = self.transform.sum(axis=0)
        self.base_energies = np.zeros(len(self.masks))
        self.groups = []
        for order in range(4):
            masks = [mask for mask in self.masks if mask.bit_count() == order]
            bases, derivatives, indices = [], [], []
            for mask in masks:
                base = model.hamiltonian(mask, hopping, density)
                if order <= 1:
                    self.base_energies[self.position[mask]] = eigh(base, eigvals_only=True, subset_by_index=(0, 0))[0]
                    continue
                occupation, (rows, columns, sources, destinations) = model.topology(mask)
                local_edges = [edge for edge in EDGES if (mask >> edge[0]) & 1 and (mask >> edge[1]) & 1]
                local_indices = [EDGE_INDEX[edge] for edge in local_edges]
                local_indices += [index + 21 for index in local_indices]
                deriv = np.zeros((len(local_indices), len(base), len(base)))
                for local, (first, second) in enumerate(local_edges):
                    selected = ((sources == first + 3) & (destinations == second + 3)) | ((sources == second + 3) & (destinations == first + 3))
                    deriv[local, rows[selected], columns[selected]] = 1.0
                    deriv[local, columns[selected], rows[selected]] = 1.0
                    deriv[local + len(local_edges)] = np.diag(occupation[:, first + 3] * occupation[:, second + 3])
                bases.append(base)
                derivatives.append(deriv)
                indices.append(local_indices)
            if order > 1:
                self.groups.append((np.array([self.position[mask] for mask in masks]), np.array(bases), np.array(derivatives), np.array(indices)))
        self.full_base = model.hamiltonian(127, hopping, density)
        occupation, (rows, columns, sources, destinations) = model.topology(127)
        selected = (sources >= 3) & (destinations >= 3)
        self.rows, self.columns = rows[selected], columns[selected]
        self.hopping_indices = np.array([EDGE_INDEX[tuple(sorted((int(source) - 3, int(destination) - 3)))] for source, destination in zip(sources[selected], destinations[selected])])
        self.density_derivatives = np.array([occupation[:, first + 3] * occupation[:, second + 3] for first, second in EDGES]).T
        self.diagonal_indices = np.diag_indices(120)
        self.last_parameters = None
        self.calls = 0
        self.best_score = -1.0
        self.best_tail = 0.0
        self.started = time.monotonic()

    def gradient(self, first, second=None):
        if second is None:
            second = first
        hopping = np.bincount(self.hopping_indices, weights=first[self.rows] * second[self.columns] + first[self.columns] * second[self.rows], minlength=21)
        density = self.density_derivatives.T @ (first * second)
        return np.concatenate((hopping, density))

    def evaluate(self, parameters):
        if self.last_parameters is not None and np.array_equal(parameters, self.last_parameters):
            return self.result
        energies = self.base_energies.copy()
        energy_jacobian = np.zeros((len(self.masks), 42))
        for positions, bases, derivatives, indices in self.groups:
            matrices = bases + np.einsum('bk,bkij->bij', parameters[indices], derivatives, optimize=True)
            values, vectors = np.linalg.eigh(matrices)
            energies[positions] = values[:, 0]
            ground = vectors[:, :, 0]
            local_jacobian = np.einsum('bi,bkij,bj->bk', ground, derivatives, ground, optimize=True)
            energy_jacobian[positions[:, None], indices] = local_jacobian
        triples = self.triple_transform @ energies
        triple_jacobian = self.triple_transform @ energy_jacobian
        full_matrix = self.full_base.copy()
        full_matrix[self.rows, self.columns] = full_matrix[self.columns, self.rows] = parameters[self.hopping_indices]
        full_matrix[self.diagonal_indices] += self.density_derivatives @ parameters[21:]
        values, vectors = eigh(full_matrix, check_finite=False, driver='evd')
        ground = vectors[:, 0]
        ground_jacobian = self.gradient(ground)
        tail = values[0] - self.truncation_weights @ energies
        tail_jacobian = ground_jacobian - self.truncation_weights @ energy_jacobian
        weight = ground[0] ** 2
        response = vectors[:, 1:] @ (vectors[0, 1:] / (values[0] - values[1:]))
        weight_jacobian = 2.0 * ground[0] * self.gradient(ground, response)
        gap = values[1] - values[0]
        gap_jacobian = self.gradient(vectors[:, 1]) - ground_jacobian
        margins = np.diag(full_matrix)[1:] - full_matrix[0, 0]
        smallest = int(np.argmin(margins))
        margin_jacobian = np.concatenate((np.zeros(21), self.density_derivatives[smallest + 1]))
        self.calls += 1
        self.last_parameters = parameters.copy()
        self.result = (triples, triple_jacobian, tail, tail_jacobian, weight, weight_jacobian, gap, gap_jacobian, margins[smallest], margin_jacobian)
        largest = max(np.max(np.abs(triples)), 1e-10)
        score = min(1.0, 1e-6 / largest, abs(tail) / 5e-5, abs(tail) / largest / 100)
        valid = weight >= 0.95 and gap >= 0.4 and margins[smallest] >= 0.6 and np.all(np.abs(parameters) <= BOUNDS)
        if valid and (score > self.best_score or score >= 1 and abs(tail) > self.best_tail):
            self.best_score = score
            self.best_tail = abs(tail)
            Path('witness.json').write_text(json.dumps(witness(parameters), indent=2) + '\n')
            Path('checkpoint.json').write_text(json.dumps(dict(score=score, tail=tail, largest_triple=largest, weight=weight, gap=gap, margin=float(margins[smallest]), calls=self.calls, seconds=time.monotonic() - self.started), indent=2) + '\n')
        return self.result

    def describe(self, parameters):
        result = self.evaluate(parameters)
        return dict(triple=float(np.max(np.abs(result[0]))), tail=float(result[2]), weight=float(result[4]), gap=float(result[6]), margin=float(result[8]), best=self.best_score, calls=self.calls, seconds=round(time.monotonic() - self.started, 2))


def validate():
    search = ExactSearch()
    generator = np.random.default_rng(72)
    parameters = generator.uniform(-0.2, 0.2, 42)
    result = search.evaluate(parameters)
    metrics = model.compute(witness(parameters), complete=False)
    print('fast', search.describe(parameters), flush=True)
    print('public', {key: metrics[key] for key in ('signed_tail_eh', 'max_abs_triple_eh', 'hf_weight', 'spectral_gap_eh', 'diagonal_margin_eh')}, flush=True)
    direction = generator.normal(size=42)
    direction /= np.linalg.norm(direction)
    plus = search.evaluate(parameters + 1e-5 * direction)
    minus = search.evaluate(parameters - 1e-5 * direction)
    for value_index, jacobian_index in ((0, 1), (2, 3), (4, 5), (6, 7), (8, 9)):
        finite = (plus[value_index] - minus[value_index]) / 2e-5
        exact = result[jacobian_index] @ direction
        print('derivative', value_index, float(np.max(np.abs(finite - exact))), flush=True)
    started = time.monotonic()
    for trial in range(100):
        search.evaluate(parameters + trial * 1e-6)
    print('100 evaluations', time.monotonic() - started, flush=True)


def optimize(start, search, sign, limit=300, tolerance=0.35e-6):
    def objective(parameters):
        result = search.evaluate(parameters)
        return -sign * result[2] / 1e-4, -sign * result[3] / 1e-4

    def constraints(parameters):
        result = search.evaluate(parameters)
        return np.concatenate(((tolerance - result[0]) / 1e-5, (tolerance + result[0]) / 1e-5, [(result[4] - 0.951) / 0.05, result[6] - 0.405, result[8] - 0.605]))

    def constraint_jacobian(parameters):
        result = search.evaluate(parameters)
        return np.vstack((-result[1] / 1e-5, result[1] / 1e-5, result[5] / 0.05, result[7], result[9]))

    iteration = [0]
    def callback(parameters):
        iteration[0] += 1
        if iteration[0] % 50 == 0:
            print('iteration', iteration[0], search.describe(parameters), flush=True)

    return minimize(objective, start, jac=True, method='SLSQP', bounds=list(zip(-BOUNDS, BOUNDS)), constraints=[dict(type='ineq', fun=constraints, jac=constraint_jacobian)], callback=callback, options=dict(maxiter=limit, ftol=1e-11, disp=False))


def run():
    search = ExactSearch()
    generator = np.random.default_rng(20382)
    start = np.zeros(42)
    print('baseline', search.describe(start), flush=True)
    for trial in range(200):
        if trial == 0:
            start = np.zeros(42)
            sign = -1
        elif trial == 1:
            start = np.zeros(42)
            sign = 1
        elif trial % 4 == 0:
            start = parameters_from_witness(json.loads(Path('witness.json').read_text()))
            start += generator.normal(size=42) * np.concatenate((np.full(21, 0.025), np.full(21, 0.08)))
            start = np.clip(start, -BOUNDS, BOUNDS)
            sign = -1 if search.evaluate(start)[2] < 0 else 1
        elif trial % 4 == 1:
            start = generator.uniform(-0.12, 0.12, 42)
            chosen = generator.choice(7, size=4, replace=False)
            for first, second, value in ((0, 1, .3), (2, 3, .3), (0, 2, .3), (1, 3, .3), (0, 3, -.15), (1, 2, -.15)):
                edge = tuple(sorted((chosen[first], chosen[second])))
                start[EDGE_INDEX[edge]] = value
            sign = -1 if generator.random() < .5 else 1
        else:
            start = generator.uniform(-1, 1, 42) * BOUNDS * (0.3 if trial < 10 else 0.8)
            sign = -1 if generator.random() < .5 else 1
        print('start', trial, 'sign', sign, search.describe(start), flush=True)
        result = optimize(start, search, sign)
        print('finished', trial, result.success, result.message, search.describe(result.x), flush=True)
        np.save(f'trial_{trial:03d}.npy', result.x)
        if search.best_score >= 1.0:
            print('PASSING CANDIDATE SAVED', flush=True)
            break


if __name__ == '__main__':
    if '--validate' in sys.argv:
        validate()
    else:
        run()
