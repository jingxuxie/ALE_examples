import json
from pathlib import Path
import zipfile

import numpy as np
import scipy.linalg as sla


CONTRACT_VERSION = "critical-vacuum-v4"
IDENTITY = np.eye(2, dtype=np.complex128)
SIGMA_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
SIGMA_Y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
SIGMA_Z = np.diag([1.0, -1.0]).astype(np.complex128)
COMPOSITE_INTERVALS = (16, 32, 64, 96)
COMPOSITE_GAPS = (32, 64, 96, 128)
COMPOSITE_QUARTETS = tuple((0, left, left + gap, left + gap + right)
                           for left in COMPOSITE_INTERVALS for gap in COMPOSITE_GAPS
                           for right in COMPOSITE_INTERVALS if left + gap + right <= 256)
THREE_INTERVAL_SEXTUPLES = tuple((0, left, left + first_gap, left + first_gap + middle,
                                 left + first_gap + middle + second_gap,
                                 left + first_gap + middle + second_gap + right)
                                for left in COMPOSITE_INTERVALS for first_gap in COMPOSITE_GAPS
                                for middle in COMPOSITE_INTERVALS for second_gap in COMPOSITE_GAPS
                                for right in COMPOSITE_INTERVALS
                                if left + first_gap + middle + second_gap + right <= 256)


def load_tensor(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("the tensor must be a regular file, not a symlink")
    if path.stat().st_size > 1048576:
        raise ValueError("artifact is larger than one MiB")
    with zipfile.ZipFile(path) as archive:
        if sum(member.file_size for member in archive.infolist()) > 1048576:
            raise ValueError("uncompressed artifact is larger than one MiB")
        if archive.namelist() != ["A.npy"]:
            raise ValueError("state.npz must contain exactly the A array")
        with archive.open("A.npy") as member:
            version = np.lib.format.read_magic(member)
            if version == (1, 0):
                shape, unused_fortran_order, dtype = np.lib.format.read_array_header_1_0(member)
            elif version in ((2, 0), (3, 0)):
                shape, unused_fortran_order, dtype = np.lib.format.read_array_header_2_0(member)
            else:
                raise ValueError("unsupported NumPy array format")
            if dtype.kind not in "fc":
                raise ValueError("A must be a floating or complex array")
            if len(shape) != 3 or shape[0] != 2:
                raise ValueError("A shape must be (2,D,D)")
            if shape[1] != shape[2] or shape[1] < 2 or shape[1] > 24 or shape[1] % 2:
                raise ValueError("D must be even and between 2 and 24")
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
    positions = np.arange(1, distance)
    logarithm = distance * np.log(2.0 / np.pi) - np.sum((distance - positions) * np.log1p(-1.0 / (4.0 * positions**2)))
    return float(np.exp(logarithm))


def exact_density(distance):
    return float(4.0 / (np.pi**2 * (4.0 * distance**2 - 1.0)))


def fourpoint_cross_log(quartet):
    first, second, third, fourth = quartet
    if not first < second < third < fourth:
        raise ValueError("four-spin sites must be strictly increasing")
    first_sites = np.arange(first + 1, second + 1, dtype=np.float64)
    second_sites = np.arange(third + 1, fourth + 1, dtype=np.float64)
    distances = second_sites[:, None] - first_sites[None, :]
    return float(-np.log1p(-1.0 / (4.0 * distances**2)).sum(dtype=np.longdouble))


def exact_composite_covariance(quartet):
    first, second, third, fourth = quartet
    pair_product = exact_order(second - first) * exact_order(fourth - third)
    return float(pair_product * np.expm1(fourpoint_cross_log(quartet)))


def exact_four_order(quartet):
    first, second, third, fourth = quartet
    pair_product = exact_order(second - first) * exact_order(fourth - third)
    return float(pair_product * np.exp(fourpoint_cross_log(quartet)))


def composite_observables(tensor, density, quartets=COMPOSITE_QUARTETS, right_boundary=None):
    if right_boundary is None:
        tensor, density, right_boundary, unused_eigenvalue, unused_residual = observable_boundaries(tensor, density)
    specifications = [(second - first, third - second, fourth - third)
                      for first, second, third, fourth in quartets]
    lengths = {length for left, unused_gap, right in specifications for length in (left, right)}
    identity = np.eye(tensor.shape[1], dtype=np.complex128) if right_boundary is None else right_boundary
    environment = apply_transfer(tensor, identity, SIGMA_X)
    interval_environments = {}
    interval_means = {}
    for length in range(1, max(lengths) + 1):
        if length in lengths:
            interval = apply_transfer(tensor, environment, SIGMA_X)
            interval_environments[length] = interval
            interval_means[length] = real_value(np.trace(density @ interval), "interval mean")
        environment = apply_transfer(tensor, environment)
    raw_values = {}
    for right in sorted({right for unused_left, unused_gap, right in specifications}):
        gaps = {gap for unused_left, gap, interval in specifications if interval == right}
        environment = interval_environments[right].copy()
        for gap in range(1, max(gaps) + 1):
            if gap in gaps:
                left_lengths = {left for left, separation, interval in specifications
                                if separation == gap and interval == right}
                left_environment = apply_transfer(tensor, environment, SIGMA_X)
                for left in range(1, max(left_lengths) + 1):
                    if left in left_lengths:
                        raw_values[left, gap, right] = real_value(
                            np.trace(density @ apply_transfer(tensor, left_environment, SIGMA_X)),
                            "four-spin order correlation")
                    left_environment = apply_transfer(tensor, left_environment)
            environment = apply_transfer(tensor, environment)
    raw = [raw_values[specification] for specification in specifications]
    means = [[interval_means[left], interval_means[right]] for left, unused_gap, right in specifications]
    covariances = [value - left_mean * right_mean for value, (left_mean, right_mean) in zip(raw, means)]
    return raw, means, covariances


def exact_three_interval_cumulant(sextuple):
    if len(sextuple) != 6 or any(right <= left for left, right in zip(sextuple, sextuple[1:])):
        raise ValueError("six-spin sites must be strictly increasing")
    intervals = tuple(zip(sextuple[::2], sextuple[1::2]))
    means = [exact_order(second - first) for first, second in intervals]
    enhancements = [np.expm1(fourpoint_cross_log(intervals[first] + intervals[second]))
                    for first, second in ((0, 1), (0, 2), (1, 2))]
    first_cross, outer_cross, last_cross = enhancements
    return float(np.prod(means) * (first_cross * outer_cross + first_cross * last_cross
                                  + outer_cross * last_cross + first_cross * outer_cross * last_cross))


def three_interval_observables(tensor, density, sextuples=THREE_INTERVAL_SEXTUPLES, right_boundary=None):
    if right_boundary is None:
        tensor, density, right_boundary, unused_eigenvalue, unused_residual = observable_boundaries(tensor, density)
    moment_cache = {}
    identity = np.eye(tensor.shape[1], dtype=np.complex128) if right_boundary is None else right_boundary

    def moment(sites):
        sites = tuple(site - sites[0] for site in sites)
        if sites not in moment_cache:
            environment = identity.copy()
            previous = None
            for site in reversed(sites):
                if previous is not None:
                    for unused_step in range(previous - site - 1):
                        environment = apply_transfer(tensor, environment)
                environment = apply_transfer(tensor, environment, SIGMA_X)
                previous = site
            moment_cache[sites] = real_value(np.trace(density @ environment), "six-spin moment")
        return moment_cache[sites]

    raw_values, pair_values, four_values, cumulants = [], [], [], []
    for sextuple in sextuples:
        if len(sextuple) != 6 or any(right <= left for left, right in zip(sextuple, sextuple[1:])):
            raise ValueError("six-spin sites must be strictly increasing")
        intervals = tuple(zip(sextuple[::2], sextuple[1::2]))
        means = [moment(interval) for interval in intervals]
        lower = [moment(intervals[first] + intervals[second]) for first, second in ((0, 1), (0, 2), (1, 2))]
        raw = moment(sextuple)
        cumulant = raw - lower[0] * means[2] - lower[1] * means[1] - lower[2] * means[0] + 2 * np.prod(means)
        raw_values.append(raw)
        pair_values.append(means)
        four_values.append(lower)
        cumulants.append(float(cumulant))
    return np.asarray(raw_values), np.asarray(pair_values), np.asarray(four_values), np.asarray(cumulants)


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


def observable_boundaries(tensor, density):
    dimension = tensor.shape[1]
    transfer = transfer_matrix(tensor)
    identity_vector = np.eye(dimension, dtype=np.complex128).reshape(-1)
    left_vector = density.reshape(-1)
    eigenvalue = real_value(np.vdot(left_vector, transfer @ identity_vector), "leading transfer eigenvalue")
    if eigenvalue <= 0:
        raise ValueError("leading transfer eigenvalue must be positive")
    system = eigenvalue * np.eye(dimension**2) - transfer + np.outer(identity_vector, left_vector.conj())
    right = sla.solve(system, identity_vector, check_finite=False).reshape(dimension, dimension)
    right = (right + right.conj().T) / 2.0
    overlap = real_value(np.trace(density @ right), "fixed-point overlap")
    if overlap <= 0 or not np.isfinite(right).all():
        raise ValueError("invalid right transfer fixed point")
    right = right / overlap
    normalized_tensor = tensor / np.sqrt(eigenvalue)
    residual = float(np.linalg.norm(apply_transfer(normalized_tensor, right) - right) / np.linalg.norm(right))
    if residual > 2e-9:
        raise ValueError("right transfer fixed point could not be resolved accurately")
    return normalized_tensor, density, right, eigenvalue, residual


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
    tensor, density, identity, observable_eigenvalue, right_residual = observable_boundaries(tensor, density)
    order_environment = apply_transfer(tensor, identity, SIGMA_X)
    density_environment = apply_transfer(tensor, identity, SIGMA_Z)
    y_environment = apply_transfer(tensor, identity, SIGMA_Y)
    transverse = real_value(np.trace(density @ density_environment), "transverse magnetization")
    longitudinal = real_value(np.trace(density @ order_environment), "longitudinal magnetization")
    order_values = []
    density_values = []
    y_values = []
    for distance in range(1, 1025):
        order_values.append(real_value(np.trace(density @ apply_transfer(tensor, order_environment, SIGMA_X)), "order correlation"))
        if distance <= 256:
            density_values.append(real_value(np.trace(density @ apply_transfer(tensor, density_environment, SIGMA_Z)), "density correlation") - transverse**2)
            density_environment = apply_transfer(tensor, density_environment)
        if distance <= 128:
            y_values.append(real_value(np.trace(density @ apply_transfer(tensor, y_environment, SIGMA_Y)), "y-spin correlation"))
            y_environment = apply_transfer(tensor, y_environment)
        order_environment = apply_transfer(tensor, order_environment)
    energy = -order_values[0] - transverse
    energy_excess = energy + 4.0 / np.pi
    if require_admissible and energy_excess < -5e-9:
        raise ValueError("energy violates the exact variational bound")
    exact_orders = np.array([exact_order(distance) for distance in range(1, 1025)])
    exact_densities = np.array([exact_density(distance) for distance in range(1, 257)])
    exact_y = -exact_orders[:128] / (4.0 * np.arange(1, 129)**2 - 1.0)
    order_errors = np.abs(np.asarray(order_values) / exact_orders - 1.0)
    density_errors = np.abs(np.asarray(density_values) / exact_densities - 1.0)
    y_errors = np.abs(np.asarray(y_values) / exact_y - 1.0)
    composite_raw, composite_means, composite_values = composite_observables(tensor, density, right_boundary=identity)
    exact_composites = np.asarray([exact_composite_covariance(quartet) for quartet in COMPOSITE_QUARTETS])
    composite_errors = np.abs(np.asarray(composite_values) / exact_composites - 1.0)
    three_raw, three_means, three_lower, three_values = three_interval_observables(tensor, density, right_boundary=identity)
    exact_three = np.asarray([exact_three_interval_cumulant(sextuple) for sextuple in THREE_INTERVAL_SEXTUPLES])
    three_errors = np.abs(three_values / exact_three - 1.0)
    return {
        "dimension": dimension,
        "canonical_defect": canonical_defect,
        "parity_defect": parity_defect,
        "fixed_point_residual": fixed_residual,
        "fixed_point_eigenvalue_error": fixed_error,
        "minimum_density_eigenvalue": minimum_density,
        "second_transfer_modulus": second_modulus,
        "observable_transfer_eigenvalue": observable_eigenvalue,
        "observable_right_fixed_point_residual": right_residual,
        "observable_right_fixed_point_identity_defect": float(np.linalg.norm(identity - np.eye(dimension))),
        "correlation_length": float(-1.0 / np.log(second_modulus)) if 0.0 < second_modulus < 1.0 else None,
        "energy_density": energy,
        "energy_excess": energy_excess,
        "transverse_magnetization": transverse,
        "longitudinal_magnetization": longitudinal,
        "order_max_relative_error": float(max(order_errors)),
        "density_max_relative_error": float(max(density_errors)),
        "y_max_relative_error": float(max(y_errors)),
        "composite_order_max_relative_error": float(max(composite_errors)),
        "three_interval_max_relative_error": float(max(three_errors)),
        "order_worst_distance": int(np.argmax(order_errors) + 1),
        "density_worst_distance": int(np.argmax(density_errors) + 1),
        "y_worst_distance": int(np.argmax(y_errors) + 1),
        "composite_order_worst_quartet": list(COMPOSITE_QUARTETS[int(np.argmax(composite_errors))]),
        "three_interval_worst_sextuple": list(THREE_INTERVAL_SEXTUPLES[int(np.argmax(three_errors))]),
        "order_correlations": order_values,
        "density_connected_correlations": density_values,
        "y_correlations": y_values,
        "composite_order_quartets": [list(quartet) for quartet in COMPOSITE_QUARTETS],
        "composite_order_four_spin_correlations": composite_raw,
        "composite_order_interval_means": composite_means,
        "composite_order_covariances": composite_values,
        "three_interval_sextuples": [list(sextuple) for sextuple in THREE_INTERVAL_SEXTUPLES],
        "three_interval_six_spin_correlations": three_raw.tolist(),
        "three_interval_means": three_means.tolist(),
        "three_interval_four_spin_correlations": three_lower.tolist(),
        "three_interval_cumulants": three_values.tolist(),
    }


def score_metrics(values):
    errors = [max(0.0, values["energy_excess"]), values["order_max_relative_error"], values["density_max_relative_error"], values["y_max_relative_error"], values["composite_order_max_relative_error"], values["three_interval_max_relative_error"]]
    limits = [5e-5, 0.025, 0.1, 0.1, 0.01, 0.1]
    qualities = [float(min(1.0, limit / max(error, 1e-300))) for error, limit in zip(errors, limits)]
    passed = all(error <= limit for error, limit in zip(errors, limits))
    return {
        "core_score": float(np.prod(qualities)**(1.0 / 6.0)),
        "worst_family_score": min(qualities),
        "family_scores": dict(zip(["energy", "order", "density", "y_spin", "composite_order", "three_interval"], qualities)),
        "passed": passed,
        "valid": True,
        "reason": "all witness conditions satisfied" if passed else "one or more multiscale witness tolerances failed",
        "metrics": values,
    }


def check(path):
    try:
        return score_metrics(metrics(load_tensor(path)))
    except (ValueError, OSError, KeyError, EOFError, TypeError, RuntimeError, zipfile.BadZipFile, sla.LinAlgError) as error:
        return {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": str(error)}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
