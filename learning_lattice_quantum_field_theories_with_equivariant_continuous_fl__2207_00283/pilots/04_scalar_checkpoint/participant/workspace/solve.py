from __future__ import annotations

import os
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import solve_ivp


def dense_probe(phi, instant, params):
    batch, size, _ = phi.shape
    frequencies = params["phi_freq"]
    angle = 2 * np.pi * np.arange(1, 11) * instant
    time_features = np.concatenate((np.sin(angle), np.cos(angle), [1.]))
    time_mix = (params["time_superpos"] / 21) @ time_features
    feature_mix = params["freq_superpos"] / 50
    kernel = (params["w"] @ time_mix)[params["orbits"]]
    fields = phi.reshape(batch, size * size)
    phases = fields[..., None] * frequencies
    features = np.concatenate((np.sin(phases), fields[..., None]), axis=-1) @ feature_mix.T
    derivatives = np.concatenate((np.cos(phases) * frequencies, np.ones_like(fields[..., None])), axis=-1) @ feature_mix.T
    coordinates = np.indices((size, size), dtype=np.int32).reshape(2, -1)
    row_displacements = (coordinates[0][None, :] - coordinates[0][:, None] + size // 2) % size
    col_displacements = (coordinates[1][None, :] - coordinates[1][:, None] + size // 2) % size
    velocity = np.zeros_like(fields)
    jacobian = np.zeros((batch, size * size, size * size))
    for channel in range(20):
        matrix = kernel[row_displacements, col_displacements, channel]
        velocity += features[..., channel] @ matrix.T
        jacobian += matrix[None] * derivatives[:, None, :, channel]
    return dict(velocity=velocity.reshape(phi.shape), divergence=np.trace(jacobian, axis1=1, axis2=2),
                kernel=np.broadcast_to(kernel, (batch,) + kernel.shape))


def solve(request):
    name = str(request["model"])
    if name.startswith("range") or str(request["profile"]) != "native":
        raise NotImplementedError("Implement the conditional contraction and transfer profile from SPEC.md.")
    root = Path(os.environ.get("ALE_INPUT_DIR", Path(__file__).resolve().parents[1] / "input"))
    with np.load(root / "checkpoints" / (name + ".npz"), allow_pickle=False) as data:
        params = {key: data[key].astype(np.float64) if data[key].dtype.kind == "f" else data[key] for key in data.files}
    phi, logp = request["phi"], request["logp"]
    operation = str(request["operation"])
    if operation == "probe":
        return dense_probe(phi, float(request["t"]), params)
    span = (0., 1.) if operation == "forward" else (1., 0.)
    initial = np.concatenate((phi.ravel(), logp))

    def derivative(instant, state):
        fields = state[:phi.size].reshape(phi.shape)
        probe = dense_probe(fields, instant, params)
        return np.concatenate((probe["velocity"].ravel(), -probe["divergence"]))

    result = solve_ivp(derivative, span, initial, rtol=1e-7, atol=1e-9)
    if not result.success:
        raise RuntimeError(result.message)
    return dict(phi=result.y[:phi.size, -1].reshape(phi.shape), logp=result.y[phi.size:, -1])


if __name__ == "__main__":
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        request = dict(archive)
    np.savez(sys.argv[2], **solve(request))
