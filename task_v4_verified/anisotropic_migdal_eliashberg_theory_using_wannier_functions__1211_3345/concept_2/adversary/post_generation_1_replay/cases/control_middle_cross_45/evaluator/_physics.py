import hashlib
import io
import json
import os
import stat
import struct
import zipfile
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.sparse.linalg import LinearOperator, eigsh


DEFAULT_INPUT = Path(__file__).resolve().parent / "hidden" / "frozen_input"


def load_instance(input_dir=DEFAULT_INPUT):
    input_dir = Path(input_dir)
    config = json.loads((input_dir / "config.json").read_text())
    with np.load(input_dir / "reference.npz", allow_pickle=False) as archive:
        instance = {name: np.asarray(archive[name], dtype=np.float64) for name in archive.files}
    instance["config"] = config
    instance["input_sha256"] = hashlib.sha256(
        (input_dir / "config.json").read_bytes() + (input_dir / "reference.npz").read_bytes()
    ).hexdigest()
    return instance


def read_artifact(path, config, with_digest=False):
    path = Path(path)
    initial = os.lstat(path)
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        raise ValueError("artifact must be a regular, non-symlink, single-link file")
    if initial.st_size > config["max_artifact_bytes"]:
        raise ValueError("artifact exceeds compressed size limit")
    directory = os.open("/" if path.is_absolute() else ".", os.O_RDONLY | os.O_DIRECTORY)
    descriptor = None
    try:
        parts = path.parts[1:] if path.is_absolute() else path.parts
        for component in parts[:-1]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = following
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise ValueError("opened artifact is not a single-link regular file")
        if (opened.st_dev, opened.st_ino) != (initial.st_dev, initial.st_ino):
            raise ValueError("artifact changed during open")
        if opened.st_size > config["max_artifact_bytes"]:
            raise ValueError("artifact exceeds compressed size limit")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            payload = stream.read(config["max_artifact_bytes"] + 1)
            finished = os.fstat(stream.fileno())
        if len(payload) > config["max_artifact_bytes"] or len(payload) != opened.st_size:
            raise ValueError("artifact size changed during read")
        if finished.st_nlink != 1 or (finished.st_size, finished.st_mtime_ns, finished.st_ctime_ns) != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
            raise ValueError("artifact changed during read")
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != "kernels.npy":
            raise ValueError("archive must contain only kernels.npy")
        if sum(member.file_size for member in members) > config["max_uncompressed_bytes"]:
            raise ValueError("artifact exceeds uncompressed size limit")
        array_payload = archive.read(members[0])
    header_stream = io.BytesIO(array_payload)
    version = np.lib.format.read_magic(header_stream)
    if version not in ((1, 0), (2, 0)):
        raise ValueError("unsupported NPY header version")
    length_bytes = 2 if version == (1, 0) else 4
    header_length = struct.unpack("<H" if length_bytes == 2 else "<I", header_stream.read(length_bytes))[0]
    if header_length > 4096:
        raise ValueError("NPY header exceeds limit")
    header_stream.seek(8)
    reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
    shape, fortran_order, dtype = reader(header_stream)
    if shape != tuple(config["artifact_shape"]) or dtype.kind not in "fiu" or dtype.itemsize > 8:
        raise ValueError("invalid NPY shape or dtype")
    expected_bytes = int(np.prod(shape)) * dtype.itemsize
    if len(array_payload) - header_stream.tell() != expected_bytes:
        raise ValueError("NPY data length does not match its header")
    with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
        kernels = archive["kernels"]
        if kernels.shape != tuple(config["artifact_shape"]):
            raise ValueError("kernels has the wrong shape")
        if kernels.dtype.kind not in "fiu":
            raise ValueError("kernels must have a real numeric dtype")
        kernels = np.array(kernels, dtype=np.float64, copy=True)
    if not np.isfinite(kernels).all():
        raise ValueError("kernels contains nonfinite entries")
    return (kernels, hashlib.sha256(payload).hexdigest()) if with_digest else kernels


def constraint_report(kernels, instance):
    config = instance["config"]
    if kernels.shape != tuple(config["artifact_shape"]) or not np.isfinite(kernels).all():
        return {"admissible": False, "error": "invalid shape or nonfinite arrays"}, None
    canonical = (kernels + kernels.transpose(0, 1, 3, 2)) * 0.5
    metrics = {
        "symmetry_error": float(np.max(np.abs(kernels - kernels.transpose(0, 1, 3, 2)))),
        "minimum_entry": float(kernels.min()),
        "maximum_entry": float(kernels.max()),
    }
    errors = []
    for label, values in (("raw", kernels), ("canonical", canonical)):
        for name, actual, expected in (
            ("row", values @ instance["weights"], instance["row_sums"]),
            ("diagonal", np.diagonal(values, axis1=2, axis2=3), instance["diagonal"]),
            ("static", values.sum(axis=1), instance["static"]),
        ):
            error = float(np.max(np.abs(actual - expected)))
            metrics[label + "_" + name + "_error"] = error
            if error > config["constraint_atol"]:
                errors.append(label + " " + name + " invariant failed")
    if metrics["symmetry_error"] > config["symmetry_atol"]:
        errors.append("symmetry invariant failed")
    if metrics["minimum_entry"] < config["entry_lower"] - config["constraint_atol"]:
        errors.append("entry lower bound failed")
    if metrics["maximum_entry"] > config["entry_upper"] + config["constraint_atol"]:
        errors.append("entry upper bound failed")
    metrics["admissible"] = not errors
    metrics["errors"] = errors
    return metrics, canonical


class EliashbergSolver:
    def __init__(self, weights, row_sums, energies, config):
        self.weights = np.asarray(weights, dtype=float)
        self.row_sums = np.asarray(row_sums, dtype=float)
        self.energies = np.asarray(energies, dtype=float)
        self.config = config
        self.cache = {}

    def components(self, temperature, count):
        key = (float(temperature), int(count))
        if key in self.cache:
            return self.cache[key]
        thermal = self.config["boltzmann_mev_per_kelvin"] * temperature
        indices = np.arange(count)
        omega = (2 * indices + 1) * np.pi * thermal
        transfer = 2 * np.pi * thermal * indices
        energy_squared = self.energies[:, None] ** 2
        row_kernel = self.row_sums.T @ (energy_squared / (energy_squared + transfer[None] ** 2))
        normal_z = 1 + (2 * np.cumsum(row_kernel, axis=1) - row_kernel[:, :1]) / (2 * indices[None] + 1)
        differences = omega[:, None] - omega[None]
        sums = omega[:, None] + omega[None]
        mode_squared = self.energies[:, None, None] ** 2
        frequency_kernel = mode_squared / (mode_squared + differences[None] ** 2)
        frequency_kernel += mode_squared / (mode_squared + sums[None] ** 2)
        scale = np.sqrt(self.weights[:, None] / (omega[None] * normal_z))
        result = thermal, omega, normal_z, frequency_kernel, scale
        if len(self.cache) >= 20:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = result
        return result

    def eigenpair(self, modes, temperature, count, gradient=False):
        thermal, omega, normal_z, frequency_kernel, scale = self.components(temperature, count)
        patches = len(self.weights)

        def multiply(vector):
            scaled = scale * vector.reshape(patches, count)
            transformed = np.zeros_like(scaled)
            for mode, matrix in enumerate(modes):
                transformed += matrix @ (scaled @ frequency_kernel[mode])
            return (np.pi * thermal * scale * transformed).ravel()

        size = patches * count
        operator = LinearOperator((size, size), matvec=multiply, dtype=float)
        eigenvalues, eigenvectors = eigsh(
            operator, k=1, which="LA", tol=self.config["eigenvalue_tolerance"],
            v0=np.ones(size), maxiter=2000,
        )
        eigenvalue = float(eigenvalues[0])
        vector = eigenvectors[:, 0]
        residual = float(np.linalg.norm(multiply(vector) - eigenvalue * vector))
        result = {"eigenvalue": eigenvalue, "residual": residual}
        if gradient:
            scaled = scale * vector.reshape(patches, count)
            result["gradient"] = np.array([
                np.pi * thermal * scaled @ kernel @ scaled.T for kernel in frequency_kernel
            ])
            result["gap"] = vector.reshape(patches, count) / np.sqrt(
                self.weights[:, None] * normal_z / omega[None]
            )
        return result

    def critical_temperature(self, modes, count):
        lower, upper = self.config["temperature_bracket_kelvin"]

        def objective(temperature):
            return self.eigenpair(modes, temperature, count)["eigenvalue"] - 1

        lower_value = objective(lower)
        upper_value = objective(upper)
        if not (lower_value > 0 and upper_value < 0):
            raise ValueError("transition does not have the required temperature bracket")
        temperature = brentq(
            objective, lower, upper, xtol=self.config["root_xtol_kelvin"], rtol=1e-12
        )
        details = self.eigenpair(modes, temperature, count)
        if details["residual"] > 1e-7 or abs(details["eigenvalue"] - 1) > 2e-6:
            raise ValueError("eigensolve or transition root did not converge")
        return {"tc_kelvin": float(temperature), **details}


def physics_report(kernels, instance):
    config = instance["config"]
    families = []
    convergence = []
    for family in config["families"]:
        energies = instance["energies_mev"] * np.asarray(family["energy_factors"])
        solver = EliashbergSolver(instance["weights"], instance["row_sums"], energies, config)
        counts = list(config["positive_matsubara_counts"])
        if family["name"] == "nominal":
            counts.append(config["nominal_audit_count"])
        grids = []
        previous = None
        for count in counts:
            transitions = [solver.critical_temperature(modes, count) for modes in kernels]
            grids.append({"positive_count": count, "transitions": transitions})
            temperatures = np.array([transition["tc_kelvin"] for transition in transitions])
            if previous is not None:
                drift = float(np.max(np.abs(temperatures - previous) / temperatures))
                convergence.append({"family": family["name"], "positive_count": count, "relative_drift": drift})
            previous = temperatures
        families.append({"name": family["name"], "energies_mev": energies.tolist(), "grids": grids})
    nominal = next(family for family in families if family["name"] == "nominal")
    fine = next(grid for grid in nominal["grids"] if grid["positive_count"] == max(config["positive_matsubara_counts"]))
    high_index = int(fine["transitions"][1]["tc_kelvin"] > fine["transitions"][0]["tc_kelvin"])
    ratios = []
    for family in families:
        for grid in family["grids"]:
            transitions = grid["transitions"]
            ratio = transitions[high_index]["tc_kelvin"] / transitions[1 - high_index]["tc_kelvin"]
            grid["ordered_ratio"] = float(ratio)
            ratios.append(float(ratio))
    score = min(ratios)
    converged = all(item["relative_drift"] <= config["refinement_rtol"] for item in convergence)
    return {
        "score": score, "target_met": score >= config["target_ratio"],
        "converged": converged, "high_kernel_index": high_index,
        "families": families, "refinement": convergence,
    }


def json_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
