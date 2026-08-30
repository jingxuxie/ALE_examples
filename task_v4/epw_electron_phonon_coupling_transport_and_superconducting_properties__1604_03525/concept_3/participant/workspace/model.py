import argparse
import json
import os
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

import numpy as np

ORDER = 9
DIMENSION = 2 * ORDER
FREQUENCIES = np.repeat(np.arange(1, ORDER + 1), 2)


def angular_basis(count, shift=0.0):
    angles = 2 * np.pi * (np.arange(count) + shift) / count
    values = np.empty((count, DIMENSION))
    for harmonic in range(1, ORDER + 1):
        values[:, 2 * harmonic - 2] = np.sqrt(2) * np.cos(harmonic * angles)
        values[:, 2 * harmonic - 1] = np.sqrt(2) * np.sin(harmonic * angles)
    return angles, values


def kernel_values(coefficients, count=256, shift=0.0):
    angles, values = angular_basis(count, shift)
    return angles, 1 + values @ coefficients @ values.T


def conductivity(coefficients):
    return np.linalg.solve(np.eye(DIMENSION) - coefficients, np.eye(DIMENSION)[:, :2])[:2] / 2


def enclosure(coefficients, count=1024):
    _, values = kernel_values(coefficients, count)
    second = FREQUENCIES[:, None] ** 2 + FREQUENCIES[None, :] ** 2
    error = (2 * np.pi / count) ** 2 * np.sum(np.abs(coefficients) * second) / 4
    return float(values.min() - error), float(values.max() + error), float(error)


def diagnostics(first, second):
    results = []
    for coefficients in (first, second):
        lower, upper, error = enclosure(coefficients)
        results.append({
            "conductivity": conductivity(coefficients).tolist(),
            "certified_lower": lower,
            "certified_upper": upper,
            "enclosure_error": error,
            "reciprocity_error": float(np.max(np.abs(coefficients - coefficients.T))),
            "first_block_error": float(np.max(np.abs(coefficients[:2, :2]))),
            "inversion_error": float(np.max(np.abs(coefficients[(FREQUENCIES[:, None] + FREQUENCIES[None, :]) % 2 == 1]))),
            "collision_gap": float(np.linalg.eigvalsh(np.eye(DIMENSION) - coefficients).min()),
        })
    traces = [np.trace(np.array(result["conductivity"])) for result in results]
    ratio = float(max(traces) / min(traces))
    return {"authoritative": False, "trace_ratio": ratio, "target": 1.75, "kernels": results}


def write_witness(path, first, second):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"schema_version": 1, "kernel_a": first.tolist(), "kernel_b": second.tolist()}, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    arguments = parser.parse_args()
    artifact = json.loads(Path(arguments.witness).read_text())
    first = np.asarray(artifact["kernel_a"], dtype=float)
    second = np.asarray(artifact["kernel_b"], dtype=float)
    if first.shape != (DIMENSION, DIMENSION) or second.shape != (DIMENSION, DIMENSION):
        raise ValueError("each coefficient matrix must be 18 by 18")
    print(json.dumps(diagnostics(first, second), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
