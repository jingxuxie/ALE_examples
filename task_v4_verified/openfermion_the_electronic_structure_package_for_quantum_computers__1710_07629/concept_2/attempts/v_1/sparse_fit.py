import argparse
import time
from scipy.optimize import minimize
from optimize import *


def run(instance, seed=0, source='local'):
    random = np.random.default_rng(seed)
    if source != 'zero':
        circuit = json.loads(Path(instance['id'] + '_' + source + '.json').read_text())
        edges, parameters = [], []
        for layer in circuit['layers']:
            insertions = list(instance['edges'])
            random.shuffle(insertions)
            for first, second in insertions:
                edges.append((first, second))
                parameters.append((0.0, 0.0))
            for gate in layer:
                edges.append((gate['u'], gate['v']))
                parameters.append((gate['theta'] * np.cos(gate['phi']), gate['theta'] * np.sin(gate['phi'])))
        parameters = np.array(parameters)
    else:
        edges = []
        for sweep in range(8):
            insertions = list(instance['edges'])
            random.shuffle(insertions)
            edges.extend(map(tuple, insertions))
        parameters = random.normal(scale=0.025, size=(len(edges), 2))
    started = time.monotonic()
    fit = Fit(instance, edges)
    for stage, (epsilon, strength) in enumerate([(0.1, 2e-4), (0.06, 1e-4), (0.03, 3e-5), (0.01, 1e-5), (0.004, 1e-6)]):
        def objective(values):
            residual, jacobian = fit.evaluate(values)
            pairs = values.reshape(-1, 2)
            radii_squared = np.sum(pairs ** 2, axis=1)
            cost = 0.5 * np.sum(residual ** 2) + strength * np.sum(np.log1p(radii_squared / epsilon ** 2))
            gradient = jacobian.T @ residual + (2 * strength * pairs / (epsilon ** 2 + radii_squared[:, None])).ravel()
            return cost, gradient
        result = minimize(objective, parameters.ravel(), method='L-BFGS-B', jac=True,
                          options={'maxiter': 1800, 'ftol': 1e-15, 'gtol': 1e-10, 'maxcor': 30})
        parameters = result.x.reshape(-1, 2)
        radii = np.linalg.norm(parameters, axis=1)
        print(instance['id'], source, seed, stage, 'count', len(edges), 'cost', result.fun,
              'error', np.linalg.norm(fit.evaluate(parameters.ravel())[0]) * np.sqrt(2),
              'counts', [(threshold, int(sum(radii > threshold))) for threshold in (0.1, 0.03, 0.01, 0.003)],
              'time', round(time.monotonic() - started, 1), flush=True)
        cutoff = epsilon * 0.5
        keep = radii > cutoff
        trial_edges = [edge for edge, kept in zip(edges, keep) if kept]
        trial_parameters = parameters[keep]
        solver = Fit(instance, trial_edges)
        polished, error = solver.solve(trial_parameters, evaluations=250)
        circuit = pack(instance, trial_edges, polished)
        print('POLISH', len(trial_edges), len(circuit['layers']), error, flush=True)
        if error < 1e-8:
            Path(instance['id'] + f'_sparse_{source}_{seed}_{stage}.json').write_text(json.dumps(circuit))
            if len(trial_edges) <= instance['budgets']['max_gates'] and len(circuit['layers']) <= instance['budgets']['max_depth']:
                print('SOLVED', flush=True)
                return
        if stage >= 1:
            keep = radii > epsilon * 0.1
            edges = [edge for edge, kept in zip(edges, keep) if kept]
            parameters = parameters[keep]
            fit = Fit(instance, edges)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, default=0)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--source', default='local')
    arguments = parser.parse_args()
    run(INSTANCES[arguments.index], arguments.seed, arguments.source)
