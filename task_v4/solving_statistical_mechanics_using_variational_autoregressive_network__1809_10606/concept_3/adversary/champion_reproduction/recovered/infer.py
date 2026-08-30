import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import minimize


ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/solving_statistical_mechanics_using_variational_autoregressive_network__1809_10606/concept_3/participant')
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ASSETS))
from transfer import model_from_edges, spin_states

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)


class Likelihood:
    def __init__(self, configurations, betas, spec):
        self.spec = spec
        self.betas = np.asarray(betas)
        self.count = configurations.shape[1]
        self.edges = np.asarray(spec['edges'])
        self.edge_count = len(self.edges)
        self.signs = torch.tensor(spec['edge_signs'], dtype=torch.float64)
        self.states = torch.tensor(spin_states(8), dtype=torch.float64)
        self.vertical_products = self.states[:, :-1] * self.states[:, 1:]
        hidden = set(spec['hidden_indices'])
        visible = spec['visible_indices']
        lookup = {spin: index for index, spin in enumerate(visible)}
        statistics = np.zeros((len(betas), self.edge_count + 96))
        statistics[:, self.edge_count + np.asarray(visible)] = configurations.mean(axis=1)
        for edge_index, (first, second) in enumerate(self.edges):
            if first not in hidden and second not in hidden:
                statistics[:, edge_index] = (configurations[:, :, lookup[first]] * configurations[:, :, lookup[second]]).mean(axis=1) * spec['edge_signs'][edge_index]
        self.statistics = torch.tensor(statistics)
        neighbors = {spin: [] for spin in hidden}
        for first, second in self.edges:
            if first in hidden and second in hidden:
                neighbors[first].append(second)
                neighbors[second].append(first)
        remaining = set(hidden)
        components = []
        while remaining:
            pending = [remaining.pop()]
            component = []
            while pending:
                spin = pending.pop()
                component.append(spin)
                for neighbor in neighbors[spin]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        pending.append(neighbor)
            components.append(sorted(component))
        self.components = []
        for component in components:
            component_set = set(component)
            boundary = sorted({spin for first, second in self.edges if first in component_set or second in component_set for spin in (first, second) if spin not in hidden})
            hidden_lookup = {spin: index for index, spin in enumerate(component)}
            boundary_lookup = {spin: index for index, spin in enumerate(boundary)}
            hidden_states = spin_states(len(component)).astype(np.float64)
            boundary_states = spin_states(len(boundary)).astype(np.float64)
            codes = ((configurations[:, :, [lookup[spin] for spin in boundary]] + 1) // 2) @ (1 << np.arange(len(boundary)))
            counts = np.asarray([np.bincount(condition_codes, minlength=len(boundary_states)) for condition_codes in codes])
            used = np.any(counts > 0, axis=0)
            boundary_states = boundary_states[used]
            weights = counts[:, used] / self.count
            cross_indices = []
            cross_boundary = []
            cross_hidden = []
            internal_indices = []
            internal_features = []
            for edge_index, (first, second) in enumerate(self.edges):
                if first in component_set and second in component_set:
                    internal_indices.append(edge_index)
                    internal_features.append(hidden_states[:, hidden_lookup[first]] * hidden_states[:, hidden_lookup[second]])
                elif first in component_set and second not in hidden:
                    cross_indices.append(edge_index)
                    cross_boundary.append(boundary_states[:, boundary_lookup[second]])
                    cross_hidden.append(hidden_states[:, hidden_lookup[first]])
                elif second in component_set and first not in hidden:
                    cross_indices.append(edge_index)
                    cross_boundary.append(boundary_states[:, boundary_lookup[first]])
                    cross_hidden.append(hidden_states[:, hidden_lookup[second]])
            self.components.append({
                'sites': torch.tensor(component),
                'hidden': torch.tensor(hidden_states),
                'weights': torch.tensor(weights),
                'cross_indices': torch.tensor(cross_indices, dtype=torch.long),
                'cross_boundary': torch.tensor(np.asarray(cross_boundary).T.copy()),
                'cross_hidden': torch.tensor(np.asarray(cross_hidden).copy()),
                'internal_indices': torch.tensor(internal_indices, dtype=torch.long),
                'internal_features': torch.tensor(np.asarray(internal_features).T.copy() if internal_features else np.zeros((len(hidden_states), 0))),
            })
        self.calls = 0
        self.started = time.monotonic()
        self.best = np.inf

    def partition(self, theta, beta):
        couplings = theta[:self.edge_count] * self.signs
        vertical = couplings[:84].reshape(12, 7)
        horizontal = couplings[84:].reshape(11, 8)
        fields = theta[self.edge_count:].reshape(12, 8)
        unary_energy = beta * (vertical @ self.vertical_products.T + fields @ self.states.T)
        unary = torch.exp(unary_energy)
        weights = unary[0]
        normalization = weights.sum()
        log_partition = torch.log(normalization)
        forward = weights / normalization
        for column in range(1, 12):
            propagated = forward
            for row in range(8):
                blocks = propagated.reshape(-1, 2, 1 << row)
                same = torch.exp(beta * horizontal[column - 1, row])
                different = 1.0 / same
                propagated = torch.stack((same * blocks[:, 0] + different * blocks[:, 1], different * blocks[:, 0] + same * blocks[:, 1]), dim=1).reshape(256)
            weights = unary[column] * propagated
            normalization = weights.sum()
            log_partition = log_partition + torch.log(normalization)
            forward = weights / normalization
        return log_partition

    def loss(self, theta):
        couplings = theta[:self.edge_count] * self.signs
        fields = theta[self.edge_count:]
        hidden_energies = []
        for component in self.components:
            energy = component['hidden'] @ fields[component['sites']]
            energy = energy + component['internal_features'] @ couplings[component['internal_indices']]
            energy = energy[None, :] + (component['cross_boundary'] * couplings[component['cross_indices']]) @ component['cross_hidden']
            hidden_energies.append(energy)
        total = theta.sum() * 0
        for condition, beta in enumerate(self.betas):
            numerator = beta * (self.statistics[condition] @ theta)
            for component, energy in zip(self.components, hidden_energies):
                numerator = numerator + component['weights'][condition] @ torch.logsumexp(beta * energy, dim=1)
            total = total + self.partition(theta, beta) - numerator
        return total / len(self.betas)

    def evaluate(self, values):
        theta = torch.tensor(values, requires_grad=True)
        loss = self.loss(theta)
        loss.backward()
        value = float(loss.detach())
        gradient = theta.grad.detach().numpy().copy()
        self.calls += 1
        if value < self.best:
            self.best = value
            np.savez(OUTPUT / 'fit_checkpoint.npz', theta=values, loss=value, calls=self.calls)
        if self.calls % 25 == 0:
            print(f'call={self.calls} loss={value:.10f} grad={np.linalg.norm(gradient):.6g} seconds={time.monotonic()-self.started:.1f}', flush=True)
        return value, gradient


def load_data():
    spec = json.loads((ASSETS / 'input/model.json').read_text())
    with np.load(ASSETS / 'input/train.npz') as archive:
        configurations = archive['visible_spins'].copy()
        betas = archive['betas'].copy()
    return configurations, betas, spec


def prediction(values, spec, queries=None):
    if queries is None:
        queries = json.loads((ASSETS / 'input/queries.json').read_text())
    model = model_from_edges(spec, values[:172] * np.asarray(spec['edge_signs']), values[172:])
    results = []
    for query in queries:
        delta = np.zeros(96)
        delta[query['field_indices']] = query['field_values']
        results.append(model.joint(query['beta'], query['readout'], delta.reshape(12, 8)))
    return np.asarray(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--maxiter', type=int, default=1500)
    parser.add_argument('--init', type=Path)
    parser.add_argument('--train-count', type=int, default=8192)
    parser.add_argument('--name', default='fit')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    configurations, betas, spec = load_data()
    likelihood = Likelihood(configurations[:, :args.train_count], betas, spec)
    initial = np.concatenate((np.full(172, 0.625), np.zeros(96)))
    if args.init:
        initial = np.load(args.init)['theta']
    if args.check:
        rng = np.random.default_rng(72631)
        initial = np.concatenate((rng.uniform(0.3, 0.95, 172), rng.uniform(-0.12, 0.12, 96)))
        theta = torch.tensor(initial, requires_grad=True)
        model = model_from_edges(spec, initial[:172] * np.asarray(spec['edge_signs']), initial[172:])
        for beta in betas:
            actual = float(likelihood.partition(theta, beta).detach())
            expected = model.log_partition(beta)
            print('partition check', beta, actual, expected, actual - expected, flush=True)
            assert abs(actual - expected) < 1e-10
        value, gradient = likelihood.evaluate(initial)
        for index in rng.choice(len(initial), 10, replace=False):
            upper = initial.copy()
            lower = initial.copy()
            upper[index] += 1e-5
            lower[index] -= 1e-5
            finite_difference = (float(likelihood.loss(torch.tensor(upper))) - float(likelihood.loss(torch.tensor(lower)))) / 2e-5
            print('gradient check', index, gradient[index], finite_difference, flush=True)
            assert abs(gradient[index] - finite_difference) < 2e-8
        single = Likelihood(configurations[:, :1], betas, spec)
        actual = float(single.loss(theta).detach())
        expected = 0.0
        for condition, beta in enumerate(betas):
            evidence = np.zeros(96)
            evidence[spec['visible_indices']] = configurations[condition, 0]
            expected += model.log_partition(beta) - model.log_partition(beta, evidence=evidence.reshape(12, 8))
        expected /= len(betas)
        print('evidence likelihood check', actual, expected, actual - expected, flush=True)
        assert abs(actual - expected) < 1e-10
        return
    bounds = [(0.3, 0.95)] * 172 + [(-0.12, 0.12)] * 96
    result = minimize(likelihood.evaluate, initial, jac=True, bounds=bounds, method='L-BFGS-B', options={'maxiter': args.maxiter, 'ftol': 1e-12, 'gtol': 2e-7, 'maxcor': 30, 'maxls': 30})
    print(result.message, result.fun, result.nit, result.nfev, flush=True)
    np.savez(OUTPUT / f'{args.name}.npz', theta=result.x, loss=result.fun, gradient=result.jac)
    queries = json.loads((ASSETS / 'input/queries.json').read_text())
    probabilities = prediction(result.x, spec, queries)
    np.savez(OUTPUT / 'predictions.npz', probabilities=np.ascontiguousarray(probabilities, dtype='<f8'), query_ids=np.asarray([query['id'] for query in queries], dtype='<U24'))


if __name__ == '__main__':
    main()
