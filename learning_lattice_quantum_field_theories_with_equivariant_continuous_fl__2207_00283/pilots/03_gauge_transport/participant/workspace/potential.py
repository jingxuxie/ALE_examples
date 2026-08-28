import jax.numpy as jnp


PATHS = ((1, 2, -1, -2), (1, 1, 2, -1, -1, -2), (1, 2, 2, -1, -2, -2))


def loops(links):
    matrices = []
    for path in PATHS:
        position = [0, 0]
        product = jnp.broadcast_to(jnp.eye(links.shape[-1]), links.shape[:2] + links.shape[-2:])
        for edge in path:
            axis = abs(edge) - 1
            if edge < 0:
                position[axis] -= 1
            link = jnp.roll(links[:, :, axis], tuple(-value for value in position), axis=(0, 1))
            if edge < 0:
                link = jnp.swapaxes(link.conj(), -1, -2)
            product = product @ link
            if edge > 0:
                position[axis] += 1
        matrices.append(product)
    return jnp.stack(matrices)


def local_potential(matrix, coefficients, time):
    trace = jnp.trace(matrix, axis1=-2, axis2=-1) / matrix.shape[-1]
    trace_square = jnp.trace(matrix @ matrix, axis1=-2, axis2=-1).real / matrix.shape[-1]
    features = jnp.stack((trace.real, trace.real**2, trace.imag**2, trace_square), axis=-1)
    time_basis = jnp.array((1.0, jnp.sin(2 * jnp.pi * time), jnp.cos(2 * jnp.pi * time)))
    return jnp.sum(features * (time_basis @ coefficients), axis=-1)


def potential(links, weights, time):
    return sum(jnp.sum(local_potential(matrix, coefficients, time)) for matrix, coefficients in zip(loops(links), weights))
