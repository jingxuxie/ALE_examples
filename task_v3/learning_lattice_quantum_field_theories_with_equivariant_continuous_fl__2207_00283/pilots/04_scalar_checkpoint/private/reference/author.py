from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import partial
import json
import os
from pathlib import Path
import resource
import sys
import time

os.sched_setaffinity(0, {int(core) for core in os.environ.get("ALE_REFERENCE_CORES", "40,41,42,43").split(",")})
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "4"
os.environ["JAX_ENABLE_X64"] = "true"
os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["XLA_FLAGS"] = "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=4"

import numpy as np
import jax
import jax.numpy as jnp
import haiku as hk
from flax import nnx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "vendor"))
from jaxlft import cnf, convolution
import later_conv


def load_model(name):
    with np.load(ROOT / "participant" / "input" / "checkpoints" / (name + ".npz"), allow_pickle=False) as data:
        params = {"~": {key: jnp.asarray(data[key], dtype=jnp.float64) for key in ("w", "time_superpos", "freq_superpos", "phi_freq")}}
        if "width_factor" in data:
            params["kernel_gauss"] = {"width_factor": jnp.asarray(data["width_factor"], dtype=jnp.float64)}
        orbits = data["orbits"].copy()
    return params, orbits


def transfer_map(orbits, size):
    support = tuple(length + 1 for length in orbits.shape)
    labels = (orbits + 1).astype(np.float64)[..., None, None]
    weights = np.ones_like(labels)
    lifted_labels = convolution.pad_kernel_weights(labels, support)
    lifted_weights = convolution.pad_kernel_weights(weights, support)
    shifted_labels = later_conv.resize_kernel_weights(lifted_labels, (size, size))[..., 0, 0]
    factors = later_conv.resize_kernel_weights(lifted_weights, (size, size))[..., 0, 0]
    indices = np.rint(shifted_labels / np.where(factors > 0, factors, 1)).astype(np.int32) - 1
    return jnp.asarray(np.maximum(indices, 0)), jnp.asarray(factors)


@contextmanager
def backend(orbits, size, profile):
    original = convolution.apply_equiv_conv
    capture = []
    if profile == "transfer":
        indices, factors = transfer_map(orbits, size)
        layer = later_conv.ConvSym(20, 1, kernel_size=(size, size), orbit_function=None,
                                   use_bias=False, param_dtype=jnp.float64, dtype=jnp.float64, rngs=nnx.Rngs(0))

    def apply(inputs, weights, config, **kwargs):
        if profile == "native":
            kernel = weights[config.orbits]
            output = original(inputs, weights, config, **kwargs)
        else:
            kernel = weights[indices] * factors[..., None, None]
            output = layer(inputs, kernel_params=kernel.reshape(-1, 20, 1))
        capture.append(kernel[..., 0])
        return output

    convolution.apply_equiv_conv = apply
    try:
        yield capture
    finally:
        convolution.apply_equiv_conv = original


def evaluate(request, steps=100, repeat=False, frozen=False):
    model_name = str(request["model"])
    conditional = model_name.startswith("range")
    params, orbits = load_model(model_name)
    phi = jnp.asarray(request["phi"], dtype=jnp.float64)
    logp = jnp.asarray(request["logp"], dtype=jnp.float64)
    lam = jnp.asarray(request["lam"], dtype=jnp.float64)
    instant = jnp.asarray(request["t"], dtype=jnp.float64)
    operation, profile = str(request["operation"]), str(request["profile"])
    with backend(orbits, phi.shape[-1], profile) as capture:
        def body(fields, density, coupling):
            kwargs = {"kernel_shape": orbits.shape, "int_steps": steps}
            model = cnf.Phi4CNFConditional(lam_kernel_base=partial(cnf.KernelGauss, minmax=(4., 6.)), **kwargs) if conditional else cnf.Phi4CNF(**kwargs)
            extra = {"lam": jnp.asarray(5.) if frozen else coupling} if conditional else {}
            if operation == "probe":
                velocity, negative_divergence = model.vector_field((fields, density), instant, **extra)
                return velocity, -negative_divergence, capture[-1]
            forward, reverse = model()
            return (forward if operation == "forward" else reverse)(fields, density, **extra)

        apply = hk.without_apply_rng(hk.transform(body)).apply

        def scalar(fields, density, coupling):
            return apply(params, fields, density, coupling)

        def calculate(fields, density, coupling):
            if coupling.ndim == 0:
                result = scalar(fields, density, coupling)
                if operation == "probe":
                    result = result[0], result[1], jnp.broadcast_to(result[2], (len(fields),) + result[2].shape)
                return result

            def row(field, probability, value):
                result = scalar(field[None], probability[None], value)
                return (result[0][0], result[1][0], result[2]) if operation == "probe" else (result[0][0], result[1][0])

            return jax.vmap(row)(fields, density, coupling)

        def execute(fields, density, coupling):
            if operation == "probe" and conditional:
                result, tangent = jax.jvp(lambda value: calculate(fields, density, value), (coupling,), (jnp.ones_like(coupling),))
                return dict(velocity=result[0], divergence=result[1], kernel=result[2], dlam_velocity=tangent[0], dlam_divergence=tangent[1])
            result = calculate(fields, density, coupling)
            if operation == "probe":
                return dict(velocity=result[0], divergence=result[1], kernel=result[2])
            return dict(phi=result[0], logp=result[1])

        execute = jax.jit(execute)
        started = time.perf_counter()
        output = jax.block_until_ready(execute(phi, logp, lam))
        cold = time.perf_counter() - started
        warm = None
        if repeat:
            started = time.perf_counter()
            jax.block_until_ready(execute(phi, logp, lam))
            warm = time.perf_counter() - started
    result = {key: np.asarray(value) for key, value in output.items()}
    metrics = dict(cold_compute_seconds=cold, warm_compute_seconds=warm, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   jax=jax.__version__, haiku=hk.__version__, cores=sorted(os.sched_getaffinity(0)), threads=4, steps=steps)
    return result, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--repeat", action="store_true")
    parser.add_argument("--frozen", action="store_true")
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as data:
        request = dict(data)
    output, metrics = evaluate(request, args.steps, args.repeat, args.frozen)
    np.savez(args.output, **output)
    if args.metrics:
        args.metrics.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
