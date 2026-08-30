import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
from pathlib import Path

import numpy as np

from optimize import FREQUENCIES, basis


def main():
    path = Path(__file__).with_name("witness.json")
    artifact = json.loads(path.read_text())
    assert set(artifact) == {"schema_version", "kernel_a", "kernel_b"}
    assert artifact["schema_version"] == 1
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size <= 131072
    report = {"kernels": []}
    traces = []
    for name in ("kernel_a", "kernel_b"):
        coefficients = np.array(artifact[name])
        assert coefficients.shape == (18, 18)
        assert np.all(np.isfinite(coefficients))
        assert np.max(np.abs(coefficients)) <= 1
        assert np.max(np.abs(coefficients - coefficients.T)) <= 1e-10
        assert np.max(np.abs(coefficients[:2, :2])) <= 1e-10
        opposite_parity = (FREQUENCIES[:, None] + FREQUENCIES[None, :]) % 2 == 1
        assert np.max(np.abs(coefficients[opposite_parity])) <= 1e-10
        collision = np.eye(18) - coefficients
        gap = np.linalg.eigvalsh(collision).min()
        assert gap >= .08 - 1e-10
        conductivity = np.linalg.solve(collision, np.eye(18)[:, :2])[:2] / 2
        traces.append(float(np.trace(conductivity)))
        features = basis(2 * np.pi * np.arange(1024) / 1024)
        kernel = 1 + features @ coefficients @ features.T
        error = (2 * np.pi / 1024) ** 2 / 4 * np.sum(
            np.abs(coefficients) * (FREQUENCIES[:, None] ** 2 + FREQUENCIES[None, :] ** 2))
        lower = kernel.min() - error
        upper = kernel.max() + error
        assert lower >= .08 - 1e-10
        assert upper <= 6 + 1e-10
        result = {"name": name, "conductivity": conductivity.tolist(),
                  "trace": traces[-1], "collision_gap": float(gap),
                  "sampled_minimum": float(kernel.min()),
                  "sampled_maximum": float(kernel.max()),
                  "certificate_error": float(error),
                  "certified_minimum": float(lower),
                  "certified_maximum": float(upper), "grids": []}
        for count in (64, 128, 256):
            angles = 2 * np.pi * np.arange(count) / count
            features = basis(angles)
            velocity = np.column_stack((np.cos(angles), np.sin(angles)))
            kernel = 1 + features @ coefficients @ features.T
            degrees = kernel.mean(axis=1)
            sampled_collision = np.diag(degrees) - kernel / count
            response = np.linalg.solve(sampled_collision + np.ones((count, count)) / count, velocity)
            sampled_conductivity = velocity.T @ response / count
            differences = velocity[:, None, :] - velocity[None, :, :]
            dirichlet = np.einsum("ij,ija,ijb->ab", kernel, differences, differences) / (2 * count ** 2)
            degree_error = np.max(np.abs(degrees - 1))
            dirichlet_error = np.max(np.abs(dirichlet - np.eye(2) / 2))
            residual = np.max(np.abs(sampled_collision @ response - velocity))
            mean_error = np.max(np.abs(response.mean(axis=0)))
            numerical_error = np.max(np.abs(sampled_conductivity - conductivity))
            inversion_error = np.max(np.abs(kernel - np.roll(np.roll(kernel, count // 2, axis=0), count // 2, axis=1)))
            reciprocity_error = np.max(np.abs(kernel - kernel.T))
            assert degree_error <= 1e-9
            assert dirichlet_error <= 1e-9
            assert max(residual, mean_error, numerical_error) <= 1e-8
            assert max(inversion_error, reciprocity_error) <= 1e-9
            for order in (0, 1, 2):
                moment = np.dot([.5, .3, .2], np.array([1., 2., 4.]) ** order)
                assert degree_error * moment <= 1e-9
                assert dirichlet_error * moment <= 1e-9
            result["grids"].append({"count": count,
                                    "trace": float(np.trace(sampled_conductivity)),
                                    "degree_error": float(degree_error),
                                    "dirichlet_error": float(dirichlet_error),
                                    "residual": float(residual),
                                    "zero_mean_error": float(mean_error),
                                    "conductivity_error": float(numerical_error)})
        report["kernels"].append(result)
    ratio = max(traces) / min(traces)
    report["trace_ratio"] = ratio
    report["target_passed"] = ratio >= 1.75
    for index in range(3):
        sampled_traces = [kernel["grids"][index]["trace"] for kernel in report["kernels"]]
        assert abs(max(sampled_traces) / min(sampled_traces) - ratio) <= 1e-8
    Path(__file__).with_name("validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    assert ratio >= 1.75


if __name__ == "__main__":
    main()
