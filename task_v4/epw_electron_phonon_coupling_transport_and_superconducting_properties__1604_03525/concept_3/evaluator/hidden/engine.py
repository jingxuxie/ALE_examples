import hashlib
import json
import math
import os
from pathlib import Path
import stat

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ORDER = 9
DIMENSION = 18
FREQUENCIES = np.repeat(np.arange(1, ORDER + 1), 2)
LOWER = 0.08
UPPER = 6.0
TARGET = 1.75
COEFFICIENT_TOLERANCE = 1e-10
INVARIANT_TOLERANCE = 1e-9
NUMERICAL_TOLERANCE = 1e-8
CERTIFICATE_GRID = 1024
REFINEMENT_GRIDS = (64, 128, 256)
MAX_BYTES = 131072
PHONON_FREQUENCIES = np.array([1.0, 2.0, 4.0])
PHONON_WEIGHTS = np.array([0.5, 0.3, 0.2])


class InvalidWitness(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidWitness(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise InvalidWitness("nonstandard JSON numeric constant")


def coefficient_matrix(value):
    require(isinstance(value, list) and len(value) == DIMENSION, "matrix must contain 18 rows")
    for row in value:
        require(isinstance(row, list) and len(row) == DIMENSION, "matrix rows must contain 18 numbers")
        for entry in row:
            require(type(entry) in (int, float), "coefficient must be a JSON number, not a string or boolean")
            require(math.isfinite(entry) and abs(entry) <= 1.0, "coefficient must be finite and bounded by one")
    return np.array(value, dtype=np.float64)


def load_witness(submission):
    directory = Path(submission)
    require(directory.is_dir(), "--submission must name a directory containing witness.json")
    path = directory / "witness.json"
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode), "witness must be a regular file, not a symlink")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        require(stat.S_ISREG(metadata.st_mode), "witness must be a regular file")
        require(metadata.st_size <= MAX_BYTES, "witness exceeds byte limit")
        raw = handle.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "witness exceeds byte limit")
    artifact = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    require(isinstance(artifact, dict), "witness must be an object")
    require(set(artifact) == {"schema_version", "kernel_a", "kernel_b"}, "unexpected or missing witness keys")
    require(type(artifact["schema_version"]) is int and artifact["schema_version"] == 1, "unsupported schema version")
    matrices = (coefficient_matrix(artifact["kernel_a"]), coefficient_matrix(artifact["kernel_b"]))
    return matrices, {"witness_bytes": len(raw), "witness_sha256": hashlib.sha256(raw).hexdigest()}


def sampled_basis(count, shift=0.0):
    angles = 2 * np.pi * (np.arange(count) + shift) / count
    phases = angles[:, None] * np.arange(1, ORDER + 1)[None, :]
    basis = np.stack((np.cos(phases), np.sin(phases)), axis=-1).reshape(count, DIMENSION) * np.sqrt(2)
    velocity = np.column_stack((np.cos(angles), np.sin(angles)))
    return basis, velocity


def certify_coefficients(coefficients):
    reciprocity = float(np.max(np.abs(coefficients - coefficients.T)))
    forbidden = (FREQUENCIES[:, None] + FREQUENCIES[None, :]) % 2 == 1
    inversion = float(np.max(np.abs(coefficients[forbidden])))
    first_block = float(np.max(np.abs(coefficients[:2, :2])))
    require(reciprocity <= COEFFICIENT_TOLERANCE, "coefficient reciprocity violation")
    require(inversion <= COEFFICIENT_TOLERANCE, "coefficient inversion violation")
    require(first_block <= COEFFICIENT_TOLERANCE, "full velocity Dirichlet matrix is not the prescribed I/2")
    basis, _ = sampled_basis(CERTIFICATE_GRID)
    values = 1.0 + basis @ coefficients @ basis.T
    squared_sum = FREQUENCIES[:, None] ** 2 + FREQUENCIES[None, :] ** 2
    enclosure_error = float((2 * np.pi / CERTIFICATE_GRID) ** 2 * np.sum(np.abs(coefficients) * squared_sum) / 4)
    certified_lower = float(np.min(values) - enclosure_error)
    certified_upper = float(np.max(values) + enclosure_error)
    require(certified_lower >= LOWER - COEFFICIENT_TOLERANCE, "continuum lower-bound certificate fails")
    require(certified_upper <= UPPER + COEFFICIENT_TOLERANCE, "continuum upper-bound certificate fails")
    operator = np.eye(DIMENSION) - coefficients
    gap = float(np.min(np.linalg.eigvalsh((operator + operator.T) / 2)))
    require(gap >= LOWER - INVARIANT_TOLERANCE, "collision gap violates the uniform floor")
    response = np.linalg.solve(operator, np.eye(DIMENSION)[:, :2])
    tensor = response[:2] / 2
    require(float(np.linalg.eigvalsh((tensor + tensor.T) / 2).min()) > 0, "conductivity is not positive definite")
    return tensor, {
        "coefficient_reciprocity_error": reciprocity,
        "coefficient_inversion_error": inversion,
        "first_block_error": first_block,
        "sampled_minimum": float(np.min(values)),
        "sampled_maximum": float(np.max(values)),
        "enclosure_error": enclosure_error,
        "certified_lower": certified_lower,
        "certified_upper": certified_upper,
        "collision_gap": gap,
        "higher_harmonic_coupling_norm": float(np.linalg.norm(coefficients[:2, 2:])),
        "continuum_conductivity": tensor.tolist(),
    }


def direct_observables(coefficients, count, shift=0.0):
    basis, velocity = sampled_basis(count, shift)
    kernel = 1.0 + basis @ coefficients @ basis.T
    degree = np.mean(kernel, axis=1)
    collision = np.diag(degree) - kernel / count
    response = np.linalg.solve(collision + np.ones((count, count)) / count, velocity)
    tensor = velocity.T @ response / count
    differences = velocity[:, None, :] - velocity[None, :, :]
    dirichlet = np.einsum("ij,ija,ijb->ab", kernel, differences, differences, optimize=True) / (2 * count * count)
    moments = np.array([np.sum(PHONON_WEIGHTS * PHONON_FREQUENCIES ** power) for power in (0, 1, 2)])
    return {
        "tensor": tensor,
        "degree": degree,
        "dirichlet": dirichlet,
        "linewidth_moments": moments[:, None] * degree[None, :],
        "transport_moments": moments[:, None, None] * dirichlet[None, :, :],
        "reciprocity_error": float(np.max(np.abs(kernel - kernel.T))),
        "inversion_error": float(np.max(np.abs(kernel - np.roll(kernel, (count // 2, count // 2), axis=(0, 1))))),
        "residual": float(np.max(np.abs(collision @ response - velocity))),
        "mean_error": float(np.max(np.abs(np.mean(response, axis=0)))),
    }


def validate_pair(matrices):
    continuum = []
    certificates = []
    for coefficients in matrices:
        tensor, certificate = certify_coefficients(coefficients)
        continuum.append(tensor)
        certificates.append(certificate)
    traces = [float(np.trace(tensor)) for tensor in continuum]
    exact_ratio = max(traces) / min(traces)
    refinements = []
    worst_error = 0.0
    for count in REFINEMENT_GRIDS:
        shift = 0.375 if count == REFINEMENT_GRIDS[-1] else 0.0
        observables = [direct_observables(coefficients, count, shift) for coefficients in matrices]
        errors = {}
        for label, values, exact in zip(("a", "b"), observables, continuum):
            errors[label + "_degree"] = float(np.max(np.abs(values["degree"] - 1)))
            errors[label + "_dirichlet"] = float(np.max(np.abs(values["dirichlet"] - np.eye(2) / 2)))
            errors[label + "_conductivity"] = float(np.max(np.abs(values["tensor"] - exact)))
            for name in ("reciprocity_error", "inversion_error", "residual", "mean_error"):
                errors[label + "_" + name] = values[name]
        for name in ("degree", "dirichlet", "linewidth_moments", "transport_moments"):
            errors["matched_" + name] = float(np.max(np.abs(observables[0][name] - observables[1][name])))
        for name, value in errors.items():
            tolerance = NUMERICAL_TOLERANCE if any(term in name for term in ("conductivity", "residual", "mean_error")) else INVARIANT_TOLERANCE
            require(value <= tolerance, "independent invariant or refinement check failed: " + name)
        current_traces = [float(np.trace(values["tensor"])) for values in observables]
        ratio = max(current_traces) / min(current_traces)
        require(abs(ratio - exact_ratio) <= NUMERICAL_TOLERANCE, "conductivity-ratio refinement failure")
        worst_error = max(worst_error, max(errors.values()), abs(ratio - exact_ratio))
        refinements.append({"grid": count, "shift": shift, "trace_ratio": ratio,
                            "conductivities": [values["tensor"].tolist() for values in observables],
                            "dirichlet_matrices": [values["dirichlet"].tolist() for values in observables],
                            "errors": errors})
    worst_ratio = min([exact_ratio] + [item["trace_ratio"] for item in refinements])
    score = max(0.0, (worst_ratio - 1) / (TARGET - 1))
    passed = worst_ratio >= TARGET
    return {"valid": True, "passed": passed, "status": "passed" if passed else "target_not_met",
            "reason": "all checks and fixed trace-ratio target pass" if passed else "valid kernels; fixed trace-ratio target not met",
            "score": score, "core_score": score, "worst_family_score": score,
            "trace_ratio": exact_ratio, "worst_grid_trace_ratio": worst_ratio, "target_trace_ratio": TARGET,
            "maximum_numerical_error": worst_error, "certificates": certificates, "refinements": refinements}
