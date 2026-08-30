import os
import sys
import json
import time
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
os.environ['JAX_PLATFORMS'] = 'cpu'
os.environ['JAX_ENABLE_X64'] = 'true'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['XLA_FLAGS'] = '--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1'

import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp

from oracle import DeterminantCC, random_pair_matrix
from api import CONSTRAINTS, artifact, endpoint_failures, check_continuation

jax.config.update('jax_enable_x64', True)
oracle = DeterminantCC()
energies = np.asarray(CONSTRAINTS['orbital_energies'])
pair_rows, pair_columns = np.triu_indices(15)
pair_count = len(pair_rows)
bases = np.zeros((pair_count, 15, 15))
for position, (row, column) in enumerate(zip(pair_rows, pair_columns)):
    bases[position, row, column] = 1.0
    bases[position, column, row] = 1.0
base_hamiltonian = oracle.hamiltonian(energies, np.zeros((15, 15)))[0]
hamiltonian_basis = np.asarray([oracle.hamiltonian(np.zeros(6), basis)[0] for basis in bases])
base_stability = np.asarray(oracle.hf_stability(base_hamiltonian))
stability_basis = np.asarray([oracle.hf_stability(basis) for basis in hamiltonian_basis])

generators = jnp.asarray(oracle.generators)
identity = jnp.eye(20)
reference = jnp.asarray(oracle.ref)
targets = jnp.asarray(oracle.targets)
one_body = jnp.asarray(oracle.one)
hzero = jnp.asarray(base_hamiltonian)
hbasis = jnp.asarray(hamiltonian_basis)
szero = jnp.asarray(base_stability)
sbasis = jnp.asarray(stability_basis)
weights = jnp.asarray(np.sum(bases * bases, axis=(1, 2)))


def quantities(parameters):
    interaction = parameters[:120]
    amplitudes = parameters[120:138]
    multipliers = parameters[138:]
    hamiltonian = hzero + jnp.einsum('a,aij->ij', interaction, hbasis)
    cluster = jnp.einsum('a,aij->ij', amplitudes, generators)
    square = cluster @ cluster
    cube = square @ cluster
    positive = identity + cluster + square / 2 + cube / 6
    inverse = identity - cluster + square / 2 - cube / 6
    hbar = inverse @ hamiltonian @ positive
    column = hbar[:, 0]
    commutator = jnp.einsum('kij,j->ik', generators, column)
    jacobian = hbar[targets[:, None], targets[None, :]] - commutator[targets]
    row = reference.at[targets].set(multipliers)
    right = positive[:, 0]
    left = row @ inverse
    density = jnp.einsum('i,pqij,j->pq', left, one_body, right)
    occupations = jnp.linalg.eigvalsh((density + density.T) / 2)
    objective = occupations[0]
    equality = jnp.concatenate((column[1:], hbar[0, targets] + jacobian.T @ multipliers))
    stability = szero + jnp.einsum('a,akij->kij', interaction, sbasis)
    real_min = jnp.linalg.eigvalsh(stability[0])[0]
    imaginary_min = jnp.linalg.eigvalsh(stability[1])[0]
    exact_values = jnp.linalg.eigvalsh(hamiltonian)
    singular_values = jnp.linalg.svd(jacobian, compute_uv=False)
    symmetric_eom_min = jnp.linalg.eigvalsh((jacobian + jacobian.T) / 2)[0]
    inequality = jnp.asarray([
        (48.0 - jnp.sum(weights * interaction * interaction)) / 48,
        (1.24 ** 2 - amplitudes @ amplitudes) / 1.24 ** 2,
        (1.48 ** 2 - multipliers @ multipliers) / 1.48 ** 2,
        1 / (right @ right) - 0.46,
        exact_values[1] - hbar[0, 0] - 0.12,
        real_min - 0.065,
        imaginary_min - 0.065,
        (90 * singular_values[-1] - singular_values[0]) / 10,
        symmetric_eom_min - 0.06,
    ])
    return jnp.concatenate((jnp.atleast_1d(objective), equality, inequality))


values_function = jax.jit(quantities)
derivative_function = jax.jit(jax.jacrev(quantities))


class CachedEvaluation:
    def __init__(self):
        self.parameters = None
        self.values = None
        self.derivatives = None
        self.calls = 0

    def evaluate(self, parameters):
        if self.parameters is None or not np.array_equal(parameters, self.parameters):
            self.parameters = parameters.copy()
            self.values = np.asarray(values_function(parameters))
            self.derivatives = np.asarray(derivative_function(parameters))
            self.calls += 1
        return self.values, self.derivatives

    def objective(self, parameters):
        values, derivatives = self.evaluate(parameters)
        return values[0], derivatives[0]

    def equality(self, parameters):
        return self.evaluate(parameters)[0][1:38]

    def equality_jacobian(self, parameters):
        return self.evaluate(parameters)[1][1:38]

    def inequality(self, parameters):
        return self.evaluate(parameters)[0][38:]

    def inequality_jacobian(self, parameters):
        return self.evaluate(parameters)[1][38:]


def starting_point(rng):
    choices = []
    for trial in range(500):
        interaction = random_pair_matrix(rng, rng.uniform(0.14, 0.35))
        hamiltonian = oracle.hamiltonian(energies, interaction)[0]
        if min(np.linalg.eigvalsh(block)[0] for block in oracle.hf_stability(hamiltonian)) < 0.1:
            continue
        result = oracle.solve(hamiltonian)
        if not result.converged:
            continue
        diagnostics = oracle.diagnostics(hamiltonian, result)
        if diagnostics['ground_overlap'] < .99 or diagnostics['amplitude_norm'] > 1.0:
            continue
        multipliers = oracle.lambda_state(result)[0]
        parameters = np.concatenate((interaction[pair_rows, pair_columns], result.amplitudes, multipliers))
        choices.append((diagnostics['occupation_violation'] + .02 * abs(result.right[-1]), parameters))
        if len(choices) >= 15:
            break
    return max(choices, key=lambda item: item[0])[1]


def assess(parameters, name, verbose=True):
    interaction = np.einsum('a,aij->ij', parameters[:120], bases)
    hamiltonian = oracle.hamiltonian(energies, interaction)[0]
    result = oracle.solve(hamiltonian, parameters[120:138], tolerance=2e-12, max_evaluations=500)
    diagnostics = oracle.diagnostics(hamiltonian, result)
    failures = endpoint_failures(diagnostics)
    diagnostics['failures'] = failures
    diagnostics['pair_norm'] = float(np.linalg.norm(interaction))
    diagnostics['pair_max'] = float(np.max(np.abs(interaction)))
    Path(name + '.json').write_text(json.dumps(artifact(interaction, result.amplitudes), indent=2))
    np.save(name + '.npy', parameters)
    if not failures:
        continuation = check_continuation(interaction, result.amplitudes, oracle)
        diagnostics['continuation'] = continuation
        if continuation['passed']:
            Path('best_valid.json').write_text(json.dumps(artifact(interaction, result.amplitudes), indent=2))
            if diagnostics['occupation_violation'] >= .0201:
                Path('submission.json').write_text(json.dumps(artifact(interaction, result.amplitudes), indent=2))
                Path('validation.json').write_text(json.dumps(diagnostics, indent=2))
                print('SUCCESS', diagnostics['occupation_violation'], flush=True)
                return True
    Path(name + '.diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
    if verbose:
        selected = ['occupation_violation', 'energy_error', 'ground_overlap', 'reference_weight', 'hf_real_min', 'hf_imaginary_min', 'jacobian_condition', 'lambda_norm', 'failures']
        print('ASSESS', name, json.dumps({key: diagnostics[key] for key in selected}), flush=True)
        if 'continuation' in diagnostics:
            path = diagnostics['continuation']
            print('PATH', path['passed'], min(row['overlap'] for row in path['history']), flush=True)
    return False


def main():
    started = time.monotonic()
    rng = np.random.default_rng(2026082801)
    for restart in range(12):
        parameters = starting_point(rng)
        if restart == 0 and len(sys.argv) > 1:
            parameters = np.load(sys.argv[1])
        evaluation = CachedEvaluation()
        initial_values, initial_derivatives = evaluation.evaluate(parameters)
        print('START', restart, 'objective', initial_values[0], 'equality', np.max(np.abs(initial_values[1:38])), 'inequality', np.min(initial_values[38:]), flush=True)
        if restart == 0:
            for index in (4, 52, 117, 122, 134, 141, 153):
                displacement = np.zeros(156)
                displacement[index] = 1e-5
                numerical = (np.asarray(values_function(parameters + displacement)) - np.asarray(values_function(parameters - displacement))) / 2e-5
                print('GRADIENT', index, np.max(np.abs(numerical - initial_derivatives[:, index])), flush=True)
        iterations = [0]

        def callback(current):
            iterations[0] += 1
            if iterations[0] % 10 == 0:
                values = evaluation.evaluate(current)[0]
                print('ITER', restart, iterations[0], 'seconds', round(time.monotonic() - started, 2), 'objective', values[0], 'equality', np.max(np.abs(values[1:38])), 'inequality', np.min(values[38:]), flush=True)
                np.save('current.npy', current)
            values = evaluation.evaluate(current)[0]
            if values[0] < -.0205 and np.max(np.abs(values[1:38])) < 1e-8 and np.min(values[38:]) > -1e-7:
                if assess(current, 'passing_candidate'):
                    raise SystemExit(0)

        constraints = [
            {'type': 'eq', 'fun': evaluation.equality, 'jac': evaluation.equality_jacobian},
            {'type': 'ineq', 'fun': evaluation.inequality, 'jac': evaluation.inequality_jacobian},
        ]
        result = minimize(evaluation.objective, parameters, jac=True, method='SLSQP',
                          bounds=[(-1.48, 1.48)] * 120 + [(-1.24, 1.24)] * 18 + [(-1.48, 1.48)] * 18,
                          constraints=constraints, callback=callback,
                          options={'maxiter': 500, 'ftol': 2e-11, 'disp': True})
        print('RESULT', restart, result.success, result.message, result.fun, evaluation.calls, flush=True)
        if assess(result.x, 'candidate_' + str(restart)):
            return
        if time.monotonic() - started > 2200:
            break


if __name__ == '__main__':
    main()
