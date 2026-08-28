import os
os.environ.setdefault('JAX_ENABLE_X64', 'true')
os.environ.setdefault('JAX_PLATFORMS', 'cpu')
import sys
from pathlib import Path
from functools import partial
import numpy as np
import jax
import jax.numpy as jnp

PILOT = Path(__file__).resolve().parents[2]
ROOT = PILOT.parents[1]
sys.path.insert(0, str(ROOT / 'private/sources/bijx/src'))
sys.path.insert(0, str(PILOT / 'participant/workspace'))
from bijx import cg, lie
from potential import potential, local_potential, loops, PATHS


def trivialized_gradient(ambient, links, generators):
    components = jnp.einsum('...ij,aik,...kj->...a', ambient, generators, links).real
    return jnp.einsum('...a,aij->...ij', components, generators)


def vector_divergence(time, links, weights, generators):
    ambient = jax.grad(potential)(links, weights, time)
    vector = trivialized_gradient(ambient, links, generators)
    divergence = jnp.array(0.0)
    for path, matrix, coefficients in zip(PATHS, loops(links), weights):
        function = lambda value: local_potential(value, coefficients, time)
        local_laplacian = lambda value: lie.value_grad_divergence(function, value, generators)[2]
        divergence = divergence + len(path) * jax.vmap(local_laplacian)(matrix.reshape((-1,) + matrix.shape[-2:])).sum()
    return vector, divergence


def integrate(links, weights, generators, start, stop, steps):
    manifold = (cg.Matrix(), cg.Euclidean())
    step_size = (stop - start) / steps

    def field(time, state):
        vector, divergence = vector_divergence(time, state[0], weights, generators)
        return vector, -divergence

    def step(state, index):
        time = start + index * step_size
        result = cg.crouch_grossmann_step(manifold, cg.CG3, field, step_size, time, state)
        return result, None

    initial = (links, jnp.array(0.0))
    return jax.lax.scan(jax.checkpoint(step), initial, jnp.arange(steps))[0]


@partial(jax.jit, static_argnames=('steps',))
def compute(links, weights, generators, start, stop, probe, density_weight, steps=256):
    def objective(initial, coefficients):
        final, log_density = integrate(initial, coefficients, generators, start, stop, steps)
        value = jnp.vdot(probe, final).real + density_weight * log_density
        return value, (final, log_density)

    (_, (state, log_density)), (ambient, weight_gradient) = jax.value_and_grad(objective, argnums=(0, 1), has_aux=True)(links, weights)
    initial_gradient = trivialized_gradient(ambient, links, generators)
    vector, divergence = vector_divergence(start, links, weights, generators)
    return {'vector': vector, 'divergence': divergence, 'state': state,
            'log_density': log_density, 'weight_gradient': weight_gradient,
            'initial_gradient': initial_gradient}


def solve(data, steps=256):
    result = compute(*(jnp.asarray(data[name]) for name in
                       ('links', 'weights', 'generators', 't0', 't1', 'probe', 'density_weight')), steps=steps)
    return {name: np.asarray(value) for name, value in result.items()}


if __name__ == '__main__':
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        result = solve(dict(archive), int(sys.argv[3]) if len(sys.argv) > 3 else 256)
    np.savez(sys.argv[2], **result)
