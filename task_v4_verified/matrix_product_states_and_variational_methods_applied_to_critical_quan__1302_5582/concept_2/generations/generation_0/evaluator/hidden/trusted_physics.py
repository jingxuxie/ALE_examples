import json
from pathlib import Path
import zipfile

import numpy as np
import scipy.linalg as sla


IDENTITY = np.eye(2, dtype=np.complex128)
SIGMA_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
SIGMA_Z = np.diag([1.0, -1.0]).astype(np.complex128)


def load_tensor(path):
    path = Path(path)
    if path.stat().st_size > 1048576:
        raise ValueError("artifact is larger than one MiB")
    with zipfile.ZipFile(path) as archive:
        if sum(member.file_size for member in archive.infolist()) > 1048576:
            raise ValueError("uncompressed artifact is larger than one MiB")
        if archive.namelist() != ["A.npy"]:
            raise ValueError("state.npz must contain exactly the A array")
    with np.load(path, allow_pickle=False) as data:
        tensor = data["A"]
        if tensor.dtype.kind not in "fc":
            raise ValueError("A must be a floating or complex array")
        tensor = np.asarray(tensor, dtype=np.complex128)
    if tensor.ndim != 3 or tensor.shape[0] != 2:
        raise ValueError("A shape must be (2,D,D)")
    dimension = tensor.shape[1]
    if tensor.shape[2] != dimension or dimension < 2 or dimension > 24 or dimension % 2:
        raise ValueError("D must be even and between 2 and 24")
    if not np.isfinite(tensor).all():
        raise ValueError("A contains nonfinite entries")
    return tensor


def transfer_matrix(tensor):
    dimension = tensor.shape[1]
    return np.einsum("sac,sbd->abcd", tensor, tensor.conj()).reshape(dimension**2, dimension**2)


def apply_transfer(tensor, matrix, operator=IDENTITY):
    result = np.zeros_like(matrix, dtype=np.complex128)
    for ket in range(2):
        for bra in range(2):
            if operator[bra, ket] != 0:
                result += operator[bra, ket] * (tensor[ket] @ matrix @ tensor[bra].conj().T)
    return result


def exact_order(distance):
    indices = np.arange(distance)
    matrix = 2.0 / (np.pi * (2.0 * (indices[:, None] - indices[None, :]) + 1.0))
    sign, logdet = np.linalg.slogdet(matrix)
    return float(sign * np.exp(logdet))


def exact_density(distance):
    return float(4.0 / (np.pi**2 * (4.0 * distance**2 - 1.0)))


def stationary(tensor):
    dimension = tensor.shape[1]
    transfer = transfer_matrix(tensor)
    eigenvalues, left_vectors = sla.eig(transfer.conj().T, check_finite=False)
    fixed_index = int(np.argmin(abs(eigenvalues - 1.0)))
    fixed = left_vectors[:, fixed_index].reshape(dimension, dimension)
    fixed = fixed / np.trace(fixed)
    fixed = (fixed + fixed.conj().T) / 2.0
    fixed = fixed / np.trace(fixed)
    others = np.delete(eigenvalues, fixed_index)
    residual = np.linalg.norm(transfer.conj().T @ fixed.reshape(-1) - fixed.reshape(-1))
    return fixed, float(np.max(np.abs(others))), float(residual), float(abs(eigenvalues[fixed_index] - 1.0))


def real_value(value, name):
    if not np.isfinite(value) or abs(np.imag(value)) > 2e-8:
        raise ValueError(name + " has nonfinite or nonreal contraction")
    return float(np.real(value))


def metrics(tensor, require_admissible=True):
    dimension = tensor.shape[1]
    identity = np.eye(dimension, dtype=np.complex128)
    canonical_defect = float(np.linalg.norm(apply_transfer(tensor, identity) - identity))
    parity = np.concatenate([np.ones(dimension // 2), -np.ones(dimension // 2)])
    transformed = tensor * parity[None, :, None] * parity[None, None, :]
    parity_defect = float(max(np.linalg.norm(transformed[0] - tensor[0]), np.linalg.norm(transformed[1] + tensor[1])))
    if require_admissible and (canonical_defect > 2e-8 or parity_defect > 2e-8):
        raise ValueError("canonical or parity condition failed: " + str((canonical_defect, parity_defect)))
    density, second_modulus, fixed_residual, fixed_error = stationary(tensor)
    minimum_density = float(sla.eigvalsh(density, check_finite=False)[0])
    if require_admissible:
        if fixed_residual > 2e-9 or fixed_error > 2e-9 or minimum_density < 1e-12:
            raise ValueError("stationary-density condition failed")
        if second_modulus > 1.0 - 1e-8:
            raise ValueError("transfer operator is not numerically primitive")
    order_environment = apply_transfer(tensor, identity, SIGMA_X)
    density_environment = apply_transfer(tensor, identity, SIGMA_Z)
    transverse = real_value(np.trace(density @ density_environment), "transverse magnetization")
    longitudinal = real_value(np.trace(density @ order_environment), "longitudinal magnetization")
    order_values = []
    density_values = []
    for distance in range(1, 129):
        order_values.append(real_value(np.trace(density @ apply_transfer(tensor, order_environment, SIGMA_X)), "order correlation"))
        if distance <= 32:
            density_values.append(real_value(np.trace(density @ apply_transfer(tensor, density_environment, SIGMA_Z)), "density correlation") - transverse**2)
            density_environment = apply_transfer(tensor, density_environment)
        order_environment = apply_transfer(tensor, order_environment)
    energy = -order_values[0] - transverse
    energy_excess = energy + 4.0 / np.pi
    if require_admissible and energy_excess < -5e-9:
        raise ValueError("energy violates the exact variational bound")
    exact_orders = np.array([exact_order(distance) for distance in range(1, 129)])
    exact_densities = np.array([exact_density(distance) for distance in range(1, 33)])
    order_errors = np.abs(np.asarray(order_values) / exact_orders - 1.0)
    density_errors = np.abs(np.asarray(density_values) / exact_densities - 1.0)
    return {
        "dimension": dimension,
        "canonical_defect": canonical_defect,
        "parity_defect": parity_defect,
        "fixed_point_residual": fixed_residual,
        "fixed_point_eigenvalue_error": fixed_error,
        "minimum_density_eigenvalue": minimum_density,
        "second_transfer_modulus": second_modulus,
        "correlation_length": float(-1.0 / np.log(second_modulus)) if 0.0 < second_modulus < 1.0 else None,
        "energy_density": energy,
        "energy_excess": energy_excess,
        "transverse_magnetization": transverse,
        "longitudinal_magnetization": longitudinal,
        "order_max_relative_error": float(max(order_errors)),
        "density_max_relative_error": float(max(density_errors)),
        "order_worst_distance": int(np.argmax(order_errors) + 1),
        "density_worst_distance": int(np.argmax(density_errors) + 1),
        "order_correlations": order_values,
        "density_connected_correlations": density_values,
    }


def score_metrics(values):
    errors = [max(0.0, values["energy_excess"]), values["order_max_relative_error"], values["density_max_relative_error"]]
    limits = [5e-5, 0.025, 0.1]
    qualities = [float(min(1.0, limit / max(error, 1e-300))) for error, limit in zip(errors, limits)]
    passed = all(error <= limit for error, limit in zip(errors, limits))
    return {
        "core_score": float(np.prod(qualities)**(1.0 / 3.0)),
        "worst_family_score": min(qualities),
        "family_scores": dict(zip(["energy", "order", "density"], qualities)),
        "passed": passed,
        "valid": True,
        "reason": "all witness conditions satisfied" if passed else "one or more multiscale witness tolerances failed",
        "metrics": values,
    }


def check(path):
    try:
        return score_metrics(metrics(load_tensor(path)))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, sla.LinAlgError) as error:
        return {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": str(error)}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
