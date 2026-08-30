import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from search_model import JointModel, structured, axes, bounds

parser = argparse.ArgumentParser()
parser.add_argument('--seed', default='seeds.json')
parser.add_argument('--full', action='store_true')
parser.add_argument('--starts', type=int, default=20)
parser.add_argument('--iterations', type=int, default=1000)
parser.add_argument('--prefix', default='joint')
parser.add_argument('--population', type=float, default=.021)
parser.add_argument('--dad', type=float, default=.0004)
parser.add_argument('--error', type=float, default=.000094)
parser.add_argument('--robust', type=float, default=.001)
parser.add_argument('--mode', default='dad')
arguments = parser.parse_args()
selection = np.arange(120) if arguments.full else np.array(structured)
seed_data = json.loads(Path(arguments.seed).read_text())
filenames = [entry[1] for entry in seed_data] if isinstance(seed_data, list) else [arguments.seed]
started = time.monotonic()
best = np.inf
model = JointModel(selection)


def constraint_values(diagnostic):
    minimum, maximum, error, gradient, infidelity, reference, gap, real_hf, imag_hf, condition, multiplier, amplitude, dad, norm, eom, singular = diagnostic[:16]
    return np.array([
        (arguments.error - error - arguments.robust * gradient) / .001,
        (arguments.error + error - arguments.robust * gradient) / .001,
        (.00095 - infidelity) / .01,
        reference - .455,
        gap - .105,
        real_hf - .055,
        imag_hf - .055,
        (95 - condition) / 100,
        1.45 - multiplier,
        1.23 - amplitude,
        (-arguments.population - minimum) * 10 if arguments.mode == 'dad' else (arguments.dad - dad) / .01,
        (6.99 - norm) / 7,
        eom - .055,
        singular - .021,
    ])


constraint_matrix = np.zeros((14, 16 + len(model.active)))
constraint_matrix[0, 2] = -1000
constraint_matrix[0, 3] = -arguments.robust * 1000
constraint_matrix[1, 2] = 1000
constraint_matrix[1, 3] = -arguments.robust * 1000
for row, index, scale in [(2, 4, -100), (3, 5, 1), (4, 6, 1), (5, 7, 1), (6, 8, 1), (7, 9, -.01), (8, 10, -1), (9, 11, -1), (11, 13, -1/7), (12, 14, 1), (13, 15, 1)]:
    constraint_matrix[row, index] = scale
constraint_matrix[10, 0 if arguments.mode == 'dad' else 12] = -10 if arguments.mode == 'dad' else -100
objective_index = 12 if arguments.mode == 'dad' else 0


for start, filename in enumerate(filenames[:arguments.starts]):
    data = json.loads(Path(filename).read_text())
    coefficients = np.einsum('kij,ij->k', axes, np.array(data['pair_matrix']))[selection]
    initial = np.concatenate((coefficients, np.array(data['amplitudes'])[model.active]))
    iteration = [0]

    def objective(values):
        diagnostic, derivative = model.evaluate(values)
        return 10 * diagnostic[objective_index], 10 * derivative[objective_index]

    def constraints(values):
        return constraint_values(model.evaluate(values)[0])

    def jacobian(values):
        return constraint_matrix @ model.evaluate(values)[1]

    def callback(values):
        global best
        iteration[0] += 1
        diagnostic, derivative = model.evaluate(values)
        margin = min(np.min(constraint_values(diagnostic)), -np.max(abs(diagnostic[16:])))
        if margin > -1e-7 and diagnostic[objective_index] < best:
            best = diagnostic[objective_index]
            model.save(values, f'{arguments.prefix}_best.json')
            print('BEST', start, iteration[0], 'objective', best, 'metrics', diagnostic[:16].tolist(), flush=True)
        if iteration[0] % 50 == 0:
            model.save(values, f'{arguments.prefix}_current.json')
            print('progress', start, iteration[0], 'minimum', diagnostic[0], 'margin', margin, 'error', diagnostic[2], 'grad', diagnostic[3], 'dad', diagnostic[12], 'seconds', time.monotonic()-started, flush=True)

    print('START', start, filename, flush=True)
    constraint_list = [{'type':'ineq','fun':constraints,'jac':jacobian}, {'type':'eq','fun':lambda values:model.evaluate(values)[0][16:], 'jac':lambda values:model.evaluate(values)[1][16:]}]
    result = minimize(objective, initial, method='SLSQP', jac=True, bounds=bounds(selection) + [(-1.23, 1.23)] * len(model.active), constraints=constraint_list, callback=callback, options={'maxiter':arguments.iterations, 'ftol':1e-11, 'disp':False})
    callback(result.x)
    model.save(result.x, f'{arguments.prefix}_{start}.json')
    print('END', start, result.message, 'metrics', model.evaluate(result.x)[0][:16].tolist(), 'margin', min(constraints(result.x)), 'calls', model.calls, flush=True)
    if (arguments.mode == 'dad' and best < .0002) or (arguments.mode != 'dad' and best < -.022):
        break
