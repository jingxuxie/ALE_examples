import os

os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_ENABLE_COMPILATION_CACHE", "false")
os.environ.setdefault("XLA_FLAGS", "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4")

import jax
import jax.numpy as jnp
import numpy as np

jax.config.update("jax_enable_x64", True)


def sincos(phases):
    quadrant = jnp.rint(phases * (2.0 / np.pi))
    reduced = (phases - quadrant * 1.57079632673412561417) - quadrant * 6.07710050650619224932e-11
    squared = reduced * reduced
    sine_polynomial = (
        -1.66666666666666324348e-1 + squared * (
            8.33333333332248946124e-3 + squared * (
                -1.98412698298579493134e-4 + squared * (
                    2.75573137070700676789e-6 + squared * (
                        -2.50507602534068634195e-8 + squared * 1.58969099521155010221e-10
                    )
                )
            )
        )
    )
    cosine_polynomial = (
        4.16666666666666019037e-2 + squared * (
            -1.38888888888741095749e-3 + squared * (
                2.48015872894767294178e-5 + squared * (
                    -2.75573143513906633035e-7 + squared * (
                        2.08757232129817482790e-9 + squared * -1.13596475577881948265e-11
                    )
                )
            )
        )
    )
    reduced_sine = reduced + reduced * squared * sine_polynomial
    reduced_cosine = (1.0 - 0.5 * squared) + squared * squared * cosine_polynomial
    integer_quadrant = quadrant.astype(jnp.int32)
    odd = (integer_quadrant & 1) != 0
    negative = (integer_quadrant & 2) != 0
    sine = jnp.where(odd, reduced_cosine, reduced_sine)
    cosine = jnp.where(odd, -reduced_sine, reduced_cosine)
    return jnp.where(negative, -sine, sine), jnp.where(negative, -cosine, cosine)


def integrate(model, logp, reverse, steps):
    batch, size = model.batch, model.size
    volume = size * size
    direction = -1 if reverse else 1
    increment = direction / steps

    def projected(fields, matrices, frequencies, center, fast):
        flattened = fields.reshape(batch, volume)
        phases = flattened[:, None, :] * frequencies[None, :, None]
        if fast:
            sine, cosine = sincos(phases)
        else:
            sine, cosine = jnp.sin(phases), jnp.cos(phases)
        features = jnp.concatenate((sine, flattened[:, None, :]), axis=1)
        embedding = (matrices @ features).reshape(batch, 20, size, size)
        divergence = jnp.sum(cosine * frequencies[None, :, None] * center[:, :-1, None], axis=(1, 2))
        divergence += volume * center[:, -1]
        return embedding, divergence

    def rhs(fields, matrices, frequencies, kernel, center):
        arguments = (fields, matrices, frequencies, center)
        embedding, divergence = jax.lax.cond(
            jnp.max(jnp.abs(fields)) * jnp.max(jnp.abs(frequencies)) < 262144.0,
            lambda values: projected(*values, fast=True),
            lambda values: projected(*values, fast=False),
            arguments,
        )
        spectrum = jnp.fft.rfft2(embedding)
        velocity = jnp.fft.irfft2(jnp.sum(spectrum * kernel, axis=1), s=(size, size))
        return velocity, divergence

    @jax.jit
    def run(fields, matrices, frequencies, kernels, centers):
        def step_body(step, state):
            initial_fields, density_change = state
            start = 2 * steps - 2 * step if reverse else 2 * step

            def stage_body(stage, stage_state):
                stage_fields, velocity_sum, divergence_sum = stage_state
                offset = jnp.where(stage == 0, 0, jnp.where(stage == 3, 2, 1))
                index = start + direction * offset
                velocity, divergence = rhs(stage_fields, matrices, frequencies, kernels[index], centers[index])
                weight = jnp.where((stage == 0) | (stage == 3), 1.0, 2.0)
                factor = jnp.where(stage == 2, 1.0, 0.5)
                return (
                    initial_fields + (increment * factor) * velocity,
                    velocity_sum + weight * velocity,
                    divergence_sum + weight * divergence,
                )

            stages = (initial_fields, jnp.zeros_like(initial_fields), jnp.zeros(batch, dtype=jnp.float64))
            _, velocity_sum, divergence_sum = jax.lax.fori_loop(0, 4, stage_body, stages)
            return (
                initial_fields + (increment / 6.0) * velocity_sum,
                density_change - (increment / 6.0) * divergence_sum,
            )

        return jax.lax.fori_loop(0, steps, step_body, (fields, jnp.zeros(batch, dtype=jnp.float64)))

    fields, change = run(
        jnp.asarray(model.phi),
        jnp.asarray(model.feature_matrices),
        jnp.asarray(model.frequencies),
        jnp.asarray(model.grid_kernels),
        jnp.asarray(model.grid_centers),
    )
    return {"phi": np.asarray(fields), "logp": np.asarray(logp, dtype=np.float64) + np.asarray(change)}
