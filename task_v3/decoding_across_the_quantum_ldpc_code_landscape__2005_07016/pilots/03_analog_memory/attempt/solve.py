import argparse
import ctypes
import os
from pathlib import Path
import subprocess
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
from scipy import sparse


def build_model(checks, stabilizers, metachecks, rounds):
    num_checks, num_qubits = checks.shape
    data_count = rounds * num_qubits
    variable_count = data_count + (rounds - 1) * num_checks
    base_rows = rounds * num_checks
    row_indices = []
    column_indices = []
    check_rows, check_columns = np.nonzero(checks)
    meta_rows, meta_columns = np.nonzero(metachecks)
    for interval in range(rounds):
        row_indices.extend((interval * num_checks + check_rows).tolist())
        column_indices.extend((interval * num_qubits + check_columns).tolist())
        if interval < rounds - 1:
            row_indices.extend((interval * num_checks + np.arange(num_checks)).tolist())
            column_indices.extend((data_count + interval * num_checks + np.arange(num_checks)).tolist())
        if interval:
            row_indices.extend((interval * num_checks + np.arange(num_checks)).tolist())
            column_indices.extend((data_count + (interval - 1) * num_checks + np.arange(num_checks)).tolist())
    for interval in range(rounds - 1):
        row_indices.extend((base_rows + interval * len(metachecks) + meta_rows).tolist())
        column_indices.extend((data_count + interval * num_checks + meta_columns).tolist())
    matrix = sparse.coo_matrix(
        (np.ones(len(row_indices), dtype=np.uint8), (row_indices, column_indices)),
        shape=(base_rows + (rounds - 1) * len(metachecks), variable_count),
    ).tocsr()
    moves = []
    for interval in range(rounds):
        for stabilizer in stabilizers:
            support = np.flatnonzero(stabilizer)
            if len(support):
                moves.append((interval * num_qubits + support).tolist())
    for first in range(rounds - 1):
        for last in range(first + 1, rounds):
            for qubit in range(num_qubits):
                support = np.flatnonzero(checks[:, qubit])
                move = [first * num_qubits + qubit, last * num_qubits + qubit]
                for interval in range(first, last):
                    move.extend((data_count + interval * num_checks + support).tolist())
                moves.append(move)
    move_pointers = np.zeros(len(moves) + 1, dtype=np.int32)
    move_pointers[1:] = np.cumsum([len(move) for move in moves])
    move_columns = np.array([column for move in moves for column in move], dtype=np.int32)
    return matrix, base_rows, move_pointers, move_columns


def native_library():
    directory = Path(__file__).resolve().parent
    source = directory / "decoder.cpp"
    library = directory / "decoder.so"
    if not library.exists() or library.stat().st_mtime < source.stat().st_mtime:
        temporary = directory / ("decoder." + str(os.getpid()) + ".so")
        subprocess.run(
            ["g++", "-O3", "-std=c++17", "-shared", "-fPIC", str(source), "-o", str(temporary)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "TMPDIR": str(directory)},
        )
        os.replace(temporary, library)
    result = ctypes.CDLL(str(library))
    pointer = np.ctypeslib.ndpointer
    result.decode.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        pointer(np.int32, flags="C_CONTIGUOUS"),
        pointer(np.int32, flags="C_CONTIGUOUS"),
        pointer(np.float64, flags="C_CONTIGUOUS"),
        pointer(np.uint8, flags="C_CONTIGUOUS"),
        ctypes.c_int,
        pointer(np.int32, flags="C_CONTIGUOUS"),
        pointer(np.int32, flags="C_CONTIGUOUS"),
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_double,
        pointer(np.uint8, flags="C_CONTIGUOUS"),
        pointer(np.float64, flags="C_CONTIGUOUS"),
    ]
    result.decode.restype = ctypes.c_int
    result.refine_history.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        pointer(np.float64, flags="C_CONTIGUOUS"),
        pointer(np.float64, flags="C_CONTIGUOUS"),
        ctypes.c_int,
        pointer(np.int32, flags="C_CONTIGUOUS"),
        pointer(np.int32, flags="C_CONTIGUOUS"),
        ctypes.c_int, ctypes.c_double,
        pointer(np.uint8, flags="C_CONTIGUOUS"),
    ]
    result.refine_history.restype = ctypes.c_int
    return result


def solve_arrays(case, runs=None, iterations=70, order=40, budget=86.0, refine=True,
                 refine_sweeps=800):
    checks = np.asarray(case["checks"], dtype=np.uint8)
    stabilizers = np.asarray(case["stabilizers"], dtype=np.uint8)
    metachecks = np.asarray(case["metachecks"], dtype=np.uint8)
    readout = np.asarray(case["readout"], dtype=np.float64)
    shots, rounds, num_checks = readout.shape
    num_qubits = checks.shape[1]
    mean0 = np.asarray(case["mean0"], dtype=np.float64)
    mean1 = np.asarray(case["mean1"], dtype=np.float64)
    sigma = np.asarray(case["sigma"], dtype=np.float64)
    terminal = np.asarray(case["terminal_syndrome"], dtype=np.uint8)
    likelihood = (mean0 - mean1) * (readout - (mean0 + mean1) / 2) / sigma**2
    hard = (likelihood < 0).astype(np.uint8)
    hard[:, -1] = terminal
    differences = hard.copy()
    differences[:, 1:] ^= hard[:, :-1]
    meta_syndrome = (hard[:, :-1] @ metachecks.T) & 1
    syndrome = np.ascontiguousarray(
        np.concatenate((differences.reshape(shots, -1), meta_syndrome.reshape(shots, -1)), axis=1),
        dtype=np.uint8,
    )
    probability = np.clip(np.asarray(case["data_error_prob"], dtype=np.float64), 1e-12, 1 - 1e-12)
    data_prior = np.log1p(-probability) - np.log(probability)
    priors = np.ascontiguousarray(np.concatenate(
        (np.broadcast_to(data_prior.reshape(1, -1), (shots, rounds * num_qubits)),
         np.abs(likelihood[:, :-1]).reshape(shots, -1)), axis=1), dtype=np.float64)
    priors = np.clip(priors, -100.0, 100.0)
    matrix, base_rows, move_pointers, move_columns = build_model(checks, stabilizers, metachecks, rounds)
    if runs is None:
        runs = 32 if matrix.shape[1] < 1600 else 16
    answer = np.zeros(priors.shape, dtype=np.uint8)
    statistics = np.zeros((shots, 4), dtype=np.float64)
    library = native_library()
    status = library.decode(
        matrix.shape[0], matrix.shape[1], base_rows, shots,
        np.ascontiguousarray(matrix.indptr, dtype=np.int32),
        np.ascontiguousarray(matrix.indices, dtype=np.int32), priors, syndrome,
        len(move_pointers) - 1, move_pointers, move_columns,
        runs, iterations, order, budget, answer, statistics,
    )
    if status:
        raise RuntimeError("Native decoding failed with status " + str(status))
    if refine and rounds > 1:
        state_bias = np.cumprod(1 - 2 * probability, axis=0)
        parity_bias = np.empty((rounds - 1, num_checks))
        for check, support in enumerate(checks):
            parity_bias[:, check] = np.prod(state_bias[:-1, support != 0], axis=1)
        prevalence = np.mean((1 - parity_bias) / 2)
        thresholds = np.ascontiguousarray(np.where(hard[:, :-1], 1 - prevalence, prevalence).reshape(shots, -1))
        status = library.refine_history(
            matrix.shape[1], shots, rounds * num_qubits, priors, thresholds,
            len(move_pointers) - 1, move_pointers, move_columns, refine_sweeps, 16.0, answer,
        )
        if status:
            raise RuntimeError("History refinement failed")
    increments = answer[:, :rounds * num_qubits].reshape(shots, rounds, num_qubits)
    states = np.bitwise_xor.accumulate(increments, axis=1)
    history = (states @ checks.T) & 1
    if not np.array_equal(history[:, -1], terminal):
        raise RuntimeError("Decoder did not satisfy the exact final boundary")
    if np.any((history @ metachecks.T) & 1):
        raise RuntimeError("Input metachecks are inconsistent with decoded history")
    return {"increments": increments, "syndrome_history": history}, statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    start = time.process_time()
    with np.load(arguments.input, allow_pickle=False) as case:
        answer, statistics = solve_arrays(case)
    with open(arguments.output, "wb") as output:
        np.savez_compressed(output, **answer)
    if os.environ.get("DECODER_STATS"):
        print("cpu_seconds", time.process_time() - start, "statistics", statistics.tolist())


if __name__ == "__main__":
    main()
