import os
import sys

os.environ.setdefault('JAX_ENABLE_X64', 'true')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('XLA_FLAGS', '--xla_cpu_multi_thread_eigen=false')
try:
    available_cpus = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available_cpus[:8])
except (AttributeError, OSError):
    pass

import jax
import jax.numpy as jnp
import numpy as np
from scipy.integrate import solve_ivp

jax.config.update('jax_enable_x64', True)

PATHS = ((1, 2, -1, -2), (1, 1, 2, -1, -1, -2),
         (1, 2, 2, -1, -2, -2))


def adjoint(matrix):
    return jnp.swapaxes(matrix.conj(), -1, -2)


def path_factors(links, path):
    position = [0, 0]
    factors = []
    for edge in path:
        axis = abs(edge) - 1
        if edge < 0:
            position[axis] -= 1
        factor = jnp.roll(links[:, :, axis],
                          tuple(-value for value in position), axis=(0, 1))
        factors.append(adjoint(factor) if edge < 0 else factor)
        if edge > 0:
            position[axis] += 1
    return factors


def time_coefficients(weights, time):
    basis = jnp.array((1.0, jnp.sin(2 * jnp.pi * time),
                       jnp.cos(2 * jnp.pi * time)))
    return jnp.einsum('t,ptf->pf', basis, weights)


class MatrixField:
    def __init__(self, shape, generators):
        self.shape = shape
        self.entries = int(np.prod(shape))
        self.dimension = shape[-1]
        self.generators = jnp.asarray(generators)
        gram = -np.einsum('aij,bji->ab', generators, generators).real
        scale = np.trace(gram) / len(generators)
        self.scale = float(scale)
        self.isotropic = (len(generators) == self.dimension**2 - 1 and
                          scale > 0 and np.max(np.abs(
                              gram - scale * np.eye(len(generators)))) <=
                          1e-11 * scale)
        self.casimir = jnp.einsum('aij,ajk->ik', self.generators,
                                  self.generators)
        self.covariance = jnp.einsum('aij,akl->ijkl', self.generators,
                                     self.generators)
        self.rhs = jax.jit(self._rhs)
        self.pullback = jax.jit(self._pullback)

    def pack(self, links):
        return np.concatenate((links.real.ravel(), links.imag.ravel(),
                               np.zeros(1)))

    def unpack(self, state):
        return (state[:self.entries] +
                1j * state[self.entries:2 * self.entries]).reshape(self.shape)

    def _isotropic_laplacian(self, matrix, trace, square):
        dimension = self.dimension
        scale = self.scale
        casimir = scale * (dimension**2 - 1) / dimension
        squared_derivative = -scale / dimension * (square - trace**2)
        absolute_derivative = scale / dimension**2 * (
            jnp.sum(jnp.abs(matrix)**2, axis=(-2, -1)) -
            dimension * jnp.abs(trace)**2)
        return jnp.stack((
            -casimir * trace.real,
            -2 * casimir * trace.real**2 + absolute_derivative +
            squared_derivative.real,
            -2 * casimir * trace.imag**2 + absolute_derivative -
            squared_derivative.real,
            (-2 * casimir + 2 * scale / dimension) * square.real -
            2 * scale * dimension * (trace**2).real), axis=-1)

    def _general_laplacian(self, factors, path, trace):
        identity = jnp.broadcast_to(jnp.eye(self.dimension), factors[0].shape)
        prefixes = [identity]
        for factor in factors:
            prefixes.append(prefixes[-1] @ factor)
        suffixes = [identity]
        for factor in reversed(factors):
            suffixes.append(factor @ suffixes[-1])
        suffixes.reverse()
        laplacian = jnp.zeros(trace.shape + (4,))
        for index, edge in enumerate(path):
            boundary = index if edge > 0 else index + 1
            cyclic = suffixes[boundary] @ prefixes[boundary]
            first = jnp.einsum('aij,...ji->...a', self.generators,
                               cyclic) / self.dimension
            second = jnp.einsum('ij,...ji->...', self.casimir,
                                cyclic) / self.dimension
            cyclic_square = cyclic @ cyclic
            sandwich = jnp.einsum('ijkl,...jk->...il', self.covariance,
                                  cyclic)
            square_second = 2 / self.dimension * (
                jnp.einsum('ij,...ji->...', self.casimir, cyclic_square) +
                jnp.einsum('...ij,...ji->...', sandwich, cyclic)).real
            laplacian = laplacian + jnp.stack((
                second.real,
                2 * jnp.sum(first.real**2, axis=-1) +
                2 * trace.real * second.real,
                2 * jnp.sum(first.imag**2, axis=-1) +
                2 * trace.imag * second.imag,
                square_second), axis=-1)
        return laplacian

    def potential_and_divergence(self, links, weights, time):
        coefficients = time_coefficients(weights, time)
        value = jnp.array(0.0)
        divergence = jnp.array(0.0)
        for path_index, path in enumerate(PATHS):
            factors = path_factors(links, path)
            matrix = factors[0]
            for factor in factors[1:]:
                matrix = matrix @ factor
            trace = jnp.trace(matrix, axis1=-2, axis2=-1) / self.dimension
            square = jnp.trace(matrix @ matrix, axis1=-2,
                                axis2=-1) / self.dimension
            features = jnp.stack((trace.real, trace.real**2,
                                   trace.imag**2, square.real), axis=-1)
            value = value + jnp.sum(features * coefficients[path_index])
            if self.isotropic:
                laplacian = len(path) * self._isotropic_laplacian(
                    matrix, trace, square)
            else:
                laplacian = self._general_laplacian(factors, path, trace)
            divergence = divergence + jnp.sum(
                laplacian * coefficients[path_index])
        return value, divergence

    def _rhs(self, time, state, weights):
        links = self.unpack(state)
        (_, divergence), gradient = jax.value_and_grad(
            self.potential_and_divergence, has_aux=True)(links, weights, time)
        cotangent = links @ jnp.swapaxes(gradient, -1, -2)
        components = jnp.einsum('aij,...ji->...a', self.generators,
                                 cotangent).real
        vector = jnp.einsum('...a,aij->...ij', components, self.generators)
        velocity = vector @ links
        return jnp.concatenate((velocity.real.ravel(), velocity.imag.ravel(),
                                jnp.reshape(-divergence, (1,))))

    def _pullback(self, time, state, weights, cotangent):
        _, backward = jax.vjp(lambda state_arg, weight_arg:
                             self._rhs(time, state_arg, weight_arg),
                             state, weights)
        state_gradient, weight_gradient = backward(cotangent)
        return jnp.concatenate((state_gradient, weight_gradient.ravel()))

    def vector(self, links, rhs):
        return self.unpack(rhs) @ np.swapaxes(links.conj(), -1, -2)

    def terminal_cotangent(self, state, probe, density_weight):
        return np.concatenate((probe.real.ravel(), probe.imag.ravel(),
                               np.array([density_weight])))

    def initial_gradient(self, links, gradient):
        ambient = (gradient[:self.entries] -
                   1j * gradient[self.entries:2 * self.entries]).reshape(
                       self.shape)
        cotangent = links @ np.swapaxes(ambient, -1, -2)
        components = np.einsum('aij,...ji->...a',
                                np.asarray(self.generators), cotangent).real
        return np.einsum('...a,aij->...ij', components,
                         np.asarray(self.generators))

    def final_state(self, state):
        links = np.asarray(self.unpack(state))
        left, _, right = np.linalg.svd(links)
        unitary = left @ right
        determinant = np.linalg.det(unitary)
        return unitary * np.exp(-1j * np.angle(determinant) /
                                self.dimension)[..., None, None]


class AbelianField:
    def __init__(self, shape, generators):
        self.shape = shape
        self.angle_shape = shape[:3]
        self.entries = int(np.prod(self.angle_shape))
        self.metric = float(np.sum(np.asarray(generators).imag**2))
        self.rhs = jax.jit(self._rhs)
        self.pullback = jax.jit(self._pullback)

    def pack(self, links):
        return np.concatenate((np.angle(links).ravel(), np.zeros(1)))

    def _rhs(self, time, state, weights):
        angles = state[:-1].reshape(self.angle_shape)
        coefficients = time_coefficients(weights, time)
        velocity = jnp.zeros_like(angles)
        divergence = jnp.array(0.0)
        for path_index, path in enumerate(PATHS):
            position = [0, 0]
            phase = jnp.zeros(self.angle_shape[:2])
            locations = []
            for edge in path:
                axis = abs(edge) - 1
                sign = 1 if edge > 0 else -1
                if edge < 0:
                    position[axis] -= 1
                offset = tuple(position)
                phase = phase + sign * jnp.roll(
                    angles[:, :, axis], tuple(-value for value in offset),
                    axis=(0, 1))
                locations.append((axis, sign, offset))
                if edge > 0:
                    position[axis] += 1
            coefficient = coefficients[path_index]
            harmonic = coefficient[1] - coefficient[2] + 2 * coefficient[3]
            first = -coefficient[0] * jnp.sin(phase) - harmonic * jnp.sin(
                2 * phase)
            second = -coefficient[0] * jnp.cos(phase) - 2 * harmonic * jnp.cos(
                2 * phase)
            for axis, sign, offset in locations:
                velocity = velocity.at[:, :, axis].add(
                    sign * jnp.roll(first, offset, axis=(0, 1)))
            divergence = divergence + len(path) * jnp.sum(second)
        return self.metric * jnp.concatenate((velocity.ravel(),
                                              jnp.reshape(-divergence, (1,))))

    def _pullback(self, time, state, weights, cotangent):
        _, backward = jax.vjp(lambda state_arg, weight_arg:
                             self._rhs(time, state_arg, weight_arg),
                             state, weights)
        state_gradient, weight_gradient = backward(cotangent)
        return jnp.concatenate((state_gradient, weight_gradient.ravel()))

    def vector(self, links, rhs):
        return (1j * rhs[:-1]).reshape(self.shape)

    def final_state(self, state):
        return np.exp(1j * state[:-1]).reshape(self.shape)

    def terminal_cotangent(self, state, probe, density_weight):
        links = self.final_state(state)
        gradient = (probe.conj() * (1j * links)).real
        return np.concatenate((gradient.ravel(), np.array([density_weight])))

    def initial_gradient(self, links, gradient):
        return (1j * self.metric * gradient[:-1]).reshape(self.shape)


def solve(data):
    links = np.asarray(data['links'], dtype=np.complex128)
    weights = np.asarray(data['weights'], dtype=np.float64)
    generators = np.asarray(data['generators'], dtype=np.complex128)
    probe = np.asarray(data['probe'], dtype=np.complex128)
    density_weight = float(data['density_weight'])
    time_start = float(data['t0'])
    time_end = float(data['t1'])
    field_type = AbelianField if links.shape[-1] == 1 else MatrixField
    field = field_type(links.shape, generators)
    initial = field.pack(links)
    device_weights = jnp.asarray(weights)

    def forward_rhs(time, state):
        return np.asarray(field.rhs(time, state, device_weights))

    first_rhs = forward_rhs(time_start, initial)
    result = {
        'vector': np.asarray(field.vector(links, first_rhs)),
        'divergence': np.asarray(-first_rhs[-1]),
    }
    if time_start == time_end:
        final = initial
        initial_cotangent = field.terminal_cotangent(final, probe, density_weight)
        weight_gradient = np.zeros_like(weights)
    else:
        trajectory = solve_ivp(forward_rhs, (time_start, time_end), initial,
                               method='DOP853', rtol=5e-10, atol=2e-12,
                               dense_output=True)
        if not trajectory.success:
            raise RuntimeError(trajectory.message)
        final = trajectory.y[:, -1]
        terminal = field.terminal_cotangent(final, probe, density_weight)
        adjoint_terminal = np.concatenate((terminal, np.zeros(weights.size)))

        def backward_rhs(time, augmented):
            state = trajectory.sol(time)
            cotangent = augmented[:initial.size]
            return -np.asarray(field.pullback(time, state, device_weights,
                                              cotangent))

        sensitivity = solve_ivp(backward_rhs, (time_end, time_start),
                                adjoint_terminal, method='DOP853',
                                rtol=5e-10, atol=2e-12)
        if not sensitivity.success:
            raise RuntimeError(sensitivity.message)
        initial_cotangent = sensitivity.y[:initial.size, -1]
        weight_gradient = sensitivity.y[initial.size:, -1].reshape(weights.shape)
    result.update({
        'state': np.asarray(field.final_state(final), dtype=np.complex128),
        'log_density': np.asarray(final[-1], dtype=np.float64),
        'weight_gradient': np.asarray(weight_gradient, dtype=np.float64),
        'initial_gradient': np.asarray(field.initial_gradient(
            links, initial_cotangent), dtype=np.complex128),
    })
    return result


if __name__ == '__main__':
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        result = solve(dict(archive))
    np.savez(sys.argv[2], **result)
