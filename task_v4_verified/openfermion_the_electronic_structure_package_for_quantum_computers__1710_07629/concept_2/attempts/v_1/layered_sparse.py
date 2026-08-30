import argparse
import time
from scipy.optimize import minimize
from optimize import *


def run(instance, seed=0):
    random = np.random.default_rng(seed)
    size = instance['n_modes']
    depth = instance['budgets']['max_depth']
    edges, layers = [], []
    for layer in range(depth):
        block = list(map(tuple, instance['edges']))
        random.shuffle(block)
        edges.extend(block)
        layers.extend([layer] * len(block))
    endpoints = np.array(edges)
    locations_first = np.array(layers) * size + endpoints[:, 0]
    locations_second = np.array(layers) * size + endpoints[:, 1]
    parameters = random.normal(scale=0.035, size=(len(edges), 2))
    solver = Fit(instance, edges)
    started = time.monotonic()
    for stage, (epsilon, strength) in enumerate([(0.25, 0.002), (0.12, 0.001), (0.05, 0.0003), (0.015, 2e-5), (0.003, 2e-7)]):
        def objective(values):
            residual, jacobian = solver.evaluate(values)
            pairs = values.reshape(-1, 2)
            radii_squared = np.sum(pairs ** 2, axis=1)
            activity = radii_squared / (epsilon ** 2 + radii_squared)
            sums = np.zeros(depth * size)
            np.add.at(sums, locations_first, activity)
            np.add.at(sums, locations_second, activity)
            collisions = 0.5 * (np.sum(sums ** 2) - 2 * np.sum(activity ** 2))
            activity_gradient = 1 + 3 * (sums[locations_first] + sums[locations_second] - 2 * activity)
            derivative = 2 * epsilon ** 2 * pairs / (epsilon ** 2 + radii_squared[:, None]) ** 2
            cost = 0.5 * np.sum(residual ** 2) + strength * (np.sum(activity) + 3 * collisions)
            gradient = jacobian.T @ residual + (strength * activity_gradient[:, None] * derivative).ravel()
            return cost, gradient
        result = minimize(objective, parameters.ravel(), method='L-BFGS-B', jac=True,
                          options={'maxiter': 2400 if stage < 2 else 1800, 'ftol': 1e-14, 'gtol': 2e-10, 'maxcor': 30})
        parameters = result.x.reshape(-1, 2)
        radii = np.linalg.norm(parameters, axis=1)
        error = np.linalg.norm(solver.evaluate(parameters.ravel())[0]) * np.sqrt(2)
        print(instance['id'], seed, stage, 'error', error, 'count', [(cut, int(sum(radii > cut))) for cut in (0.1, 0.03, 0.01)],
              'time', round(time.monotonic() - started, 1), flush=True)
        cutoff = epsilon * 0.5
        keep = radii > cutoff
        trial_edges = [edge for edge, kept in zip(edges, keep) if kept]
        trial_parameters = parameters[keep]
        trial_parameters, accurate_error = Fit(instance, trial_edges).solve(trial_parameters, evaluations=200)
        circuit = pack(instance, trial_edges, trial_parameters)
        print('POLISH', instance['id'], seed, stage, len(trial_edges), len(circuit['layers']), accurate_error, flush=True)
        if accurate_error < 1e-8:
            Path(instance['id'] + f'_layered_{seed}_{stage}.json').write_text(json.dumps(circuit))
            if len(trial_edges) <= instance['budgets']['max_gates'] and len(circuit['layers']) <= depth:
                print('SOLVED', instance['id'], flush=True)
                return True
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--trials', type=int, default=3)
    arguments = parser.parse_args()
    for seed in range(arguments.seed, arguments.seed + arguments.trials):
        if run(INSTANCES[arguments.index], seed):
            break
