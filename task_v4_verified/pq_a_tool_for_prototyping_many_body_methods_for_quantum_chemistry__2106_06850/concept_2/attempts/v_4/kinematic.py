import json
import time
import argparse
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
from search_model import generator_flat, identity, targets, ref, one, haxes_jax, oracle

active = np.array([0, 4, 8, 9, 13, 17])
parser=argparse.ArgumentParser()
parser.add_argument('--population',type=float,default=.022)
parser.add_argument('--starts',type=int,default=60)
parser.add_argument('--prefix',default='kinematic')
arguments=parser.parse_args()


def measurements(values):
    amplitudes = jnp.zeros(18).at[active].set(values[:6])
    multipliers = jnp.zeros(18).at[active].set(values[6:])
    cluster = (amplitudes @ generator_flat).reshape(20, 20)
    square = cluster @ cluster / 2
    cube = square @ cluster / 3
    right = (identity + cluster + square + cube)[:, 0]
    inverse = identity - cluster + square - cube
    left_reference = ref.at[targets].set(multipliers)
    left = left_reference @ inverse
    density = jnp.einsum('i,pqij,j->pq', left, one, right)
    occupations = jnp.linalg.eigvalsh((density + density.T) / 2)
    gradient = jnp.einsum('i,kij,j->k', left, haxes_jax, right) - jnp.einsum('i,kij,j->k', right, haxes_jax, right) / (right @ right)
    return jnp.concatenate((jnp.array([jnp.linalg.norm(gradient), occupations[0], jnp.linalg.norm(amplitudes), jnp.linalg.norm(multipliers), 1 / (right @ right)]), density[jnp.arange(3), jnp.arange(3)+3] - density[jnp.arange(3)+3, jnp.arange(3)]))


evaluate = jax.jit(measurements)
derivative = jax.jit(jax.jacfwd(measurements))
matrix = np.zeros((4, 8))
matrix[0, 1] = -1
matrix[1, 2] = -1
matrix[2, 3] = -1
matrix[3, 4] = 1
offset = np.array([-arguments.population, 1.24, 1.49, -.455])
rng = np.random.default_rng(3488)
best = 1e10
started = time.monotonic()
seeds = json.loads(Path('seeds.json').read_text())
for trial in range(arguments.starts):
    if trial < len(seeds):
        seed = json.loads(Path(seeds[trial][1]).read_text())
        hamiltonian = oracle.hamiltonian([-1.2, -.9, -.5, .5, .9, 1.2], seed['pair_matrix'])[0]
        result = oracle.solve(hamiltonian, seed['amplitudes'])
        multipliers = oracle.lambda_state(result)[0]
        initial = np.concatenate((result.amplitudes[active], multipliers[active]))
    else:
        initial = rng.normal(size=12) * .3
    constraints = [
        {'type':'ineq','fun':lambda values:offset + matrix @ np.array(evaluate(values)), 'jac':lambda values:matrix @ np.array(derivative(values))},
        {'type':'eq','fun':lambda values:np.array(evaluate(values))[5:], 'jac':lambda values:np.array(derivative(values))[5:]},
    ]
    answer = minimize(lambda values:(float(evaluate(values)[0]),np.array(derivative(values))[0]), initial, jac=True, method='SLSQP', constraints=constraints, options={'maxiter':1000,'ftol':1e-12})
    diagnostic = np.array(evaluate(answer.x))
    feasible = min(offset + matrix @ diagnostic) > -1e-7 and max(abs(diagnostic[5:])) < 1e-7
    print(trial, answer.message, diagnostic.tolist(), 'seconds', time.monotonic()-started, flush=True)
    if feasible and diagnostic[0] < best:
        best = diagnostic[0]
        np.savez(f'{arguments.prefix}_best.npz', values=answer.x, metrics=diagnostic)
        print('BEST', trial, best, flush=True)
