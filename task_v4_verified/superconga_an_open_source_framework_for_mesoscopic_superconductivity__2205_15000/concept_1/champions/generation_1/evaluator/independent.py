import ast
import io
import json
import os
from pathlib import Path
import struct
import zipfile

import numpy as np


def read_case(path):
    return json.loads(Path(path).read_text())


def checked_field(path, case, maximum_bytes=4194304):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        import stat
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum_bytes:
            raise ValueError("result is not a bounded regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(maximum_bytes + 1)
    finally:
        os.close(descriptor)
    if len(data) > maximum_bytes:
        raise ValueError("oversized result")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != "psi.npy":
            raise ValueError("NPZ must contain exactly psi")
        entry = entries[0]
        if entry.file_size > maximum_bytes or entry.flag_bits & 1:
            raise ValueError("oversized or encrypted NPZ member")
        with archive.open(entry) as stream:
            prefix = stream.read(8)
            if prefix not in (b"\x93NUMPY\x01\x00", b"\x93NUMPY\x02\x00"):
                raise ValueError("unsupported NPY format")
            length_bytes = 2 if prefix[-2] == 1 else 4
            length = struct.unpack("<H" if length_bytes == 2 else "<I", stream.read(length_bytes))[0]
            if length > 2048:
                raise ValueError("oversized NPY header")
            header = ast.literal_eval(stream.read(length).decode("latin1"))
            if not isinstance(header, dict) or set(header) != {"descr", "fortran_order", "shape"}:
                raise ValueError("invalid NPY header")
            dtype = np.dtype(header["descr"])
            shape = tuple(case["shape"])
            if header["shape"] != shape or dtype.kind != "c" or dtype.itemsize not in (8, 16):
                raise ValueError("psi must be a correctly shaped complex64/complex128 array")
            if not isinstance(header["fortran_order"], bool):
                raise ValueError("invalid storage order")
            expected = int(np.prod(shape)) * dtype.itemsize
            if entry.file_size != 8 + length_bytes + length + expected:
                raise ValueError("inconsistent array payload")
        payload = archive.read(entry)
    field = np.load(io.BytesIO(payload), allow_pickle=False).astype(np.complex128)
    mask = np.asarray(case["mask"], dtype=bool)
    if not np.isfinite(field).all() or np.max(np.abs(field)) > 1e6:
        raise ValueError("nonfinite or unbounded field")
    if np.any(np.abs(field[~mask]) > 1e-12):
        raise ValueError("nonzero inactive sites")
    return field


def energy_gradient(case, field):
    shape = tuple(case["shape"])
    mask = np.asarray(case["mask"], dtype=bool).ravel()
    field = np.asarray(field, dtype=np.complex128)
    if field.shape != shape or not np.isfinite(field).all():
        raise ValueError("invalid field")
    values = field.ravel()
    real = values.real
    imag = values.imag
    density = real**2 + imag**2
    alpha = np.asarray(case["alpha"], dtype=float).ravel()
    beta = np.asarray(case["beta"], dtype=float).ravel()
    area = float(case["h"])**2
    energy = area * np.sum((alpha * density + beta * density**2 / 2)[mask], dtype=np.float64)
    derivative = 2 * area * (alpha + beta * density)
    real_gradient = derivative * real
    imag_gradient = derivative * imag
    indices = np.arange(values.size).reshape(shape)
    for source_grid, dest_grid, phase_name, weight_name in (
        (indices[:, :-1], indices[:, 1:], "ax", "kx"),
        (indices[:-1, :], indices[1:, :], "ay", "ky"),
    ):
        source = source_grid.ravel()
        dest = dest_grid.ravel()
        keep = mask[source] & mask[dest]
        source, dest = source[keep], dest[keep]
        phases = np.asarray(case[phase_name], dtype=float).ravel()[keep]
        weights = np.asarray(case[weight_name], dtype=float).ravel()[keep]
        cosine, sine = np.cos(phases), np.sin(phases)
        residual_real = real[source] - cosine * real[dest] - sine * imag[dest]
        residual_imag = imag[source] + sine * real[dest] - cosine * imag[dest]
        energy += np.sum(weights * (residual_real**2 + residual_imag**2), dtype=np.float64)
        real_gradient += np.bincount(source, weights=2 * weights * residual_real, minlength=values.size)
        imag_gradient += np.bincount(source, weights=2 * weights * residual_imag, minlength=values.size)
        real_gradient += np.bincount(dest, weights=-2 * weights * (cosine * residual_real - sine * residual_imag), minlength=values.size)
        imag_gradient += np.bincount(dest, weights=-2 * weights * (sine * residual_real + cosine * residual_imag), minlength=values.size)
    gradient = real_gradient + 1j * imag_gradient
    gradient[~mask] = 0
    rms = np.sqrt(np.sum(np.abs(gradient[mask])**2) / (2 * int(mask.sum())))
    return float(energy), gradient.reshape(shape), float(rms)


def lower_bound(case):
    mask = np.asarray(case["mask"], dtype=bool)
    alpha = np.asarray(case["alpha"], dtype=float)
    beta = np.asarray(case["beta"], dtype=float)
    return float(-float(case["h"])**2 * np.sum((np.minimum(alpha, 0)**2 / (2 * beta))[mask]))
