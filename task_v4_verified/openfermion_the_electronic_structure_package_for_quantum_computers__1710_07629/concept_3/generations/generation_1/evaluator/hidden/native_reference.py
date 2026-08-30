"""Double-precision source Hamiltonian with native matvec and SciPy ARPACK."""

import ctypes
from pathlib import Path
import time

import numpy as np
from scipy.sparse.linalg import LinearOperator

from exact import ground_state, sector_matrix, spin_kinetic


DOUBLE_POINTER = ctypes.POINTER(ctypes.c_double)
INDEX_POINTER = ctypes.POINTER(ctypes.c_int32)
LIBRARY = ctypes.CDLL(str(Path(__file__).resolve().with_name("reference_matvec.so")))
LIBRARY.apply_sector.argtypes = [ctypes.c_int, ctypes.c_int,
    INDEX_POINTER, INDEX_POINTER, DOUBLE_POINTER, INDEX_POINTER, INDEX_POINTER, DOUBLE_POINTER,
    DOUBLE_POINTER, DOUBLE_POINTER, DOUBLE_POINTER, DOUBLE_POINTER, DOUBLE_POINTER]
LIBRARY.apply_sector.restype = None


def pointer(values, pointer_type=DOUBLE_POINTER):
    return values.ctypes.data_as(pointer_type)


def native_operator(hopping, interaction, potential, up_count, down_count):
    up_matrix, up_occupation = spin_kinetic(hopping, up_count)
    down_matrix, down_occupation = spin_kinetic(hopping, down_count)
    up_offsets = np.ascontiguousarray(up_matrix.indptr, dtype=np.int32)
    up_columns = np.ascontiguousarray(up_matrix.indices, dtype=np.int32)
    up_values = np.ascontiguousarray(up_matrix.data, dtype=np.float64)
    down_offsets = np.ascontiguousarray(down_matrix.indptr, dtype=np.int32)
    down_columns = np.ascontiguousarray(down_matrix.indices, dtype=np.int32)
    down_values = np.ascontiguousarray(down_matrix.data, dtype=np.float64)
    diagonal = np.ascontiguousarray(((up_occupation * interaction) @ down_occupation.T
        + (up_occupation @ potential)[:, None] + (down_occupation @ potential)[None, :]).ravel())
    transposed = np.empty_like(diagonal)
    product = np.empty_like(diagonal)
    counters = {"matvec_count": 0, "matvec_cpu_seconds": 0.0}

    def matvec(vector):
        vector = np.ascontiguousarray(vector, dtype=np.float64)
        result = np.empty_like(vector)
        started = time.process_time()
        LIBRARY.apply_sector(len(up_occupation), len(down_occupation),
            pointer(up_offsets, INDEX_POINTER), pointer(up_columns, INDEX_POINTER), pointer(up_values),
            pointer(down_offsets, INDEX_POINTER), pointer(down_columns, INDEX_POINTER), pointer(down_values),
            pointer(diagonal), pointer(vector), pointer(result), pointer(transposed), pointer(product))
        counters["matvec_count"] += 1
        counters["matvec_cpu_seconds"] += time.process_time() - started
        return result

    operator = LinearOperator((len(diagonal), len(diagonal)), matvec=matvec, dtype=np.float64)
    return operator, counters


def label(hopping, interaction, potential, seed=871, tolerance=1e-10, action_check=False, ncv=16):
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    half = len(hopping) // 2
    energies, residuals, details = [], [], []
    for up_count, down_count in ((half, half), (half, half - 1), (half + 1, half), (half + 1, half - 1)):
        operator, counters = native_operator(hopping, interaction, potential, up_count, down_count)
        tick = time.process_time()
        energy, residual, vector = ground_state(operator, seed=seed, tolerance=tolerance, ncv=ncv)
        solver_seconds = time.process_time() - tick
        independent_residual = None
        if action_check:
            matrix = sector_matrix(hopping, interaction, potential, up_count, down_count)
            independent_residual = float(np.linalg.norm(matrix @ vector - energy * vector))
            if independent_residual > 2e-8:
                raise RuntimeError(f"Full-CSR action check failed: {independent_residual}")
            del matrix
        energies.append(energy)
        residuals.append(residual)
        details.append({"sector": [up_count, down_count], "dimension": operator.shape[0],
                        "solver_cpu_seconds": solver_seconds, **counters,
                        "full_csr_eigenpair_residual": independent_residual})
    gaps = [energies[1] + energies[2] - 2.0 * energies[0], energies[3] - energies[0]]
    return {"gaps": gaps, "energies": energies, "residuals": residuals, "sectors": details,
            "wall_seconds": time.perf_counter() - wall_started,
            "cpu_seconds": time.process_time() - cpu_started}
