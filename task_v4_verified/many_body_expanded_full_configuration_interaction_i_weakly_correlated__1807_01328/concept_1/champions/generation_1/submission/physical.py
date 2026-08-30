import itertools
import time

import numpy as np
from scipy.optimize import least_squares

from experiment import MASKS, ORDERS, SUBSETS, transform


SITE_PAIRS = np.array(list(itertools.combinations(range(11), 2)))
PAIR_INDEX = np.zeros((11, 11), dtype=int)
PAIR_INDEX[SITE_PAIRS[:, 0], SITE_PAIRS[:, 1]] = np.arange(55)
PAIR_INDEX += PAIR_INDEX.T


class Group:
    def __init__(self, masks, orbitals, singles=False):
        self.masks = masks
        self.sites = np.array([[0, 1, 2] + [orbital + 3 for orbital in range(8) if mask & (1 << orbital)] for mask in masks])
        count = self.sites.shape[1]
        configurations = list(itertools.combinations(range(count), 3))
        if singles:
            configurations = [configuration for configuration in configurations if sum(site >= 3 for site in configuration) == 1]
        positions = {configuration: index for index, configuration in enumerate(configurations)}
        occupations = np.zeros((len(configurations), count))
        for index, configuration in enumerate(configurations):
            occupations[index, list(configuration)] = 1
        local_pairs = np.array(list(itertools.combinations(range(count), 2)))
        pair_lookup = {tuple(pair): index for index, pair in enumerate(local_pairs)}
        rows, columns, pairs = [], [], []
        for index, configuration in enumerate(configurations):
            for source in configuration:
                for target in range(count):
                    if target not in configuration:
                        child = tuple(sorted(set(configuration) - {source} | {target}))
                        if child in positions and positions[child] > index:
                            rows.append(index)
                            columns.append(positions[child])
                            pairs.append(pair_lookup[tuple(sorted((source, target)))])
        self.rows, self.columns, self.pairs = np.array(rows), np.array(columns), np.array(pairs)
        self.pair_map = np.eye(len(local_pairs))[self.pairs]
        self.global_pairs = PAIR_INDEX[self.sites[:, local_pairs[:, 0]], self.sites[:, local_pairs[:, 1]]]
        self.density_map = occupations[:, local_pairs[:, 0]] * occupations[:, local_pairs[:, 1]]
        self.reference_density = ((local_pairs[:, 0] < 3) & (local_pairs[:, 1] < 3)).astype(float)
        self.base = orbitals[self.sites] @ occupations.T - np.sum(orbitals[:3])
        self.diagonal_indices = np.arange(len(configurations))

    def evaluate(self, parameters, gradient=True, reference=None, follow_reference=False):
        hopping = parameters[:55][self.global_pairs]
        density = parameters[55:][self.global_pairs]
        diagonal = self.base + density @ self.density_map.T - (density @ self.reference_density)[:, None]
        matrix = np.zeros((len(self.masks), self.base.shape[1], self.base.shape[1]))
        matrix[:, self.diagonal_indices, self.diagonal_indices] = diagonal
        matrix[:, self.rows, self.columns] = hopping[:, self.pairs]
        matrix[:, self.columns, self.rows] = hopping[:, self.pairs]
        if reference is None:
            eigenvalues, eigenvectors = np.linalg.eigh(matrix)
            energy = eigenvalues[:, 0]
            vectors = eigenvectors[:, :, 0]
            if follow_reference:
                selected = np.argmax(eigenvectors[:, 0, :] ** 2, axis=1)
                energy = eigenvalues[np.arange(len(matrix)), selected]
                vectors = eigenvectors[np.arange(len(matrix)), :, selected]
        else:
            excited = matrix[:, 1:, 1:] - reference[:, None, None] * np.eye(matrix.shape[1] - 1)
            response = np.linalg.solve(excited, matrix[:, 1:, 0])
            energy = -np.sum(matrix[:, 0, 1:] * response, axis=1)
            vectors = np.concatenate((np.ones((len(matrix), 1)), -response), axis=1)
        if not gradient:
            return energy
        local_hopping = 2 * (vectors[:, self.rows] * vectors[:, self.columns]) @ self.pair_map
        local_density = (vectors ** 2) @ self.density_map - self.reference_density[None, :] * np.sum(vectors ** 2, axis=1)[:, None]
        jacobian = np.zeros((len(self.masks), 110))
        jacobian[np.arange(len(self.masks))[:, None], self.global_pairs] = local_hopping
        jacobian[np.arange(len(self.masks))[:, None], self.global_pairs + 55] = local_density
        return energy, jacobian


class Physical:
    def __init__(self, energy, orbitals, observed=None, density_scale=0.07):
        self.observed = np.flatnonzero((ORDERS >= 1) & (ORDERS <= 3)) if observed is None else np.array(observed)
        self.groups = [(np.flatnonzero(ORDERS[self.observed] == order), Group(self.observed[ORDERS[self.observed] == order], orbitals)) for order in sorted(set(ORDERS[self.observed]))]
        self.orbitals = orbitals
        self.mobius = np.eye(len(self.observed))
        for row, mask in enumerate(self.observed):
            if ORDERS[mask] <= 3:
                self.mobius[row] = SUBSETS[mask, self.observed] * (-1.) ** (ORDERS[mask] - ORDERS[self.observed])
            else:
                for column, subset in enumerate(self.observed):
                    if ORDERS[subset] <= 3 and SUBSETS[mask, subset]:
                        self.mobius[row, column] = -sum((-1.) ** (ORDERS[child] - ORDERS[subset]) for child in self.observed if ORDERS[child] <= 3 and SUBSETS[mask, child] and SUBSETS[child, subset])
        self.target = self.mobius @ energy[self.observed]
        self.weights = 1 / np.array([0.02, 0.002, 0.0002, 0.00004, 0.0001, 0.0002])[ORDERS[self.observed] - 1]
        self.prior_scale = np.concatenate((np.full(55, 0.12), np.full(55, density_scale)))
        self.cache_parameters = None
        self.ridge = 0.0005
        self.singles = -energy[MASKS[1]]
        self.low_terms = transform(energy)
        self.guard = Group([255], orbitals, singles=True)
        self.energy = energy

    def evaluate(self, parameters, gradient=False):
        if self.cache_parameters is None or not np.array_equal(self.cache_parameters, parameters):
            values = np.zeros(len(self.observed))
            derivatives = np.zeros((len(self.observed), 110))
            for indices, group in self.groups:
                values[indices], derivatives[indices] = group.evaluate(parameters, reference=self.energy[group.masks])
            residual = (self.mobius @ values - self.target) * self.weights
            jacobian = (self.mobius @ derivatives) * self.weights[:, None]
            guard_energy, guard_jacobian = self.guard.evaluate(parameters)
            guard_residual = np.maximum(0, 0.2 - guard_energy) * 10
            guard_jacobian *= -10 * (guard_energy < 0.2)[:, None]
            self.cache_parameters = parameters.copy()
            self.cache_residual = np.concatenate((residual, parameters * self.ridge / self.prior_scale, guard_residual))
            self.cache_jacobian = np.concatenate((jacobian, np.diag(self.ridge / self.prior_scale), guard_jacobian), axis=0)
        return self.cache_jacobian if gradient else self.cache_residual

    def fit(self, seed=0, iterations=300, initial=None, reduced=False, normalize=False, init_mode='quadratic', scaling='jac'):
        if initial is None:
            generator = np.random.default_rng(seed)
            initial = np.zeros(110)
            hopping = np.zeros((11, 11))
            for orbital in range(8):
                vector = np.ones(3) + generator.normal(0, 0.35, size=3) if seed == 0 else generator.normal(size=3)
                vector *= np.sqrt(self.singles[orbital] / np.sum(vector ** 2 / (self.orbitals[orbital + 3] - self.orbitals[:3])))
                hopping[:3, orbital + 3] = vector
            for left, right in itertools.combinations(range(8), 2):
                if init_mode == 'naive':
                    first = hopping[:3, left + 3] / (self.orbitals[left + 3] - self.orbitals[:3])
                    second = hopping[:3, right + 3] / (self.orbitals[right + 3] - self.orbitals[:3])
                    hopping[left + 3, right + 3] = np.clip(self.low_terms[(1 << left) | (1 << right)] / (2 * np.dot(first, second)), -.4, .4)
                    continue
                first = hopping[:3, left + 3] / np.sqrt(self.orbitals[left + 3] - self.orbitals[:3])
                second = hopping[:3, right + 3] / np.sqrt(self.orbitals[right + 3] - self.orbitals[:3])
                gram = np.dot(first, second)
                pair_value = self.low_terms[(1 << left) | (1 << right)]
                denominator = self.singles[left] + self.singles[right] - pair_value
                radical = np.sqrt(max(gram ** 2 - pair_value * denominator, 0))
                roots = np.array([gram - radical, gram + radical]) / denominator
                if seed:
                    probabilities = np.exp(-roots ** 2 / (2 * .18 ** 2))
                    probabilities /= probabilities.sum()
                    root = generator.choice(roots, p=probabilities)
                else:
                    root = roots[np.argmin(np.abs(roots))]
                hopping[left + 3, right + 3] = np.clip(root * np.sqrt((self.orbitals[left + 3] + .22) * (self.orbitals[right + 3] + .22)), -.7, .7)
            initial[:55] = hopping[SITE_PAIRS[:, 0], SITE_PAIRS[:, 1]]
        if normalize:
            virtual_pairs = PAIR_INDEX[np.arange(3)[:, None], np.arange(3, 11)[None, :]]
            signs = np.sign(initial[virtual_pairs[0]])
            for column, (left, right) in enumerate(SITE_PAIRS):
                if left >= 3:
                    initial[column] *= signs[left - 3] * signs[right - 3]
            initial[virtual_pairs] /= initial[virtual_pairs[0]][None, :]
            active = np.r_[np.arange(55), 55 + np.flatnonzero((SITE_PAIRS[:, 0] < 3) & (SITE_PAIRS[:, 1] >= 3))] if reduced else np.arange(110)
            active = active[~np.isin(active, virtual_pairs[0])]
            single_group = next(group for indices, group in self.groups if ORDERS[group.masks[0]] == 1)
            references = self.energy[single_group.masks]
            cache = {}
            def expand_normalized(parameters):
                raw = np.zeros(110)
                raw[virtual_pairs[0]] = 1
                raw[active] = parameters
                energies = single_group.evaluate(raw, reference=references, gradient=False)
                factors = np.sqrt(np.maximum(references / energies, 1e-10))
                projected = raw.copy()
                projected[virtual_pairs] *= factors[None, :]
                return projected, factors
            def normalized_evaluate(parameters, gradient=False):
                if 'parameters' not in cache or not np.array_equal(cache['parameters'], parameters):
                    projected, factors = expand_normalized(parameters)
                    residual = self.evaluate(projected)
                    jacobian = self.evaluate(projected, True).copy()
                    _, single_jacobian = single_group.evaluate(projected, reference=references)
                    radial = np.stack([jacobian[:, virtual_pairs[:, orbital]] @ projected[virtual_pairs[:, orbital]] for orbital in range(8)], axis=1)
                    jacobian -= (radial / (2 * references)[None, :]) @ single_jacobian
                    jacobian[:, virtual_pairs.reshape(-1)] *= np.tile(factors, 3)[None, :]
                    cache['parameters'] = parameters.copy()
                    cache['residual'] = residual
                    cache['jacobian'] = jacobian[:, active]
                return cache['jacobian'] if gradient else cache['residual']
            result = least_squares(normalized_evaluate, initial[active], jac=lambda parameters: normalized_evaluate(parameters, True), method='lm', max_nfev=iterations, ftol=1e-7, x_scale='jac')
            result.x = expand_normalized(result.x)[0]
            return result
        if reduced:
            active = np.r_[np.arange(55), 55 + np.flatnonzero((SITE_PAIRS[:, 0] < 3) & (SITE_PAIRS[:, 1] >= 3))]
            def expand(parameters):
                expanded = np.zeros(110)
                expanded[active] = parameters
                return expanded
            result = least_squares(lambda parameters: self.evaluate(expand(parameters)), initial[active], jac=lambda parameters: self.evaluate(expand(parameters), True)[:, active], method='lm', max_nfev=iterations, ftol=1e-8, x_scale='jac')
            result.x = expand(result.x)
            return result
        return least_squares(self.evaluate, initial, jac=lambda parameters: self.evaluate(parameters, True), method='lm', max_nfev=iterations, ftol=1e-8, x_scale=scaling)

    def predict(self, parameters, masks):
        result = np.zeros(len(masks))
        for order in sorted(set(ORDERS[masks])):
            selected = np.flatnonzero(ORDERS[masks] == order)
            if order:
                result[selected] = Group(np.asarray(masks)[selected], self.orbitals).evaluate(parameters, False, follow_reference=True)
        return result


def main():
    data = np.load('train.npz')
    energies, orbitals = data['energies'][-1800:], data['orbitals'][-1800:]
    started = time.time()
    for index in [2, 8, 14, 20, 26, 32]:
        problem = Physical(energies[index], orbitals[index])
        for seed in range(3):
            result = problem.fit(seed, iterations=400)
            predicted = problem.predict(result.x, np.arange(256))
            residual = transform(predicted - energies[index])
            print(index, seed, np.linalg.norm(result.fun), np.linalg.norm(result.fun[:92]), residual[ORDERS >= 4].sum() * 1e6, result.nfev, time.time() - started, flush=True)


if __name__ == '__main__':
    main()
