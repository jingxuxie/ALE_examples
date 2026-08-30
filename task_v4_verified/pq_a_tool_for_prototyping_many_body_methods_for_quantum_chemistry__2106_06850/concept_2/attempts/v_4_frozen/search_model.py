import os
import json
import time
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
os.environ['JAX_ENABLE_X64'] = 'True'
os.environ['JAX_PLATFORMS'] = 'cpu'
os.environ['XLA_FLAGS'] = '--xla_cpu_multi_thread_eigen=false --xla_force_host_platform_device_count=1'

import numpy as np
import scipy.linalg as sla
from scipy.optimize import root, minimize
import jax
import jax.numpy as jnp
from oracle import DeterminantCC, CCResult
from api import artifact, check_continuation, endpoint_failures

oracle = DeterminantCC()
epsilon = np.array([-1.2, -.9, -.5, .5, .9, 1.2])
paired_virtuals = [int(value) for value in os.environ.get('PAIRING', '345')]
orbital_colors = {orbital: orbital for orbital in range(3)}
orbital_colors.update({orbital: color for color, orbital in enumerate(paired_virtuals)})
paired_amplitudes = np.array([index for index, label in enumerate(oracle.labels) if sorted(orbital_colors[orbital] for orbital in label['holes']) == sorted(orbital_colors[orbital] for orbital in label['particles'])])
axes = []
coordinates = []
structured = []
for row in range(15):
    for column in range(row, 15):
        direction = np.zeros((15, 15))
        direction[row, column] = direction[column, row] = 1. if row == column else 1 / np.sqrt(2)
        axes.append(direction)
        coordinates.append((row, column))
        first = sorted(orbital_colors[orbital] for orbital in oracle.pairs[row])
        second = sorted(orbital_colors[orbital] for orbital in oracle.pairs[column])
        if first == second:
            structured.append(len(axes) - 1)
axes = np.array(axes)
hbase = oracle.hamiltonian(epsilon, np.zeros((15, 15)))[0]
haxes = np.array([oracle.hamiltonian(np.zeros(6), direction)[0] for direction in axes])
hfbase = np.array(oracle.hf_stability(hbase))
hfaxes = np.array([oracle.hf_stability(derivative) for derivative in haxes])
generators = jnp.array(oracle.generators)
generator_flat = jnp.array(oracle.generator_flat)
targets = jnp.array(oracle.targets)
identity = jnp.eye(20)
one = jnp.array(oracle.one)
ref = jnp.array(oracle.ref)
axes_jax = jnp.array(axes)
haxes_jax = jnp.array(haxes)


def equations(hamiltonian, amplitudes):
    cluster = (amplitudes @ generator_flat).reshape((20, 20))
    square = cluster @ cluster / 2
    cube = square @ cluster / 3
    positive = identity + cluster + square + cube
    inverse = identity - cluster + square - cube
    transformed = inverse @ hamiltonian @ positive
    column = transformed[:, 0]
    jacobian = transformed[jnp.ix_(targets, targets)] - jnp.einsum('kij,j->ik', generators, column)[targets]
    return column[targets], jacobian, transformed, positive, inverse


def state_metrics(coefficients, amplitudes, implicit_enabled):
    hamiltonian = jnp.array(hbase) + jnp.einsum('k,kij->ij', coefficients, haxes_jax)
    residual, jacobian, _, _, _ = equations(hamiltonian, amplitudes)
    implicit = amplitudes - jnp.linalg.solve(jax.lax.stop_gradient(jacobian), residual) if implicit_enabled else amplitudes
    residual, jacobian, transformed, positive, inverse = equations(hamiltonian, implicit)
    right = positive[:, 0]
    multipliers = jnp.linalg.solve(jacobian.T, -transformed[0, targets])
    left_reference = ref.at[targets].set(multipliers)
    left = left_reference @ inverse
    density = jnp.einsum('i,pqij,j->pq', left, one, right)
    occupations = jnp.linalg.eigvalsh((density + density.T) / 2)
    exact_values, exact_vectors = jnp.linalg.eigh(hamiltonian)
    exact = exact_vectors[:, 0]
    gradient = jnp.einsum('i,kij,j->k', left, haxes_jax, right) - jnp.einsum('i,kij,j->k', exact, haxes_jax, exact)
    real_hf, imag_hf = jnp.array(hfbase) + jnp.einsum('k,kbij->bij', coefficients, jnp.array(hfaxes))
    singular_values = jnp.linalg.svd(jacobian, compute_uv=False)
    eom = jnp.linalg.eigvals(jacobian)
    return jnp.array([
        occupations[0], occupations[-1] - 1,
        transformed[0, 0] - exact_values[0],
        jnp.sqrt(jnp.sum(gradient ** 2) + 1e-30),
        1 - (exact @ right) ** 2 / (right @ right),
        exact[0] ** 2,
        exact_values[1] - exact_values[0],
        jnp.linalg.eigvalsh(real_hf)[0],
        jnp.linalg.eigvalsh(imag_hf)[0],
        singular_values[0] / singular_values[-1],
        jnp.linalg.norm(multipliers),
        jnp.linalg.norm(implicit),
        jnp.sqrt(jnp.sum((density - density.T) ** 2) / 3 + 1e-30),
        jnp.linalg.norm(coefficients),
        jnp.min(eom.real),
        singular_values[-1],
    ])


def metrics(coefficients, amplitudes):
    return state_metrics(coefficients, amplitudes, True)


compiled_metrics = jax.jit(metrics)
compiled_jacobian = jax.jit(jax.jacfwd(metrics, argnums=0))


class Model:
    def __init__(self, selection=None):
        self.selection = np.arange(120) if selection is None else np.array(selection)
        self.last_x = None
        self.last_t = np.zeros(18)
        self.calls = 0
        self.bad_roots = 0

    def full(self, values):
        coefficients = np.zeros(120)
        coefficients[self.selection] = values
        return coefficients

    def evaluate(self, values):
        if self.last_x is not None and np.array_equal(self.last_x, values):
            return self.last_metrics, self.last_gradient
        coefficients = self.full(values)
        hamiltonian = hbase + np.einsum('k,kij->ij', coefficients, haxes)
        _, vectors = np.linalg.eigh(hamiltonian)
        exact = vectors[:, 0] / vectors[0, 0]
        initial = exact[oracle.targets].copy()
        singles = (initial[:9] @ oracle.generator_flat[:9]).reshape(20, 20)
        initial[9:] -= (singles @ singles @ oracle.ref)[oracle.targets[9:]] / 2
        initial = np.clip(initial, -2, 2)
        result = oracle.solve(hamiltonian, initial, tolerance=2e-11, max_evaluations=250)
        if not result.converged:
            result = oracle.solve(hamiltonian, tolerance=2e-11, max_evaluations=250)
        if result.converged:
            self.last_t = result.amplitudes.copy()
        else:
            self.bad_roots += 1
        self.last_metrics = np.array(compiled_metrics(coefficients, result.amplitudes))
        self.last_gradient = np.array(compiled_jacobian(coefficients, result.amplitudes))[:, self.selection]
        self.last_x = values.copy()
        self.calls += 1
        return self.last_metrics, self.last_gradient

    def save(self, values, path):
        self.evaluate(values)
        matrix = np.einsum('k,kij->ij', self.full(values), axes)
        Path(path).write_text(json.dumps(artifact(matrix, self.last_t), indent=2))


class JointModel:
    def __init__(self, selection=None):
        self.selection = np.arange(120) if selection is None else np.array(selection)
        self.active = np.arange(18) if len(self.selection) == 120 else paired_amplitudes
        self.last_x = None
        self.calls = 0
        self.bad_roots = 0
        self.coefficient_count = len(self.selection)

        def combined(values):
            coefficients = jnp.zeros(120).at[self.selection].set(values[:self.coefficient_count])
            amplitudes = jnp.zeros(18).at[self.active].set(values[self.coefficient_count:])
            hamiltonian = jnp.array(hbase) + jnp.einsum('k,kij->ij', coefficients, haxes_jax)
            residual = equations(hamiltonian, amplitudes)[0][self.active]
            return jnp.concatenate((state_metrics(coefficients, amplitudes, False), residual))

        self.metric_function = jax.jit(combined)
        self.gradient_function = jax.jit(jax.jacfwd(combined))

    def evaluate(self, values):
        if self.last_x is None or not np.array_equal(self.last_x, values):
            self.last_metrics = np.array(self.metric_function(values))
            self.last_gradient = np.array(self.gradient_function(values))
            self.last_x = values.copy()
            self.calls += 1
        return self.last_metrics, self.last_gradient

    def save(self, values, path):
        coefficients = np.zeros(120)
        coefficients[self.selection] = values[:self.coefficient_count]
        amplitudes = np.zeros(18)
        amplitudes[self.active] = values[self.coefficient_count:]
        matrix = np.einsum('k,kij->ij', coefficients, axes)
        Path(path).write_text(json.dumps(artifact(matrix, amplitudes), indent=2))


def bounds(selection):
    limits = np.array([1.498 if row == column else 1.498 * np.sqrt(2) for row, column in coordinates])
    return [(-limits[index], limits[index]) for index in selection]


if __name__ == '__main__':
    started = time.monotonic()
    model = Model(structured)
    rng = np.random.default_rng(432)
    values = rng.normal(size=len(structured)) * .15
    diagnostic, derivative = model.evaluate(values)
    print('structured', len(structured), 'metrics', diagnostic, 'seconds', time.monotonic() - started, flush=True)
    direction = rng.normal(size=len(structured))
    plus = model.evaluate(values + 1e-5 * direction)[0]
    minus = model.evaluate(values - 1e-5 * direction)[0]
    print('derivative check', np.column_stack(((plus - minus) / 2e-5, derivative @ direction)), flush=True)
