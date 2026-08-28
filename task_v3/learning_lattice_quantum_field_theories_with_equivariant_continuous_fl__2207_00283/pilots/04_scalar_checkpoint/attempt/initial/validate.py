import os
import sys
import time
from pathlib import Path

import numpy as np

import solve


ROOT = solve.input_directory()
RNG = np.random.default_rng(1776)


class Reference:
    def __init__(self, request):
        self.request = request
        self.size = request["phi"].shape[-1]
        self.batch = request["phi"].shape[0]
        with np.load(ROOT / "checkpoints" / (str(request["model"]) + ".npz"), allow_pickle=False) as archive:
            params = {key: np.asarray(archive[key], dtype=np.float64) for key in archive.files}
        self.frequencies = params["phi_freq"]
        self.matrices = []
        self.temporal = []
        self.weights = []
        for coupling in np.broadcast_to(request["lam"], (self.batch,)):
            if str(request["model"]) == "range-L32":
                centers = np.linspace(0.0, 1.0, 50)
                beta = np.log1p(np.exp(params["width_factor"])) * 49.0
                gaussian = np.exp(-beta * ((coupling - 4.0) * 0.5 - centers) ** 2)
                gaussian /= np.sum(gaussian)
                self.matrices.append(np.einsum("cfl,l->cf", params["freq_superpos"], gaussian) / 300.0)
                self.temporal.append(np.einsum("dkl,l->dk", params["time_superpos"], gaussian) / 21.0)
                self.weights.append(np.einsum("ocdl,l->ocd", params["w"].reshape(-1, 20, 20, 50), gaussian))
            else:
                self.matrices.append(params["freq_superpos"] / 50.0)
                self.temporal.append(params["time_superpos"] / 21.0)
                self.weights.append(params["w"])
        source = params["orbits"].shape[0]
        self.origin = source // 2 if str(request["profile"]) == "native" else (self.size - 1) // 2
        self.map = np.zeros((self.size, self.size), dtype=np.int32)
        self.scales = np.zeros((self.size, self.size), dtype=np.float64)
        for row in range(source):
            row_displacements = [row - source // 2]
            if str(request["profile"]) == "transfer" and row == 0:
                row_displacements.append(source // 2)
            for column in range(source):
                column_displacements = [column - source // 2]
                if str(request["profile"]) == "transfer" and column == 0:
                    column_displacements.append(source // 2)
                for row_displacement in row_displacements:
                    for column_displacement in column_displacements:
                        target = ((row_displacement + self.origin) % self.size,
                                  (column_displacement + self.origin) % self.size)
                        self.map[target] = int(params["orbits"][row, column])
                        self.scales[target] += 1.0 / (len(row_displacements) * len(column_displacements))
        self.zero_orbit = int(params["orbits"][source // 2, source // 2])
        self.source_orbits = params["orbits"].astype(np.int32)

    def coefficients(self, row, instant):
        angles = 2.0 * np.pi * instant * np.arange(1, 11)
        temporal = self.temporal[row] @ np.concatenate((np.sin(angles), np.cos(angles), [1.0]))
        return np.einsum("ocd,d->oc", self.weights[row], temporal)

    def probe(self, fields, instant, direct=False):
        velocities = []
        divergences = []
        kernels = []
        for row in range(self.batch):
            coefficients = self.coefficients(row, instant)
            kernel = coefficients[self.map] * self.scales[..., None]
            phase = fields[row, ..., None] * self.frequencies
            features = np.concatenate((np.sin(phase), fields[row, ..., None]), axis=-1)
            embedded = features @ self.matrices[row].T
            centered = np.roll(kernel, (-self.origin, -self.origin), axis=(0, 1))
            spectrum = np.conj(np.fft.rfft2(centered, axes=(0, 1)))
            spectrum *= np.fft.rfft2(embedded, axes=(0, 1))
            velocity = np.fft.irfft2(np.sum(spectrum, axis=-1), s=(self.size, self.size))
            central = self.matrices[row].T @ kernel[self.origin, self.origin]
            divergence = np.sum(np.cos(phase) * self.frequencies * central[:-1]) + self.size ** 2 * central[-1]
            if direct:
                indices = np.arange(self.size)
                for location in [(0, 0), (1, 2), (self.size // 2, 0), (self.size - 1, self.size - 2)]:
                    row_indices = (location[0] + indices - self.origin) % self.size
                    column_indices = (location[1] + indices - self.origin) % self.size
                    expected = np.sum(kernel * embedded[row_indices[:, None], column_indices[None, :]])
                    np.testing.assert_allclose(velocity[location], expected, rtol=2e-12, atol=2e-12)
            np.testing.assert_allclose(kernel.sum(axis=(0, 1)), coefficients[self.source_orbits].sum(axis=(0, 1)), rtol=2e-12, atol=2e-12)
            velocities.append(velocity)
            divergences.append(divergence)
            kernels.append(kernel)
        return dict(velocity=np.array(velocities), divergence=np.array(divergences), kernel=np.array(kernels))

    def transport(self, reverse=False):
        fields = self.request["phi"].copy()
        density = self.request["logp"].copy()
        increment = -0.01 if reverse else 0.01
        for step in range(100):
            instant = 1.0 - step / 100.0 if reverse else step / 100.0
            first = self.probe(fields, instant)
            second = self.probe(fields + 0.5 * increment * first["velocity"], instant + 0.5 * increment)
            third = self.probe(fields + 0.5 * increment * second["velocity"], instant + 0.5 * increment)
            fourth = self.probe(fields + increment * third["velocity"], instant + increment)
            fields += increment / 6.0 * (first["velocity"] + 2.0 * second["velocity"] + 2.0 * third["velocity"] + fourth["velocity"])
            density -= increment / 6.0 * (first["divergence"] + 2.0 * second["divergence"] + 2.0 * third["divergence"] + fourth["divergence"])
        return dict(phi=fields, logp=density)


def request(name, size, profile, couplings, batch=2, instant=0.173):
    return dict(model=np.array(name), profile=np.array(profile), operation=np.array("probe"),
                phi=RNG.normal(size=(batch, size, size)), logp=np.arange(batch, dtype=np.float64) - 31.0,
                t=np.array(instant), lam=np.array(couplings))


def compare(actual, expected, label, tolerance=3e-11):
    for key in expected:
        assert actual[key].shape == expected[key].shape
        assert actual[key].dtype == np.float64
        assert np.isfinite(actual[key]).all()
        np.testing.assert_allclose(actual[key], expected[key], rtol=tolerance, atol=tolerance, err_msg=label + " " + key)
    print("PASS", label, {key: float(np.max(np.abs(actual[key] - expected[key]))) for key in expected}, flush=True)


def main():
    started = time.perf_counter()
    midpoint = 4.0 + 2.0 * 17.5 / 49.0
    cases = [
        request("single-L32", 32, "native", 4.572),
        request("single-L64", 64, "native", 4.398, batch=1, instant=1.0),
        request("range-L32", 32, "native", [4.0, 6.0], instant=0.0),
        request("range-L32", 33, "transfer", [midpoint - 1e-5, midpoint + 1e-5]),
        request("range-L32", 34, "transfer", [4.0, 6.0]),
        request("single-L32", 47, "transfer", 4.572),
        request("range-L32", 63, "transfer", 5.0),
        request("range-L32", 64, "transfer", [4.4, 5.6]),
    ]
    for case in cases:
        label = str(case["model"]) + "/" + str(case["profile"]) + "/" + str(case["phi"].shape[-1])
        reference = Reference(case)
        actual = solve.solve(case)
        expected = reference.probe(case["phi"], float(case["t"]), direct=True)
        compare(actual, expected, "probe " + label)
        if str(case["model"]) == "range-L32":
            delta = 1e-5
            plus = Reference(dict(case, lam=case["lam"] + delta)).probe(case["phi"], float(case["t"]))
            minus = Reference(dict(case, lam=case["lam"] - delta)).probe(case["phi"], float(case["t"]))
            for key in ("velocity", "divergence"):
                derivative = (plus[key] - minus[key]) / (2.0 * delta)
                np.testing.assert_allclose(actual["dlam_" + key], derivative, rtol=4e-7, atol=3e-6)
            print("PASS coupling derivatives", label, flush=True)
        for row in range(case["phi"].shape[0]):
            coupling = np.broadcast_to(case["lam"], (case["phi"].shape[0],))[row]
            separate = solve.solve(dict(case, phi=case["phi"][row:row + 1], logp=case["logp"][row:row + 1], lam=np.array(coupling)))
            compare(separate, {key: value[row:row + 1] for key, value in actual.items()}, "independent row " + label)
        if str(case["profile"]) == "transfer":
            impulse = np.zeros_like(case["phi"])
            impulse[:, 2, 3] = 0.937
            impulse_result = solve.solve(dict(case, phi=impulse))
            indices = (np.indices(impulse.shape[1:]) * -1 + reference.origin)
            row_indices = (indices[0] + 2) % reference.size
            column_indices = (indices[1] + 3) % reference.size
            for row in range(impulse.shape[0]):
                feature = np.r_[np.sin(0.937 * reference.frequencies), 0.937]
                embedding = reference.matrices[row] @ feature
                impulse_expected = np.sum(expected["kernel"][row, row_indices, column_indices] * embedding, axis=-1)
                np.testing.assert_allclose(impulse_result["velocity"][row], impulse_expected, rtol=2e-12, atol=2e-12)
            print("PASS displacement-resolved impulse", label, flush=True)
    for case, reverse in [(cases[0], False), (cases[3], False), (cases[3], True)]:
        case = dict(case, operation=np.array("reverse" if reverse else "forward"), phi=case["phi"] * 0.5)
        reference = Reference(case)
        expected = reference.transport(reverse=reverse)
        actual = solve.solve(case)
        compare(actual, expected, "absolute " + str(case["operation"]) + " " + str(case["model"]), tolerance=2e-10)
    zero_case = dict(cases[-1], phi=np.zeros_like(cases[-1]["phi"]), operation=np.array("forward"))
    reference = Reference(zero_case)
    expected_change = []
    for row in range(2):
        constant_coefficient = reference.weights[row][reference.zero_orbit] @ reference.temporal[row][:, -1]
        expected_change.append(-64 ** 2 * constant_coefficient @ reference.matrices[row] @ np.r_[reference.frequencies, 1.0])
    directory = Path(__file__).resolve().parent
    input_path = directory / "validation-input.npz"
    output_path = directory / "validation-output.npz"
    np.savez(input_path, **zero_case)
    import subprocess
    subprocess.run([sys.executable, str(directory / "solve.py"), str(input_path), str(output_path)], check=True)
    with np.load(output_path, allow_pickle=False) as archive:
        result = dict(archive)
    compare(result, dict(phi=zero_case["phi"], logp=zero_case["logp"] + expected_change), "CLI zero-field exact integral", tolerance=2e-11)
    print("ALL VALIDATIONS PASSED", "seconds", time.perf_counter() - started, flush=True)


if __name__ == "__main__":
    main()
