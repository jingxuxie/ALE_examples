import argparse
import json
import time

import numpy as np
from scipy.linalg import solve_banded
from scipy.ndimage import label

from broad import broaden
from invert import Model, OUT, ROOT, load_problem, hamiltonian, response, discrepancies, validate_design


class BandedModel(Model):
    def __init__(self, stride=4, conditions=None):
        super().__init__(stride, conditions)
        self.entries = []
        for condition in self.conditions:
            matrix = hamiltonian(self.config, np.zeros(144), self.config['conditions'][condition])
            rows, columns = np.nonzero(matrix)
            data = -matrix[rows, columns]
            paired = (rows >= self.sites) != (columns >= self.sites)
            diagonal = rows == columns
            diagonal_sites = rows[diagonal] % self.sites
            sign = np.where(rows[diagonal] < self.sites, -1, 1)
            permuted_rows = 2 * (rows % self.sites) + (rows >= self.sites)
            permuted_columns = 2 * (columns % self.sites) + (columns >= self.sites)
            bandwidth = int(np.max(abs(permuted_rows - permuted_columns)))
            self.entries.append((rows, columns, data, paired, diagonal, diagonal_sites, sign, permuted_rows, permuted_columns, bandwidth))
        self.rhs = np.zeros((2 * self.sites, 8), dtype=complex)
        self.rhs[2 * self.probes, np.arange(8)] = 1

    def observe(self, pattern):
        normal = np.zeros(self.sites)
        normal[self.candidates] = pattern
        amplitude = 1 - normal
        outputs = []
        for rows, columns, original, paired, diagonal, diagonal_sites, sign, permuted_rows, permuted_columns, bandwidth in self.entries:
            data = original.copy()
            data[paired] *= amplitude[rows[paired] % self.sites] * amplitude[columns[paired] % self.sites]
            data[diagonal] += sign * self.config['pin_potential'] * normal[diagonal_sites]
            template = np.zeros((2 * bandwidth + 1, 2 * self.sites), dtype=complex)
            template[bandwidth + permuted_rows - permuted_columns, permuted_columns] = data
            values = []
            for energy in self.energies:
                band = template.copy()
                band[bandwidth] += energy + 1j * self.config['broadening']
                result = solve_banded((bandwidth, bandwidth), band, self.rhs.copy(), overwrite_ab=True, overwrite_b=True, check_finite=False)
                values.append(-result[2 * self.probes, np.arange(8)].imag / np.pi)
            outputs.append(np.asarray(values).T)
        return np.asarray(outputs)

    def cost(self, pattern):
        return float(np.mean(((self.observe(pattern) - self.target) / self.scales) ** 2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=50)
    parser.add_argument('--population', type=int, default=96)
    parser.add_argument('--generations', type=int, default=45)
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args()
    rng = np.random.default_rng(arguments.seed)
    model = BandedModel(stride=6, conditions=[0])
    if arguments.check:
        pattern = np.asarray(json.loads((OUT / 'swaps_12_best.json').read_text())['pattern'])
        started = time.time()
        observed = model.observe(pattern)
        print('TIME', time.time() - started, 'ERROR', np.max(abs(observed - response(model.config, pattern)[model.conditions][:, :, model.selection])), flush=True)
        return
    def feasible(pattern):
        material = np.ones(256, dtype=int)
        material[model.candidates] = 1 - pattern
        return label(material.reshape(16, 16))[1] == 1
    def mutate(pattern, count):
        child = pattern.copy()
        child[rng.choice(np.flatnonzero(child), count, replace=False)] = 0
        child[rng.choice(np.flatnonzero(1 - pattern), count, replace=False)] = 1
        return child
    population = []
    for path in list(OUT.glob('*best.json')) + list(OUT.glob('binary_*.json')):
        pattern = np.asarray(json.loads(path.read_text())['pattern'])
        if feasible(pattern) and not any(np.array_equal(pattern, existing) for existing in population):
            population.append(pattern)
    while len(population) < arguments.population:
        if population and rng.random() < .7:
            pattern = mutate(population[rng.integers(len(population))], int(rng.integers(2, 15)))
        else:
            pattern = np.zeros(144, int)
            pattern[rng.choice(144, 54, replace=False)] = 1
        if feasible(pattern):
            population.append(pattern)
    population = np.asarray(population[:arguments.population])
    started = time.time()
    for stage, eta in enumerate([.08, .04, .02, .01]):
        model = BandedModel(stride=6 if eta > .02 else 3, conditions=[0] if eta > .02 else [0, 1, 2])
        if eta != .01:
            broaden(model, eta)
        costs = np.asarray([model.cost(pattern) for pattern in population])
        best = np.inf
        seen = set()
        for generation in range(arguments.generations):
            for iteration in range(arguments.population):
                for retry in range(100):
                    contestants = rng.choice(len(population), 3, replace=False)
                    first = population[contestants[np.argmin(costs[contestants])]]
                    contestants = rng.choice(len(population), 3, replace=False)
                    second = population[contestants[np.argmin(costs[contestants])]]
                    child = first.copy()
                    if rng.random() < .7:
                        lower = rng.integers(0, 10, 2)
                        upper = np.minimum(12, lower + rng.integers(2, 9, 2))
                        mask = np.zeros((12, 12), bool)
                        mask[lower[0]:upper[0], lower[1]:upper[1]] = True
                        child[mask.ravel()] = second[mask.ravel()]
                        difference = int(child.sum() - 54)
                        if difference > 0:
                            selected = np.flatnonzero((child == 1) & (first == 0))
                            child[rng.choice(selected, difference, replace=False)] = 0
                        elif difference < 0:
                            selected = np.flatnonzero((child == 0) & (first == 1))
                            child[rng.choice(selected, -difference, replace=False)] = 1
                    count = min(8, int(rng.geometric(.55 if stage > 1 else .35)))
                    child = mutate(child, count)
                    key = np.packbits(child).tobytes()
                    if key not in seen and feasible(child):
                        seen.add(key)
                        break
                value = model.cost(child)
                contestants = rng.choice(len(population), min(24, len(population)), replace=False)
                closest = contestants[np.argmin(np.sum(population[contestants] != child, axis=1))]
                if value < costs[closest]:
                    population[closest] = child
                    costs[closest] = value
            index = np.argmin(costs)
            if costs[index] < best:
                best = costs[index]
                pattern = population[index]
                np.save(OUT / f'genetic_{arguments.seed}_{stage}.npy', pattern)
                (OUT / f'genetic_{arguments.seed}_{stage}.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
                print('BEST', stage, generation, np.sqrt(best), 'time', round(time.time() - started, 1), flush=True)
                if stage == 3 and best < .06 ** 2:
                    config, target = load_problem(ROOT / 'input')
                    metrics = discrepancies(config, response(config, pattern), target)
                    print('FULL', metrics, flush=True)
                    if metrics['core_score'] >= .96 and metrics['worst_family_score'] >= .94:
                        validate_design(config, pattern)
                        (OUT / 'design.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
                        (OUT / 'match.json').write_text(json.dumps(metrics) + '\n')
                        return
            if generation % 5 == 0:
                print('GEN', stage, generation, np.sqrt(best), 'median', np.sqrt(np.median(costs)), 'time', round(time.time() - started, 1), flush=True)


if __name__ == '__main__':
    main()
