import os
os.environ.setdefault('JAX_ENABLE_X64', 'true')
os.environ.setdefault('JAX_PLATFORMS', 'cpu')
import sys
import time
import json
import resource
from pathlib import Path
import numpy as np
import jax
import jax.numpy as jnp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'participant/workspace'))
from potential import potential


@jax.jit
def dense_field(links, weights, generators, time_value):
    coordinates = jnp.zeros(links.shape[:-2] + (len(generators),))

    def at_identity(values):
        algebra = jnp.einsum('...a,aij->...ij', values, generators)
        displaced = (jnp.eye(links.shape[-1]) + algebra + 0.5 * algebra @ algebra) @ links
        return potential(displaced, weights, time_value)

    gradient = jax.grad(at_identity)(coordinates)
    hessian = jax.hessian(at_identity)(coordinates)
    divergence = jnp.trace(hessian.reshape(coordinates.size, coordinates.size))
    vector = jnp.einsum('...a,aij->...ij', gradient, generators)
    return vector, divergence


def main():
    with np.load(sys.argv[1]) as archive:
        data = dict(archive)
    memory_cap = 16 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (memory_cap, memory_cap))
    links, weights, generators = [jnp.asarray(data[name]) for name in ('links', 'weights', 'generators')]
    start = float(data['t0'])
    step_size = (float(data['t1']) - start) / 16
    log_density = 0.0
    began = time.monotonic()
    for index in range(16):
        vector, divergence = dense_field(links, weights, generators, start + index * step_size)
        vector.block_until_ready()
        log_density -= step_size * float(divergence)
        links = jax.scipy.linalg.expm(step_size * vector) @ links
        links.block_until_ready()
        print(json.dumps({'step': index + 1, 'seconds': time.monotonic() - began,
                          'divergence': float(divergence), 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)
    np.savez(sys.argv[2], state=np.asarray(links), log_density=log_density)


if __name__ == '__main__':
    main()
