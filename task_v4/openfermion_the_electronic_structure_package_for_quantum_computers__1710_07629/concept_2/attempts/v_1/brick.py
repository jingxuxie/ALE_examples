import argparse
import time
from scipy.optimize import minimize
from optimize import *


def coloring(instance, random):
    edges = list(map(tuple, instance['edges']))
    random.shuffle(edges)
    assigned = {}
    occupied = [set() for mode in range(instance['n_modes'])]
    def visit():
        if len(assigned) == len(edges):
            return True
        available = [(len(set(range(3)) - occupied[first] - occupied[second]), index) for index, (first, second) in enumerate(edges) if index not in assigned]
        _, index = min(available)
        first, second = edges[index]
        colors = list(set(range(3)) - occupied[first] - occupied[second])
        random.shuffle(colors)
        for color in colors:
            assigned[index] = color
            occupied[first].add(color)
            occupied[second].add(color)
            if visit():
                return True
            occupied[first].remove(color)
            occupied[second].remove(color)
            del assigned[index]
        return False
    if visit():
        return [[edge for index, edge in enumerate(edges) if assigned[index] == color] for color in range(3)]
    raise RuntimeError('three-coloring unavailable')


def run(instance, seed, bounded=False):
    random = np.random.default_rng(seed)
    colors = coloring(instance, random)
    order = []
    for layer in range(instance['budgets']['max_depth']):
        if seed % 3 == 0:
            order.append(layer % 3)
        elif seed % 3 == 1:
            order.append(int(random.choice([color for color in range(3) if not order or color != order[-1]])))
        else:
            order.append((layer // 2 + (layer % 2) * 2) % 3)
    edges = [edge for color in order for edge in colors[color]]
    parameters = random.normal(scale=0.08, size=(len(edges), 2))
    solver = Fit(instance, edges)
    started = time.monotonic()
    stages = [(0.07, 1e-4), (0.035, 5e-5), (0.015, 1e-5), (0.004, 5e-7)]
    if bounded:
        stages = [(0.3, 0.003), (0.15, 0.001), (0.07, 0.0001), (0.02, 1e-6), (0.004, 1e-8)]
    weights = np.exp(random.normal(scale=0.25, size=len(edges))) if bounded else np.ones(len(edges))
    for stage, (epsilon, strength) in enumerate(stages):
        def objective(values):
            residual, jacobian = solver.evaluate(values)
            pairs = values.reshape(-1, 2)
            radii_squared = np.sum(pairs ** 2, axis=1)
            if bounded:
                cost = 0.5 * np.sum(residual ** 2) + strength * np.sum(weights * radii_squared / (epsilon ** 2 + radii_squared))
                gradient = jacobian.T @ residual + (2 * strength * epsilon ** 2 * weights[:, None] * pairs / (epsilon ** 2 + radii_squared[:, None]) ** 2).ravel()
            else:
                cost = 0.5 * np.sum(residual ** 2) + strength * np.sum(np.log1p(radii_squared / epsilon ** 2))
                gradient = jacobian.T @ residual + (2 * strength * pairs / (epsilon ** 2 + radii_squared[:, None])).ravel()
            return cost, gradient
        result = minimize(objective, parameters.ravel(), method='L-BFGS-B', jac=True,
                          options={'maxiter': 1800, 'ftol': 2e-14, 'gtol': 1e-10, 'maxcor': 25})
        parameters = result.x.reshape(-1, 2)
        radii = np.linalg.norm(parameters, axis=1)
        error = np.linalg.norm(solver.evaluate(parameters.ravel())[0]) * np.sqrt(2)
        print(instance['id'], seed, stage, 'error', error, 'count', int(sum(radii > 0.015)),
              'time', round(time.monotonic() - started, 1), flush=True)
        keep = radii > epsilon * 0.5
        trial_edges = [edge for edge, kept in zip(edges, keep) if kept]
        trial_parameters = parameters[keep]
        polished, accurate_error = Fit(instance, trial_edges).solve(trial_parameters, evaluations=180)
        circuit = pack(instance, trial_edges, polished)
        print('POLISH', instance['id'], seed, stage, len(trial_edges), len(circuit['layers']), accurate_error, flush=True)
        if accurate_error < 1e-8:
            Path(instance['id'] + f'_brick_{seed}_{stage}.json').write_text(json.dumps(circuit))
            if len(trial_edges) <= instance['budgets']['max_gates']:
                print('SOLVED', instance['id'], flush=True)
                return True
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--trials', type=int, default=10)
    parser.add_argument('--bounded', action='store_true')
    arguments = parser.parse_args()
    for seed in range(arguments.seed, arguments.seed + arguments.trials):
        if run(INSTANCES[arguments.index], seed, arguments.bounded):
            break
