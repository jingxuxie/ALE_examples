"""Prepare exactly two private, fixture-free numerical accelerations."""

import hashlib
import json
from pathlib import Path
import subprocess


SIDECAR = Path(__file__).resolve().parent
ROOT = SIDECAR.parents[1]


FACTORED_CONVOLUTION = '''    def convolve(self, values, parity):
        self.calls += 1
        if parity == 1:
            transformed = dct(values, type=2, n=self.transform_length, workers=1)
            kernels = self.kernel_fft[:, :-1]
        else:
            transformed = dst(values, type=2, n=self.transform_length, workers=1)
            kernels = self.kernel_fft[:, 1:]
        combined = np.zeros_like(transformed)
        for matrix, kernel in zip(self.weighted_coupling, kernels):
            combined += (matrix @ transformed) * kernel[None, :]
        if parity == 1:
            return idct(combined, type=2, workers=1)[:, :self.n_freq]
        return idst(combined, type=2, workers=1)[:, :self.n_freq]

'''


EIGENMODE_INITIALIZER = '''def eigenmode_initial(model, initial):
    count = model.n_freq
    positions = np.arange(count)
    distances = 2 * model.prefactor * np.arange(2 * count)
    normal = np.zeros(model.shape)
    for energy, matrix in zip(model.omega, model.weighted_coupling):
        prefix = np.cumsum(energy ** 2 / (energy ** 2 + distances ** 2))
        difference = 2 * prefix[positions] + prefix[count - 1 - positions] - prefix[count + positions] - 1
        normal += matrix.sum(axis=1)[:, None] * difference[None, :]
    normal_z = 1 + model.prefactor * normal / model.frequencies[None, :]
    inner = np.sqrt(model.weights[:, None] * normal_z / model.frequencies[None, :])

    def linear_pairing(vector):
        delta = vector.reshape(model.shape) / inner
        ratio = delta / model.frequencies[None, :]
        pairing = model.convolve(ratio, 1)
        pairing -= 2 * (model.weighted_coulomb @ ratio.sum(axis=1))[:, None]
        return (inner * model.prefactor * pairing / normal_z).ravel()

    operator = LinearOperator((initial.size, initial.size), matvec=linear_pairing, dtype=np.float64)
    eigenvalues, eigenvectors = eigsh(operator, k=1, which="LA", ncv=8, tol=2e-10,
                                     maxiter=80, v0=(initial * inner).ravel())
    eigenvalue = float(eigenvalues[0])
    mode = eigenvectors[:, 0].reshape(model.shape) / inner
    if np.dot(model.weights, mode[:, 0]) < 0:
        mode = -mode
    mode /= np.max(np.abs(mode))
    if eigenvalue <= 1:
        return initial
    projected_weight = inner ** 2 * mode
    norm = np.sum(projected_weight * mode)
    amplitude = 0.1 * model.prefactor
    for iteration in range(2):
        mapped = model.map(amplitude * mode)[1] / amplitude
        defect = np.sum(projected_weight * (mode - mapped)) / norm
        nonlinear = max(defect + eigenvalue - 1, 1e-15)
        amplitude *= np.clip(np.sqrt((eigenvalue - 1) / nonlinear), 0.01, 100)
    return amplitude * mode


'''


SELF_CHECK = '''import argparse
import os
import sys
import numpy as np
from solve import Model

sys.path.insert(0, os.environ["ALE_PUBLIC_INPUT"])
from eliashberg import Model as PublicModel

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
arguments = parser.parse_args()
with np.load(arguments.input, allow_pickle=False) as archive:
    instance = {name: archive[name] for name in archive.files}
delta = instance["initial_delta"]
model = Model(instance)
public = PublicModel(instance)
actual_z, actual_map = model.map(delta)
expected_z, expected_map = public.map(delta)
np.testing.assert_allclose(actual_z, expected_z, rtol=3e-12, atol=3e-12)
np.testing.assert_allclose(actual_map, expected_map, rtol=3e-12, atol=3e-12)
direction = np.random.default_rng(19375).normal(size=delta.shape)
np.testing.assert_allclose(model.linearize(delta, actual_z, actual_map)(direction),
                           public.linearize(delta)(direction), rtol=3e-11, atol=3e-11)
np.savez(arguments.output, delta=actual_map, z=actual_z)
'''


def main():
    source = ROOT / "champions" / "generation_1" / "solve.py"
    original = source.read_text()
    factored = original.replace('        self.spectral = np.ascontiguousarray(np.einsum(\n            "sab,sk->abk", self.weighted_coupling, self.kernel_fft, optimize=True))\n', '')
    start = factored.index("    def convolve(")
    end = factored.index("    def map(", start)
    factored = factored[:start] + FACTORED_CONVOLUTION + factored[end:]
    seeded = factored.replace("LinearOperator, gmres", "LinearOperator, eigsh, gmres")
    seeded = seeded.replace("def solve(instance):", EIGENMODE_INITIALIZER + "def solve(instance):")
    seeded = seeded.replace('    for iteration in range(10):\n',
                            '    large_grid = model.n_freq >= 4096\n    if large_grid:\n        delta = eigenmode_initial(model, delta)\n    for iteration in range(0 if large_grid else 10):\n', 1)
    seeded = seeded.replace("if error < 2e-12 and last_step < 2e-7:", "if error < 1e-10 and last_step < 2e-6:")
    seal_path = ROOT / "evaluator" / "hidden" / "prelaunch_seal.json"
    seal = json.loads(seal_path.read_text())
    mismatches = [name for name, expected in seal["files"].items()
                  if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not mismatches, mismatches
    protocol = {"cpu_budget_seconds_total": 900, "candidate_count_max": 2,
                "active_seal_sha256": hashlib.sha256(seal_path.read_bytes()).hexdigest(),
                "active_sealed_files": seal["files"],
                "source_fresh_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "candidate_1": "Exact mode-factorized DCT/DST convolution, same nonlinear iteration",
                "candidate_2": "Candidate 1 plus normal-state eigenmode and projected nonlinear amplitude warm start on long grids",
                "candidate_inputs": "Only the seven public instance arrays; no labels, references, case IDs, or lookup data",
                "resources": {"cpu_seconds": 12, "memory_mb": 2048, "threads": 1},
                "activation_or_fresh_launch_authorized": False}
    files = {SIDECAR / "candidate_1" / "solve.py": factored,
             SIDECAR / "candidate_2" / "solve.py": seeded,
             SIDECAR / "candidate_1" / "self_check.py": SELF_CHECK,
             SIDECAR / "protocol.json": json.dumps(protocol, indent=2) + "\n"}
    patch = "*** Begin Patch\n"
    for path, text in files.items():
        if path.exists():
            raise FileExistsError(path)
        patch += "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines())
    subprocess.run(["apply_patch"], input=patch + "*** End Patch\n", text=True, check=True)
    print(json.dumps({"prepared_candidates": 2, "active_seal_verified": len(seal["files"])}))


if __name__ == "__main__":
    main()
