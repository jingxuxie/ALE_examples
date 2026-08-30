"""Bounded, generation-time-only audit; frozen sources are read but never changed."""

import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "participant/baseline"))
sys.path.insert(0, str(ROOT / "evaluator"))
import numpy as np
import contractor
import mps
from hidden.suite import cases

resource.setrlimit(resource.RLIMIT_CPU, (80, 85))


def emit(record):
    print(json.dumps(record, allow_nan=False), flush=True)
    with (OUTPUT / "events.jsonl").open("a") as stream:
        stream.write(json.dumps(record, allow_nan=False) + "\n")


def pair_kernel(left, right, first_mpo, second_mpo, shape):
    def matvec(vector):
        tensor = vector.reshape(shape)
        temporary = np.einsum("awb,bqsf->awqsf", left, tensor, optimize=True)
        temporary = np.einsum("awqsf,wxpq->axpsf", temporary, first_mpo, optimize=True)
        temporary = np.einsum("axpsf,xyrs->ayprf", temporary, second_mpo, optimize=True)
        return np.einsum("ayprf,cyf->aprc", temporary, right, optimize=True).ravel()
    return matvec


PAIR_RECORDS = []


def bounded_ritz_pair(first, second, left, right, first_mpo, second_mpo,
                      cap, direction, tolerance, maxiter):
    beginning = time.process_time()
    theta = np.tensordot(first, second, axes=(2, 0))
    shape = theta.shape
    matvec = pair_kernel(left, right, first_mpo, second_mpo, shape)
    vector = theta.ravel() / np.linalg.norm(theta)
    basis = np.empty((vector.size, 32), dtype=vector.dtype)
    products = np.empty_like(basis)
    original_energy = None
    residual_norm = None
    for iteration in range(32):
        basis[:, iteration] = vector
        products[:, iteration] = matvec(vector)
        active = basis[:, :iteration + 1]
        active_products = products[:, :iteration + 1]
        projected = active.conj().T @ active_products
        projected = (projected + projected.conj().T) / 2
        values, vectors = np.linalg.eigh(projected)
        best = active @ vectors[:, 0]
        image = active_products @ vectors[:, 0]
        if original_energy is None:
            original_energy = float(values[0])
        residual = image - values[0] * best
        residual_norm = float(np.linalg.norm(residual))
        if residual_norm < 1e-6 or time.process_time() - beginning > 0.6:
            break
        for _ in range(2):
            residual -= active @ (active.conj().T @ residual)
        norm = np.linalg.norm(residual)
        if norm < 1e-12:
            break
        vector = residual / norm
    matrix = best.reshape(shape[0] * shape[1], shape[2] * shape[3])
    left_vectors, values, right_vectors = np.linalg.svd(matrix, full_matrices=False)
    rank = min(cap, len(values))
    values = values[:rank]
    values /= np.linalg.norm(values)
    truncated = ((left_vectors[:, :rank] * values) @ right_vectors[:rank]).ravel()
    truncated_energy = float(np.vdot(truncated, matvec(truncated)).real)
    if truncated_energy > original_energy + 1e-10:
        matrix = theta.reshape(shape[0] * shape[1], shape[2] * shape[3]) / np.linalg.norm(theta)
        left_vectors, values, right_vectors = np.linalg.svd(matrix, full_matrices=False)
        rank = min(cap, len(values))
        values = values[:rank]
        values /= np.linalg.norm(values)
    if direction == "right":
        result = (left_vectors[:, :rank].reshape(shape[0], shape[1], rank),
                  (values[:, None] * right_vectors[:rank]).reshape(rank, shape[2], shape[3]))
    else:
        result = ((left_vectors[:, :rank] * values).reshape(shape[0], shape[1], rank),
                  right_vectors[:rank].reshape(rank, shape[2], shape[3]))
    PAIR_RECORDS.append({"shape": list(shape), "matvecs": iteration + 2,
                         "cpu_seconds": time.process_time() - beginning,
                         "residual_norm": residual_norm,
                         "local_improvement": original_energy - truncated_energy})
    return result


def main():
    frozen = [ROOT / "participant/baseline/mps.py", ROOT / "evaluator/hidden/calibrate.py"]
    emit({"event": "start", "pid": os.getpid(),
          "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in frozen}})
    try:
        from threadpoolctl import threadpool_info
        emit({"event": "threadpools", "info": threadpool_info()})
    except ImportError:
        pass
    for family, request in cases():
        identity = request["case_id"]
        if identity not in ("q7f1", "m2b8"):
            continue
        records = []
        for stage in ("short", "long"):
            path = ROOT / "evaluator/hidden/states" / (identity + "_baseline_" + stage + ".npz")
            tensors = contractor.load_mps(path, request)
            measured = contractor.measure(tensors, request)
            records.append((measured["energy"], tensors))
            emit({"event": "baseline", "case_id": identity, "stage": stage,
                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "measurement": measured, "shapes": [list(tensor.shape) for tensor in tensors]})
        baseline_energy, tensors = min(records, key=lambda record: record[0])
        mpo = mps.make_mpo(request, parity_bias={"any": 0, "even": 2, "odd": -2}[request["sector"]])
        canonical = mps.right_canonical(tensors)
        site = len(tensors) // 2 - 1
        left = np.ones((1, 1, 1))
        for index in range(site):
            left = mps.left_step(left, canonical[index], mpo[index])
        right = np.ones((1, 1, 1))
        for index in range(len(tensors) - 1, site + 1, -1):
            right = mps.right_step(right, canonical[index], mpo[index])
        theta = np.tensordot(canonical[site], canonical[site + 1], axes=(2, 0))
        expression = "awb,wxpq,xyrs,cyf,bqsf->aprc"
        arguments = (left, mpo[site], mpo[site + 1], right, theta)
        path, description = np.einsum_path(expression, *arguments, optimize="greedy")
        start = time.process_time()
        original = np.einsum(expression, *arguments, optimize=path).ravel()
        original_cpu = time.process_time() - start
        start = time.process_time()
        sequential = pair_kernel(left, right, mpo[site], mpo[site + 1], theta.shape)(theta.ravel())
        sequential_cpu = time.process_time() - start
        emit({"event": "kernel", "case_id": identity, "shape": list(theta.shape),
              "greedy_cpu": original_cpu, "sequential_cpu": sequential_cpu,
              "max_difference": float(np.max(np.abs(original - sequential))),
              "einsum_path": description})
        beginning = time.process_time()
        pair_start = len(PAIR_RECORDS)
        original_pair = mps.optimize_pair
        mps.optimize_pair = bounded_ritz_pair
        best_energy = baseline_energy
        try:
            for sweep_index in range(3):
                tensors = mps.sweep(tensors, mpo, request["bond_cap"],
                                    deadline=beginning + 18.0)
                try:
                    measured = contractor.measure(tensors, request)
                    emit({"event": "bounded_warm_sweep", "case_id": identity,
                          "sweep": sweep_index + 1, "cpu_seconds": time.process_time() - beginning,
                          "measurement": measured, "baseline_gap": baseline_energy - measured["energy"]})
                    if measured["energy"] < best_energy:
                        best_energy = measured["energy"]
                        contractor.save_mps(OUTPUT / (identity + "_probe_reference.npz"), tensors)
                except ValueError as error:
                    emit({"event": "invalid_probe_state", "case_id": identity, "error": str(error)})
                if time.process_time() - beginning >= 18.0:
                    break
        finally:
            mps.optimize_pair = original_pair
        emit({"event": "pair_profile", "case_id": identity, "pairs": PAIR_RECORDS[pair_start:],
              "best_gap": baseline_energy - best_energy})
    emit({"event": "finished", "total_process_cpu": time.process_time()})


if __name__ == "__main__":
    main()
