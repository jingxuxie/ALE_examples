import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['JAX_ENABLE_X64'] = 'true'
os.environ['XLA_FLAGS'] = '--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.optimize as opt
import jax
import jax.numpy as jnp

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/pq_a_tool_for_prototyping_many_body_methods_for_quantum_chemistry__2106_06850/concept_2/participant')
sys.path.insert(0, str(ASSETS / 'workspace'))
from oracle import DeterminantCC
from api import artifact, endpoint_failures, check_continuation, CONSTRAINTS

jax.config.update('jax_enable_x64', True)
oracle = DeterminantCC()
energies = np.array(CONSTRAINTS['orbital_energies'])
upper = np.triu_indices(15)
basis = np.zeros((120, 15, 15))
for index, (row, column) in enumerate(zip(*upper)):
    basis[index, row, column] = 1
    basis[index, column, row] = 1
base = oracle.hamiltonian(energies, np.zeros((15, 15)))[0]
hmap = np.array([oracle.hamiltonian(energies, matrix)[0] - base for matrix in basis])
hfbase = np.array(oracle.hf_stability(base))
hfmap = np.array([np.array(oracle.hf_stability(base + matrix)) - hfbase for matrix in hmap])
generators = jnp.array(oracle.generators)
targets = jnp.array(oracle.targets)
identity = jnp.eye(20)
reference = jnp.array(oracle.ref)
onebody = jnp.array(oracle.one)
triple = 19
weights = jnp.array(np.sum(basis * basis, axis=(1, 2)))
search_target = float(os.environ.get('SEARCH_TARGET', '0'))
path_samples = int(os.environ.get('PATH_SAMPLES', '0'))
path_grid = os.environ.get('PATH_GRID')
dad_bound = float(os.environ.get('DAD_BOUND', '0.00085'))
anchor_path = os.environ.get('SEARCH_ANCHOR')
anchor = np.load(anchor_path) if anchor_path else None


def path_quantities(hamiltonian):
    exact_energies, exact_vectors = jnp.linalg.eigh(hamiltonian)
    exact = exact_vectors[:, 0]
    coefficients = exact / exact[0]
    singles = coefficients[targets[:9]]
    single_cluster = jnp.einsum('k,kij->ij', singles, generators[:9])
    doubles = (coefficients - single_cluster @ single_cluster @ reference / 2)[targets[9:]]
    amplitudes = jnp.concatenate((singles, doubles))
    for iteration in range(5):
        cluster = jnp.einsum('k,kij->ij', amplitudes, generators)
        cluster2 = cluster @ cluster / 2
        cluster3 = cluster2 @ cluster / 3
        positive = identity + cluster + cluster2 + cluster3
        negative = identity - cluster + cluster2 - cluster3
        transformed = negative @ hamiltonian @ positive
        column = transformed[:, 0]
        commutator = jnp.einsum('kij,j->ik', generators, column)
        jacobian = transformed[targets[:, None], targets[None, :]] - commutator[targets]
        amplitudes = amplitudes - jnp.linalg.solve(jacobian, column[targets])
    cluster = jnp.einsum('k,kij->ij', amplitudes, generators)
    right = (identity + cluster + cluster @ cluster / 2 + cluster @ cluster @ cluster / 6)[:, 0]
    overlap = (right @ exact)**2 / (right @ right)
    singular_min = jnp.linalg.svd(jacobian, compute_uv=False)[-1]
    return jnp.array([overlap - 0.996, exact_energies[1] - exact_energies[0] - 0.09,
                      singular_min - 0.025])


def quantities(vector):
    interaction = vector[:120]
    amplitudes = vector[120:138]
    multipliers = vector[138:156]
    hamiltonian = jnp.array(base) + jnp.einsum('k,kij->ij', interaction, jnp.array(hmap))
    cluster = jnp.einsum('k,kij->ij', amplitudes, generators)
    cluster2 = cluster @ cluster / 2
    cluster3 = cluster2 @ cluster / 3
    positive = identity + cluster + cluster2 + cluster3
    negative = identity - cluster + cluster2 - cluster3
    transformed = negative @ hamiltonian @ positive
    energy = transformed[0, 0]
    column = transformed[:, 0]
    commutator = jnp.einsum('kij,j->ik', generators, column)
    jacobian = transformed[targets[:, None], targets[None, :]] - commutator[targets]
    gradient = transformed[0, targets]
    right = positive[:, 0]
    row = reference.at[targets].set(multipliers)
    left = row @ negative
    density = jnp.einsum('i,pqij,j->pq', left, onebody, right)
    occupations = jnp.linalg.eigvalsh((density + density.T) / 2)
    dad = jnp.sqrt(jnp.sum((density - density.T)**2) / 3 + 1e-24)
    hf = jnp.array(hfbase) + jnp.einsum('k,kbij->bij', interaction, jnp.array(hfmap))
    hfmins = jnp.linalg.eigvalsh(hf)[:, 0]
    singulars = jnp.linalg.svd(jacobian, compute_uv=False)
    norm = right @ right
    shifted = hamiltonian - energy * identity + 10 * jnp.outer(right, right) / norm
    gap = jnp.linalg.eigvalsh(shifted)[0]
    equalities = jnp.concatenate((column[1:], gradient + jacobian.T @ multipliers))
    inequalities = jnp.concatenate((
        jnp.array([6.99**2 - jnp.sum(weights * interaction**2),
                   1.23**2 - amplitudes @ amplitudes,
                   1.45**2 - multipliers @ multipliers,
                   1 / 0.46 - norm,
                   gap - 0.11,
                   singulars[-1] - singulars[0] / 95,
                   jnp.min(jnp.real(jnp.linalg.eigvals(jacobian))) - 0.06,
                   dad_bound - dad]),
        hfmins - 0.06))
    if search_target > 0:
        inequalities = jnp.concatenate((inequalities, jnp.array([-search_target - occupations[0]])))
    if path_samples > 0:
        couplings = jnp.array([float(value) for value in path_grid.split(',')]) if path_grid else jnp.arange(1, path_samples + 1) / (path_samples + 1)
        matrices = jnp.array(base)[None] + couplings[:, None, None] * (hamiltonian - jnp.array(base))[None]
        path_inequalities = jax.vmap(path_quantities)(matrices)
        inequalities = jnp.concatenate((inequalities, path_inequalities.reshape(-1)))
    diagnostics = jnp.array([occupations[0], occupations[-1], dad, column[triple],
                             gap, 1 / norm, singulars[0] / singulars[-1],
                             hfmins[0], hfmins[1], jnp.linalg.norm(amplitudes),
                             jnp.linalg.norm(multipliers)])
    objective = occupations[0]
    if search_target > 0:
        objective = 0.01 * jnp.sum(weights * interaction**2) + amplitudes @ amplitudes + 0.1 * multipliers @ multipliers
    if anchor is not None:
        objective = 0.1 * jnp.sum((vector - jnp.array(anchor))**2)
    return objective, equalities, inequalities, diagnostics


@jax.jit
def combined(vector):
    objective, equalities, inequalities, diagnostics = quantities(vector)
    return jnp.concatenate((jnp.array([objective]), equalities, inequalities)), diagnostics


derivative = jax.jit(jax.jacfwd(lambda vector: combined(vector)[0]))


class Evaluation:
    def __init__(self):
        self.last = None
        self.values = None
        self.jac = None
        self.diag = None
        self.calls = 0

    def get(self, vector):
        if self.last is None or not np.array_equal(vector, self.last):
            self.last = vector.copy()
            values, diagnostics = combined(jnp.array(vector))
            self.values = np.asarray(values)
            self.diag = np.asarray(diagnostics)
            self.jac = None
            self.calls += 1
        return self.values

    def jacobian(self, vector):
        self.get(vector)
        if self.jac is None:
            self.jac = np.asarray(derivative(jnp.array(vector)))
        return self.jac


def pack(interaction, result):
    multipliers = oracle.lambda_state(result)[0]
    return np.concatenate((interaction[upper], result.amplitudes, multipliers))


def save(vector, filename):
    interaction = np.einsum('k,kij->ij', vector[:120], basis)
    Path(filename).write_text(json.dumps(artifact(interaction, vector[120:138]), indent=2))
    np.save(str(filename) + '.npy', vector)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=821)
    parser.add_argument('--restarts', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=1000)
    parser.add_argument('--initial')
    parser.add_argument('--prefix', default='opt')
    arguments = parser.parse_args()
    rng = np.random.default_rng(arguments.seed)
    started = time.monotonic()
    best = 1.0
    for restart in range(arguments.restarts):
        if arguments.initial and restart == 0:
            if arguments.initial.endswith('.npy'):
                initial = np.load(arguments.initial)
            else:
                data = json.loads(Path(arguments.initial).read_text())
                interaction = np.array(data['pair_matrix'])
                result = oracle.solve(oracle.hamiltonian(energies, interaction)[0], data['amplitudes'])
                initial = pack(interaction, result)
        else:
            for trial in range(10000):
                scale = rng.uniform(0.15, 0.45)
                raw = rng.normal(size=(15, 15))
                interaction = scale * (raw + raw.T) / np.sqrt(2)
                if np.max(np.abs(interaction)) > 1.45 or np.linalg.norm(interaction) > 6.8:
                    continue
                hamiltonian = oracle.hamiltonian(energies, interaction)[0]
                if min(np.linalg.eigvalsh(matrix)[0] for matrix in oracle.hf_stability(hamiltonian)) < 0.05:
                    continue
                result = oracle.solve(hamiltonian)
                if not result.converged:
                    continue
                diagnostics = oracle.diagnostics(hamiltonian, result)
                if diagnostics['ground_overlap'] < 0.995 or diagnostics['reference_weight'] < 0.5:
                    continue
                initial = pack(interaction, result)
                break
        evaluation = Evaluation()
        iteration = 0
        print('START', restart, time.monotonic() - started, flush=True)

        def callback(vector):
            nonlocal iteration, best
            iteration += 1
            values = evaluation.get(vector)
            equality = np.max(np.abs(values[1:38]))
            inequality = np.min(values[38:])
            if iteration % 20 == 0 or (equality < 1e-7 and inequality > -1e-7 and values[0] < best):
                print('ITER', restart, iteration, 'time', round(time.monotonic() - started, 2),
                      'eq', equality, 'ineq', inequality, 'diag', evaluation.diag.tolist(), flush=True)
                save(vector, arguments.prefix + '_latest.json')
            if equality < 1e-7 and inequality > -1e-7 and values[0] < best:
                best = values[0]
                save(vector, arguments.prefix + '_best.json')

        answer = opt.minimize(lambda vector: evaluation.get(vector)[0], initial,
                              jac=lambda vector: evaluation.jacobian(vector)[0],
                              constraints=[{'type': 'eq', 'fun': lambda vector: evaluation.get(vector)[1:38],
                                            'jac': lambda vector: evaluation.jacobian(vector)[1:38]},
                                           {'type': 'ineq', 'fun': lambda vector: evaluation.get(vector)[38:],
                                            'jac': lambda vector: evaluation.jacobian(vector)[38:]}],
                              bounds=[(-1.499, 1.499)] * 120 + [(-1.23, 1.23)] * 18 + [(-1.45, 1.45)] * 18,
                              method='SLSQP', callback=callback,
                              options={'maxiter': arguments.iterations, 'ftol': 1e-11, 'disp': False})
        values = evaluation.get(answer.x)
        print('END', restart, answer.success, answer.message, 'fun', answer.fun,
              'eq', np.max(np.abs(values[1:38])), 'ineq', np.min(values[38:]),
              'diag', evaluation.diag.tolist(), 'calls', evaluation.calls, flush=True)
        save(answer.x, arguments.prefix + f'_restart{restart}.json')
        if evaluation.diag[0] < -0.0202 and np.max(np.abs(values[1:38])) < 1e-8 and np.min(values[38:]) > -1e-8:
            interaction = np.einsum('k,kij->ij', answer.x[:120], basis)
            result = oracle.solve(oracle.hamiltonian(energies, interaction)[0], answer.x[120:138])
            diagnostics = oracle.diagnostics(oracle.hamiltonian(energies, interaction)[0], result)
            certificate = check_continuation(interaction, result.amplitudes, oracle)
            print('VERIFY', endpoint_failures(diagnostics), certificate['passed'], diagnostics, flush=True)
            Path(arguments.prefix + '_verification.json').write_text(json.dumps({'diagnostics': diagnostics, 'continuation': certificate}, indent=2))
            if not endpoint_failures(diagnostics) and certificate['passed']:
                Path('submission.json').write_text(json.dumps(artifact(interaction, result.amplitudes), indent=2))
                return


if __name__ == '__main__':
    main()
