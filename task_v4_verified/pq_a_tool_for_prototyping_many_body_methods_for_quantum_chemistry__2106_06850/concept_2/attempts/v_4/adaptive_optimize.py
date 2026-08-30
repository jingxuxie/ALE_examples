import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
from search_model import Model, structured, axes, bounds, hbase, haxes_jax, hfbase, hfaxes, equations, state_metrics, targets, ref, oracle

parser = argparse.ArgumentParser()
parser.add_argument('--seed', default='basequiet_best.json')
parser.add_argument('--full', action='store_true')
parser.add_argument('--iterations', type=int, default=2000)
parser.add_argument('--prefix', default='finite')
parser.add_argument('--population', type=float, default=.0201)
parser.add_argument('--dad', type=float, default=.00095)
parser.add_argument('--error', type=float, default=.0000995)
parser.add_argument('--mode', default='population')
parser.add_argument('--refmax', type=float, default=1)
parser.add_argument('--infidmin', type=float, default=0)
parser.add_argument('--method', default='slsqp')
parser.add_argument('--trust', type=float, default=10)
parser.add_argument('--reference', type=float, default=.4501)
parser.add_argument('--noise', type=float, default=.005)
parser.add_argument('--hfaxes', default='')
parser.add_argument('--rounds', type=int, default=1)
arguments = parser.parse_args()
selection = np.arange(120) if arguments.full else np.array(structured)
base_model = Model(selection)
hf_displacements=[]
for axis in [int(value) for value in arguments.hfaxes.split(',') if value]:
    for sign in [1,-1]:
        displacement=np.zeros(120);displacement[axis]=sign*.001;hf_displacements.append(displacement)
hf_displacements=np.array(hf_displacements)


def combined(values, initial):
    coefficients = jnp.zeros(120).at[selection].set(values)
    hamiltonian = jnp.array(hbase) + jnp.einsum('k,kij->ij', coefficients, haxes_jax)
    residual, jacobian, _, _, _ = equations(hamiltonian, initial)
    amplitudes = initial - jnp.linalg.solve(jax.lax.stop_gradient(jacobian), residual)
    _, jacobian, transformed, positive, inverse = equations(hamiltonian, amplitudes)
    right = positive[:, 0]
    multipliers = jnp.linalg.solve(jacobian.T, -transformed[0, targets])
    left = ref.at[targets].set(multipliers) @ inverse
    _, vectors = jnp.linalg.eigh(hamiltonian)
    exact = vectors[:, 0]
    gradient = jnp.einsum('i,kij,j->k', left, haxes_jax, right) - jnp.einsum('i,kij,j->k', exact, haxes_jax, exact)
    direction = gradient / jnp.linalg.norm(gradient)
    points = jnp.stack((coefficients, coefficients + .001 * direction, coefficients - .001 * direction))

    def neighbor(point):
        point_hamiltonian = jnp.array(hbase) + jnp.einsum('k,kij->ij', point, haxes_jax)

        def iteration(index, current):
            point_residual, point_jacobian, _, _, _ = equations(point_hamiltonian, current)
            return current - jnp.linalg.solve(point_jacobian, point_residual)

        solution = jax.lax.fori_loop(0, 5, iteration, amplitudes)
        return state_metrics(point, solution, False)

    main_metrics=jax.vmap(neighbor)(points)
    if len(hf_displacements):
        hf_points=coefficients[None,:]+jnp.array(hf_displacements)
        hessians=jnp.array(hfbase)+jnp.einsum('pk,kbij->pbij',hf_points,jnp.array(hfaxes))
        minimum_hf=jnp.linalg.eigvalsh(hessians)[:,:,0]
        extra_metrics=jnp.broadcast_to(main_metrics[0],(len(hf_displacements),16)).at[:,7:9].set(minimum_hf)
        extra_hamiltonians=jnp.array(hbase)+jnp.einsum('pk,kij->pij',hf_points,haxes_jax)
        extra_energies,extra_vectors=jnp.linalg.eigh(extra_hamiltonians)
        extra_metrics=extra_metrics.at[:,5].set(extra_vectors[:,0,0]**2).at[:,6].set(extra_energies[:,1]-extra_energies[:,0])
        main_metrics=jnp.concatenate((main_metrics,extra_metrics))
    return main_metrics


metric_function = jax.jit(combined)
gradient_function = jax.jit(jax.jacfwd(combined, argnums=0))
last_values = None
cached = None
calls = 0


def evaluate(values):
    global last_values, cached, calls
    if last_values is not None and np.array_equal(last_values, values):
        return cached
    base_model.evaluate(values)
    diagnostic = np.array(metric_function(values, base_model.last_t))
    derivative = np.array(gradient_function(values, base_model.last_t))
    cached = diagnostic, derivative
    last_values = values.copy()
    calls += 1
    return cached


def constraint_values(diagnostic):
    minimum, maximum, error, gradient, infidelity, reference, gap, real_hf, imag_hf, condition, multiplier, amplitude, dad, norm, eom, singular = diagnostic.T
    matrix_values=np.array([
        (arguments.error - error) / .001,
        (arguments.error + error) / .001,
        (.00099 - infidelity) / .01,
        reference - arguments.reference,
        gap - .1001,
        real_hf - .0501,
        imag_hf - .0501,
        (99 - condition) / 100,
        1.499 - multiplier,
        1.249 - amplitude,
        (-arguments.population - minimum) * 10 if arguments.mode == 'dad' else (arguments.dad - dad) / .01,
        (6.998 - norm) / 7,
        eom - .0501,
        singular - .0201,
        arguments.refmax - reference,
        (infidelity - arguments.infidmin) / .01 if arguments.infidmin>0 else np.ones_like(infidelity),
    ]).T
    return np.concatenate((matrix_values[:3].ravel(),matrix_values[3:][:,[3,4,5,6]].ravel()))


constraint_matrix = np.zeros((16, 16))
constraint_matrix[0, 2] = -1000
constraint_matrix[1, 2] = 1000
for row, index, scale in [(2, 4, -100), (3, 5, 1), (4, 6, 1), (5, 7, 1), (6, 8, 1), (7, 9, -.01), (8, 10, -1), (9, 11, -1), (11, 13, -1/7), (12, 14, 1), (13, 15, 1)]:
    constraint_matrix[row, index] = scale
constraint_matrix[10, 0 if arguments.mode == 'dad' else 12] = -10 if arguments.mode == 'dad' else -100
constraint_matrix[14, 5] = -1
constraint_matrix[15, 4] = 100 if arguments.infidmin>0 else 0
objective_index = 12 if arguments.mode == 'dad' else 0
seed_data = json.loads(Path(arguments.seed).read_text())
filenames = [entry[1] for entry in seed_data] if isinstance(seed_data, list) else [arguments.seed]
if arguments.rounds>1:
    filenames=[filenames[0]]*arguments.rounds
started = time.monotonic()
best = np.inf
previous_values=None


for start, filename in enumerate(filenames):
    data = json.loads(Path(filename).read_text())
    initial = np.einsum('kij,ij->k', axes, np.array(data['pair_matrix']))[selection]
    if previous_values is not None and arguments.rounds>1:
        initial=previous_values.copy()
    elif arguments.full:
        initial += np.random.default_rng(748).normal(size=120) * arguments.noise
    base_model.last_t = np.array(data['amplitudes'])
    iteration = [0]

    def objective(values):
        diagnostic, derivative = evaluate(values)
        worst = np.argmax(diagnostic[:, objective_index])
        return 10 * diagnostic[worst, objective_index], 10 * derivative[worst, objective_index]

    def constraints(values):
        return constraint_values(evaluate(values)[0])

    def jacobian(values):
        matrix_derivatives=np.einsum('am,pmk->pak', constraint_matrix, evaluate(values)[1])
        return np.vstack((matrix_derivatives[:3].reshape(-1,len(selection)),matrix_derivatives[3:][:,[3,4,5,6]].reshape(-1,len(selection))))

    def callback(values):
        global best
        iteration[0] += 1
        diagnostic, derivative = evaluate(values)
        margin = np.min(constraint_values(diagnostic))
        current = max(diagnostic[:, objective_index])
        if margin > -1e-7 and current < best:
            best = current
            base_model.save(values, f'{arguments.prefix}_best.json')
            print('BEST', start, iteration[0], 'objective', best, 'metrics', diagnostic.tolist(), flush=True)
        if iteration[0] % 20 == 0:
            base_model.save(values, f'{arguments.prefix}_current.json')
            print('progress', start, iteration[0], 'minimum', diagnostic[:,0].tolist(), 'margin', margin, 'error', diagnostic[:,2].tolist(), 'grad', diagnostic[0,3], 'dad', diagnostic[:,12].tolist(), 'seconds', time.monotonic()-started, flush=True)

    print('START', filename, flush=True)
    local_bounds = [(max(lower, value-arguments.trust), min(upper, value+arguments.trust)) for value, (lower, upper) in zip(initial, bounds(selection))]
    if arguments.method == 'repair':
        def penalty(values):
            diagnostic, derivative = evaluate(values)
            margins = constraint_values(diagnostic)
            margin_derivatives = jacobian(values)
            population_margins = 10 * (-arguments.population - diagnostic[:,0])
            population_derivatives = -10 * derivative[:,0]
            margins = np.concatenate((margins, population_margins))
            margin_derivatives = np.vstack((margin_derivatives,population_derivatives))
            negative = np.minimum(margins,0)
            return np.sum(negative**2), 2 * negative @ margin_derivatives
        result = minimize(penalty, initial, method='L-BFGS-B', jac=True, bounds=local_bounds, callback=callback, options={'maxiter':arguments.iterations, 'ftol':1e-18, 'gtol':1e-10, 'maxls':50})
    else:
        result = minimize(objective, initial, method='SLSQP', jac=True, bounds=local_bounds, constraints={'type':'ineq','fun':constraints,'jac':jacobian}, callback=callback, options={'maxiter':arguments.iterations, 'ftol':1e-11, 'disp':False})
    callback(result.x)
    previous_values=result.x.copy()
    base_model.save(result.x, f'{arguments.prefix}_{start}.json')
    print('END', result.message, 'metrics', evaluate(result.x)[0].tolist(), 'margin', min(constraints(result.x)), 'calls', calls, flush=True)
