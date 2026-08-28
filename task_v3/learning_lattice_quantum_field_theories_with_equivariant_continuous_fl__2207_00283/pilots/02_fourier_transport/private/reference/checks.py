"""Independent small-case identities; never shipped to participants."""

from itertools import product
from pathlib import Path

import numpy as np

from .official import SpectrumScaling, jax, jnp, solve


def run_checks(inputs, outputs):
    spatial = tuple(map(int, inputs["spatial_shape"]))
    channels = tuple(map(int, inputs["channel_shape"]))
    batch = tuple(map(int, inputs["batch_shape"]))
    reduced = spatial[:-1] + (spatial[-1] // 2 + 1,)
    axes = tuple(range(len(batch), len(batch) + len(spatial)))
    mask_real = np.ones(reduced, dtype=bool)
    mask_imag = np.ones(reduced, dtype=bool)
    for index in np.ndindex(reduced):
        partner = tuple((-coordinate) % length for coordinate, length in zip(index, spatial))
        independent = partner[-1] >= reduced[-1] or index <= partner
        mask_real[index] = independent
        mask_imag[index] = independent and index != partner
    np.testing.assert_array_equal(outputs["mr"], mask_real)
    np.testing.assert_array_equal(outputs["mi"], mask_imag)
    assert int(mask_real.sum() + mask_imag.sum()) == int(np.prod(spatial))
    transformed = np.fft.rfftn(inputs["x"], s=spatial, axes=axes, norm="ortho")
    decoded_fft = np.fft.rfftn(outputs["unpacked"], s=spatial, axes=axes, norm="ortho")
    np.testing.assert_allclose(decoded_fft, outputs["unpacked_rfft"], atol=2e-12)
    for batch_index in product(*(range(length) for length in batch)):
        for channel_index in product(*(range(length) for length in channels)):
            event_index = batch_index + (slice(None),) * len(spatial) + channel_index
            packed_index = batch_index + (slice(None),) + channel_index
            values = transformed[event_index]
            oracle = np.concatenate((values.real[mask_real], values.imag[mask_imag]))
            np.testing.assert_allclose(outputs["packed"][packed_index], oracle, atol=2e-12)
            decoded = decoded_fft[event_index]
            encoded = np.concatenate((decoded.real[mask_real], decoded.imag[mask_imag]))
            np.testing.assert_allclose(encoded, inputs["q"][packed_index], atol=2e-12)
    for probe_index, probe in enumerate(inputs["probes"]):
        residuals = [0.0]
        for index in np.ndindex(reduced):
            partner = tuple((-coordinate) % length for coordinate, length in zip(index, spatial))
            if index == partner:
                residuals.append(float(np.max(np.abs(probe[index].imag))))
            elif partner[-1] < reduced[-1]:
                residuals.append(float(np.max(np.abs(probe[index] - probe[partner].conj()))))
        np.testing.assert_allclose(outputs["asymmetry"][probe_index], max(residuals), atol=1e-12)

    def transform(field, parameters, density, reverse=False):
        exponent = jnp.tensordot(parameters, inputs["amplitude"] + 1j * inputs["phase"], axes=1)
        spectrum = inputs["base"] * jnp.exp(exponent)
        operation = SpectrumScaling(spectrum, channel_dim=len(channels), space_dim=len(spatial))
        return operation.apply(field, density, reverse=reverse)

    field = jnp.asarray(inputs["x"])
    parameters = jnp.asarray(inputs["theta"])
    density = jnp.asarray(inputs["log_density"])
    reverse, restored_density = transform(outputs["y"], parameters, outputs["log_density_y"], True)
    np.testing.assert_allclose(reverse, field, atol=2e-12)
    np.testing.assert_allclose(restored_density, density, atol=2e-12)
    assert not batch
    dense = jax.jacfwd(lambda flat: transform(flat.reshape(field.shape), parameters, density)[0].ravel())(field.ravel())
    determinant = np.linalg.slogdet(np.asarray(dense))[1]
    np.testing.assert_allclose(density - outputs["log_density_y"], determinant, atol=2e-11)
    oracle_grad_x = np.asarray(dense).T @ inputs["cotangent"].ravel() / np.sqrt(field.size)
    np.testing.assert_allclose(outputs["grad_x"].ravel(), oracle_grad_x, atol=2e-12)
    step = 2e-5
    plus = transform(field + step * inputs["direction_x"],
                     parameters + step * inputs["direction_theta"],
                     density + step * inputs["direction_log_density"])
    minus = transform(field - step * inputs["direction_x"],
                      parameters - step * inputs["direction_theta"],
                      density - step * inputs["direction_log_density"])
    np.testing.assert_allclose(outputs["jvp_y"], (plus[0] - minus[0]) / (2 * step), atol=1e-8, rtol=1e-8)
    np.testing.assert_allclose(outputs["jvp_log_density"], (plus[1] - minus[1]) / (2 * step), atol=1e-8)
    event_size = int(np.prod(spatial + channels))

    def objective(parameters):
        transported, transported_density = transform(field, parameters, density)
        return float(jnp.sum(inputs["cotangent"] * transported) / np.sqrt(field.size)
                     + jnp.mean(transported_density) / event_size)

    for parameter_index in range(len(parameters)):
        direction = np.eye(len(parameters))[parameter_index] * step
        estimate = (objective(parameters + direction) - objective(parameters - direction)) / (2 * step)
        np.testing.assert_allclose(outputs["grad_theta"][parameter_index], estimate, atol=1e-8, rtol=1e-8)
    indices = np.moveaxis(np.indices(reduced), 0, -1)
    folded = np.where(2 * indices > np.asarray(spatial), indices - np.asarray(spatial), indices)
    expected_momenta = 2 * np.pi * folded / np.asarray(spatial)
    np.testing.assert_allclose(outputs["momenta"], expected_momenta, atol=2e-12)
    np.testing.assert_allclose(outputs["lattice_momenta"], 2 * np.sin(expected_momenta / 2), atol=2e-12)
    np.testing.assert_array_equal(outputs["shell_squared"], np.sum(folded**2, axis=-1))
    return {"packing_and_independent_decode": "passed", "symmetry_oracle": "passed",
            "inverse_and_density": "passed", "dense_logdet_and_adjoint": "passed",
            "jvp_and_parameter_finite_differences": "passed", "physical_momenta": "passed"}


if __name__ == "__main__":
    sample = Path(__file__).resolve().parents[2] / "participant/input/example_2d.npz"
    with np.load(sample, allow_pickle=False) as archive:
        inputs = dict(archive)
    print(run_checks(inputs, solve(inputs)))
