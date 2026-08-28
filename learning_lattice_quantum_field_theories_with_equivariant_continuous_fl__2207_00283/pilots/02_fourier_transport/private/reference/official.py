"""Private adapter around the retained official numerical implementations."""

import hashlib
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np


SOURCE = Path(os.environ.get("BIJX_SOURCE", Path(__file__).resolve().parents[4]
                             / "private/sources/bijx"))
FAST_SOURCE = Path("/tmp/ale_bijx")
NUMERICAL_FILES = ("src/bijx/fourier.py", "src/bijx/bijections/fourier.py",
                   "src/bijx/bijections/affine_complex.py", "src/bijx/utils.py")
if "BIJX_SOURCE" not in os.environ and FAST_SOURCE.is_dir():
    if all((FAST_SOURCE / relative).is_file() and
           hashlib.sha256((FAST_SOURCE / relative).read_bytes()).digest() ==
           hashlib.sha256((SOURCE / relative).read_bytes()).digest()
           for relative in NUMERICAL_FILES):
        SOURCE = FAST_SOURCE
sys.path.insert(0, str(SOURCE / "src"))

import jax
import jax.numpy as jnp
from bijx.bijections.fourier import SpectrumScaling
from bijx.fourier import FFTRep, FourierData, FourierMeta, fft_momenta, spectrum_asymmetry

jax.config.update("jax_enable_x64", True)


def solve(inputs):
    spatial = tuple(map(int, inputs["spatial_shape"]))
    channels = tuple(map(int, inputs["channel_shape"]))
    batch = tuple(map(int, inputs["batch_shape"]))
    space_axes = tuple(range(len(batch), len(batch) + len(spatial)))
    tail_axes = tuple(range(-len(spatial), 0))
    meta = FourierMeta.create(spatial)
    moved_x = jnp.moveaxis(jnp.asarray(inputs["x"]), space_axes, tail_axes)
    packed = FourierData.from_real(moved_x, spatial, to=FFTRep.comp_real).data
    moved_q = jnp.moveaxis(jnp.asarray(inputs["q"]), len(batch), -1)
    decoded = FourierData(moved_q, FFTRep.comp_real, meta)
    outputs = {
        "packed": jnp.moveaxis(packed, -1, len(batch)),
        "unpacked": jnp.moveaxis(decoded.to(FFTRep.real_space).data, tail_axes, space_axes),
        "unpacked_rfft": jnp.moveaxis(decoded.to(FFTRep.rfft).data, tail_axes, space_axes),
        "mr": meta.mr,
        "mi": meta.mi,
        "momenta": fft_momenta(spatial),
        "lattice_momenta": fft_momenta(spatial, lattice=True),
        "shell_squared": meta.ks_full,
    }
    spectrum_channels = len(channels) if inputs["base"].ndim > len(spatial) else 0
    outputs["asymmetry"] = jnp.stack([
        spectrum_asymmetry(probe, spatial, spectrum_channels)
        for probe in inputs["probes"]
    ])
    base = jnp.asarray(inputs["base"])
    amplitude = jnp.asarray(inputs["amplitude"])
    phase = jnp.asarray(inputs["phase"])

    def transform(field, parameters, density, reverse=False):
        exponent = jnp.tensordot(parameters, amplitude + 1j * phase, axes=1)
        spectrum = base * jnp.exp(exponent)
        bijection = SpectrumScaling(spectrum, channel_dim=len(channels), space_dim=len(spatial))
        return bijection.apply(field, density, reverse=reverse)

    field = jnp.asarray(inputs["x"])
    parameters = jnp.asarray(inputs["theta"])
    density = jnp.asarray(inputs["log_density"])
    forward = jax.jit(transform)
    outputs["y"], outputs["log_density_y"] = forward(field, parameters, density)
    outputs["reverse_y"], outputs["reverse_log_density"] = jax.jit(
        lambda field, parameters, density: transform(field, parameters, density, True)
    )(field, parameters, density)
    _, tangent = jax.jvp(
        forward, (field, parameters, density),
        tuple(jnp.asarray(inputs[key]) for key in
              ("direction_x", "direction_theta", "direction_log_density")),
    )
    outputs["jvp_y"], outputs["jvp_log_density"] = tangent
    cotangent = jnp.asarray(inputs["cotangent"])
    event_size = int(np.prod(spatial + channels))

    def objective(field, parameters):
        transported, transported_density = forward(field, parameters, density)
        return (jnp.sum(cotangent * transported) / np.sqrt(field.size)
                + jnp.mean(transported_density) / event_size)

    outputs["grad_x"], outputs["grad_theta"] = jax.jit(
        jax.grad(objective, argnums=(0, 1))
    )(field, parameters)
    return {key: np.asarray(value) for key, value in outputs.items()}
