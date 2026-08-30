import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from search_model import Model, structured, axes, bounds

parser = argparse.ArgumentParser()
parser.add_argument('--seed', default='seeds.json')
parser.add_argument('--full', action='store_true')
parser.add_argument('--starts', type=int, default=20)
parser.add_argument('--iterations', type=int, default=600)
parser.add_argument('--prefix', default='quiet')
parser.add_argument('--population', type=float, default=.023)
parser.add_argument('--error', type=float, default=.00008)
parser.add_argument('--robust', type=float, default=.001)
parser.add_argument('--objective', default='dad')
parser.add_argument('--dad', type=float, default=.0007)
parser.add_argument('--continue-search', action='store_true')
parser.add_argument('--eommax', type=float, default=100)
parser.add_argument('--jacmax', type=float, default=100)
parser.add_argument('--noise', type=float, default=0)
arguments = parser.parse_args()
selection = np.arange(120) if arguments.full else np.array(structured)
seed_data = json.loads(Path(arguments.seed).read_text())
filenames = [entry[1] for entry in seed_data] if isinstance(seed_data, list) else [arguments.seed]
started = time.monotonic()
best = np.inf


def constraint_values(diagnostic):
    minimum, maximum, error, gradient, infidelity, reference, gap, real_hf, imag_hf, condition, multiplier, amplitude, dad, norm, eom, singular = diagnostic
    return np.array([
        (arguments.error - error - arguments.robust * gradient) / .001,
        (arguments.error + error - arguments.robust * gradient) / .001,
        (.0009 - infidelity) / .01,
        reference - .455,
        gap - .105,
        real_hf - .055,
        imag_hf - .055,
        (95 - condition) / 100,
        1.45 - multiplier,
        1.23 - amplitude,
        (-arguments.population - minimum) * 10,
        (6.99 - norm) / 7,
        eom - .055,
        singular - .021,
        (arguments.dad - dad) / .01 if arguments.objective == 'gradient' else 10,
        arguments.eommax - eom,
        (arguments.jacmax - condition * singular) / 5,
    ])


constraint_matrix = np.zeros((17, 16))
constraint_matrix[0, 2] = -1000
constraint_matrix[0, 3] = -arguments.robust * 1000
constraint_matrix[1, 2] = 1000
constraint_matrix[1, 3] = -arguments.robust * 1000
for row, index, scale in [(2, 4, -100), (3, 5, 1), (4, 6, 1), (5, 7, 1), (6, 8, 1), (7, 9, -.01), (8, 10, -1), (9, 11, -1), (10, 0, -10), (11, 13, -1/7), (12, 14, 1), (13, 15, 1)]:
    constraint_matrix[row, index] = scale
if arguments.objective == 'gradient':
    constraint_matrix[14, 12] = -100
constraint_matrix[15, 14] = -1
objective_index = 3 if arguments.objective == 'gradient' else 12


for start, filename in enumerate(filenames[:arguments.starts]):
    model = Model(selection)
    data = json.loads(Path(filename).read_text())
    initial = np.einsum('kij,ij->k', axes, np.array(data['pair_matrix']))[selection]
    initial += np.random.default_rng(587+start).normal(size=len(initial))*arguments.noise
    model.last_t = np.array(data['amplitudes'])
    iteration = [0]

    def objective(values):
        diagnostic, derivative = model.evaluate(values)
        return diagnostic[objective_index], derivative[objective_index]

    def constraints(values):
        return constraint_values(model.evaluate(values)[0])

    def jacobian(values):
        diagnostic, derivative = model.evaluate(values)
        matrix = constraint_matrix.copy()
        matrix[16, 9] = -diagnostic[15] / 5
        matrix[16, 15] = -diagnostic[9] / 5
        return matrix @ derivative

    def callback(values):
        global best
        iteration[0] += 1
        diagnostic, derivative = model.evaluate(values)
        margin = np.min(constraint_values(diagnostic))
        if margin > -1e-7 and diagnostic[objective_index] < best:
            best = diagnostic[objective_index]
            model.save(values, f'{arguments.prefix}_best.json')
            print('BEST', start, iteration[0], 'dad', best, 'metrics', diagnostic.tolist(), flush=True)
        if iteration[0] % 25 == 0:
            model.save(values, f'{arguments.prefix}_current.json')
            print('progress', start, iteration[0], 'minimum', diagnostic[0], 'margin', margin, 'error', diagnostic[2], 'grad', diagnostic[3], 'dad', diagnostic[12], 'seconds', time.monotonic()-started, flush=True)

    print('START', start, filename, flush=True)
    result = minimize(objective, initial, method='SLSQP', jac=True, bounds=bounds(selection), constraints={'type':'ineq','fun':constraints,'jac':jacobian}, callback=callback, options={'maxiter':arguments.iterations, 'ftol':1e-11, 'disp':False})
    callback(result.x)
    model.save(result.x, f'{arguments.prefix}_{start}.json')
    print('END', start, result.message, 'metrics', model.evaluate(result.x)[0].tolist(), 'margin', min(constraints(result.x)), 'calls', model.calls, 'bad_roots', model.bad_roots, flush=True)
    if not arguments.continue_search and best < (.1 if arguments.objective == 'gradient' else .0002):
        break
