import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
from search_model import generator_flat, identity, targets, ref, one, haxes_jax, oracle

parser = argparse.ArgumentParser()
parser.add_argument('--full', action='store_true')
parser.add_argument('--starts', type=int, default=20)
parser.add_argument('--prefix', default='general')
parser.add_argument('--population', type=float, default=.021)
parser.add_argument('--dad', type=float, default=0)
parser.add_argument('--infidelity', type=float, default=.00099)
parser.add_argument('--reference', type=float, default=.452)
arguments = parser.parse_args()
active = np.arange(18) if arguments.full else np.array([0, 4, 8, 9, 13, 17])
exact_active = np.arange(1,20) if arguments.full else np.array(sorted(list(oracle.targets[active]) + [19]))
count = len(active)
anti_rows, anti_cols = np.triu_indices(6, 1) if arguments.full else (np.arange(3), np.arange(3)+3)


def measurements(values):
    amplitudes = jnp.zeros(18).at[active].set(values[:count])
    multipliers = jnp.zeros(18).at[active].set(values[count:2*count])
    exact = ref.at[exact_active].set(values[2*count:])
    exact = exact / jnp.linalg.norm(exact)
    cluster = (amplitudes @ generator_flat).reshape(20, 20)
    square = cluster @ cluster / 2
    cube = square @ cluster / 3
    right = (identity + cluster + square + cube)[:, 0]
    inverse = identity - cluster + square - cube
    left_reference = ref.at[targets].set(multipliers)
    left = left_reference @ inverse
    density = jnp.einsum('i,pqij,j->pq', left, one, right)
    occupations = jnp.linalg.eigvalsh((density + density.T) / 2)
    gradient = jnp.einsum('i,kij,j->k', left, haxes_jax, right) - jnp.einsum('i,kij,j->k', exact, haxes_jax, exact)
    return jnp.concatenate((jnp.array([jnp.linalg.norm(gradient), occupations[0], jnp.linalg.norm(amplitudes), jnp.linalg.norm(multipliers), exact[0] ** 2, 1 - (exact @ right)**2 / (right @ right)]), density[anti_rows, anti_cols] - density[anti_cols, anti_rows]))


evaluate = jax.jit(measurements)
derivative = jax.jit(jax.jacfwd(measurements))
matrix = np.zeros((5, 6 + len(anti_rows)))
matrix[0, 1] = -1
matrix[1, 2] = -1
matrix[2, 3] = -1
matrix[3, 4] = 1
matrix[4, 5] = -1
offset = np.array([-arguments.population, 1.25, 1.5, -arguments.reference, arguments.infidelity])
rng = np.random.default_rng(3488)
best = 1e10
started = time.monotonic()
seeds = json.loads(Path('seeds.json').read_text())
for trial in range(arguments.starts):
    seed = json.loads(Path(seeds[trial % len(seeds)][1]).read_text())
    hamiltonian = oracle.hamiltonian([-1.2, -.9, -.5, .5, .9, 1.2], seed['pair_matrix'])[0]
    result = oracle.solve(hamiltonian, seed['amplitudes'])
    multipliers = oracle.lambda_state(result)[0]
    _, exact_vectors = np.linalg.eigh(hamiltonian)
    exact = exact_vectors[:, 0] / exact_vectors[0, 0]
    initial = np.concatenate((result.amplitudes[active], multipliers[active], exact[exact_active]))
    if arguments.full:
        initial += rng.normal(size=len(initial)) * .03
    constraints = [
        {'type':'ineq','fun':lambda values:offset + matrix @ np.array(evaluate(values)), 'jac':lambda values:matrix @ np.array(derivative(values))},
    ]
    if arguments.dad == 0:
        constraints.append({'type':'eq','fun':lambda values:np.array(evaluate(values))[6:], 'jac':lambda values:np.array(derivative(values))[6:]})
    else:
        constraints.append({'type':'ineq','fun':lambda values:(arguments.dad**2 - 2/3 * np.sum(np.array(evaluate(values))[6:]**2)) * 1000, 'jac':lambda values:-4000/3 * np.array(evaluate(values))[6:] @ np.array(derivative(values))[6:]})
    answer = minimize(lambda values:(float(evaluate(values)[0]),np.array(derivative(values))[0]), initial, jac=True, method='SLSQP', constraints=constraints, options={'maxiter':1500,'ftol':1e-12})
    diagnostic = np.array(evaluate(answer.x))
    feasible = min(offset + matrix @ diagnostic) > -1e-7 and np.linalg.norm(diagnostic[6:]) * np.sqrt(2/3) < arguments.dad + 1e-7
    print(trial, answer.message, diagnostic[:6].tolist(), 'anti', max(abs(diagnostic[6:])), 'seconds', time.monotonic()-started, flush=True)
    if feasible and diagnostic[0] < best:
        best = diagnostic[0]
        np.savez(f'{arguments.prefix}_best.npz', values=answer.x, metrics=diagnostic, active=active, exact_active=exact_active)
        print('BEST', trial, best, flush=True)
