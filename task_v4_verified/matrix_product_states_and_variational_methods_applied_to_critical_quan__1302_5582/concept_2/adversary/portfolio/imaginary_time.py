import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import time

import numpy as np
import scipy.linalg as sla
import scipy.sparse.linalg as spla

sys.path.insert(0, str(ROOT.parents[1] / "evaluator" / "hidden"))
import trusted_physics


def fixed_point(tensor, left=False):
    dimension = tensor.shape[1]
    half = dimension // 2
    even = tensor[0, :half, :half]
    odd = tensor[0, half:, half:]
    upper = tensor[1, :half, half:]
    lower = tensor[1, half:, :half]
    def action(vector):
        first, second = vector.reshape(2, half, half)
        if left:
            output_first = even.T @ first @ even + lower.T @ second @ lower
            output_second = upper.T @ first @ upper + odd.T @ second @ odd
        else:
            output_first = even @ first @ even.T + upper @ second @ upper.T
            output_second = lower @ first @ lower.T + odd @ second @ odd.T
        return np.stack((output_first, output_second)).reshape(-1)
    operator = spla.LinearOperator((2*half**2, 2*half**2), matvec=action, dtype=np.float64)
    initial = np.stack((np.eye(half), np.eye(half))).reshape(-1)
    if initial.size <= 3:
        dense = np.column_stack([action(column) for column in np.eye(initial.size)])
        values, vectors = sla.eig(dense)
        index = np.argmax(values.real)
        value, vector = values[index], vectors[:, index]
    else:
        values, vectors = spla.eigs(operator, k=1, which="LR", v0=initial, tol=1e-11, ncv=min(32, initial.size))
        value, vector = values[0], vectors[:, 0]
    blocks = vector.real.reshape(2, half, half)
    if np.trace(blocks[0]) + np.trace(blocks[1]) < 0:
        blocks *= -1
    blocks = (blocks + blocks.transpose(0, 2, 1)) / 2
    result = sla.block_diag(*blocks)
    result /= np.trace(result)
    return value.real, result


def canonicalize(tensor, left_needed=False):
    value, right = fixed_point(tensor)
    half = tensor.shape[1] // 2
    roots = []
    inverses = []
    for sector in range(2):
        block = right[sector*half:(sector+1)*half, sector*half:(sector+1)*half]
        values, vectors = sla.eigh(block)
        values = np.maximum(values, 1e-15)
        roots.append((vectors * np.sqrt(values)) @ vectors.T)
        inverses.append((vectors / np.sqrt(values)) @ vectors.T)
    root = sla.block_diag(*roots)
    inverse = sla.block_diag(*inverses)
    canonical = np.stack([inverse @ matrix @ root / np.sqrt(value) for matrix in tensor])
    if left_needed:
        _, density = fixed_point(canonical, left=True)
        return canonical, density
    return canonical


def apply_layer(tensor, step, field):
    dimension = tensor.shape[1]
    half = dimension // 2
    onsite = np.exp(np.array([1.0, -1.0]) * step * field / 2)
    coefficients = np.sqrt(np.array([np.cosh(step), np.sinh(step)]))
    result = np.zeros((2, 2*dimension, 2*dimension))
    for row_bond in range(2):
        for column_bond in range(2):
            for physical in range(2):
                previous = physical ^ row_bond ^ column_bond
                block = tensor[previous] * onsite[previous] * onsite[physical]
                result[physical, row_bond*dimension:(row_bond+1)*dimension,
                       column_bond*dimension:(column_bond+1)*dimension] = coefficients[row_bond] * coefficients[column_bond] * block
    permutation = np.concatenate((np.arange(half), dimension+np.arange(half, dimension),
                                  np.arange(half, dimension), dimension+np.arange(half)))
    return result[:, permutation][:, :, permutation]


def compress(tensor, dimension):
    canonical, density = canonicalize(tensor, left_needed=True)
    half = tensor.shape[1] // 2
    kept = dimension // 2
    if dimension < tensor.shape[1]:
        bases = []
        for sector in range(2):
            block = density[sector*half:(sector+1)*half, sector*half:(sector+1)*half]
            _, vectors = sla.eigh(block)
            bases.append(vectors[:, -kept:])
        basis = sla.block_diag(*bases)
        canonical = np.stack([basis.T @ matrix @ basis for matrix in canonical])
        canonical = canonicalize(canonical)
    return canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="imaginary_time")
    parser.add_argument("--dimension", type=int, default=24)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--field", type=float, default=1.0)
    parser.add_argument("--resume")
    arguments = parser.parse_args()
    destination = ROOT / arguments.name
    destination.mkdir(parents=True, exist_ok=True)
    if arguments.resume:
        tensor = np.load(arguments.resume, allow_pickle=False)["A"].real
    else:
        angles = [0.18, 1.1]
        tensor = np.array([[[np.cos(angles[0]), 0], [0, np.cos(angles[1])]],
                           [[0, np.sin(angles[0])], [np.sin(angles[1]), 0]]])
    started = time.monotonic()
    best = -1.0
    iteration = 0
    log = (destination / "progress.jsonl").open("a", buffering=1)
    for step, count in ((0.2, 150), (0.1, 200), (0.05, 300), (0.02, 400), (0.01, 400), (0.005, 400), (0.002, 400)):
        for local_iteration in range(count):
            if time.monotonic() - started > arguments.seconds:
                return
            tensor = compress(apply_layer(tensor, step, arguments.field), min(arguments.dimension, 2*tensor.shape[1]))
            iteration += 1
            if local_iteration % 50 == 49 or local_iteration == count - 1:
                checkpoint = destination / f"layer_{iteration:05d}.npz"
                np.savez(checkpoint, A=tensor)
                result = trusted_physics.check(checkpoint)
                (destination / f"layer_{iteration:05d}.score.json").write_text(json.dumps(result, indent=2) + "\n")
                values = result.get("metrics", {})
                summary = {"iteration": iteration, "step": step, "elapsed": time.monotonic()-started,
                           "valid": result.get("valid"), "reason": result.get("reason"),
                           "core_score": result.get("core_score"), "worst_family_score": result.get("worst_family_score"),
                           "energy_excess": values.get("energy_excess"),
                           "order_max_relative_error": values.get("order_max_relative_error"),
                           "density_max_relative_error": values.get("density_max_relative_error")}
                log.write(json.dumps(summary) + "\n")
                print(json.dumps(summary), flush=True)
                np.savez(destination / "latest.npz", A=tensor)
                if result.get("worst_family_score", 0) > best:
                    best = result.get("worst_family_score", 0)
                    np.savez(destination / "state.npz", A=tensor)
                    (destination / "score.json").write_text(json.dumps(result, indent=2) + "\n")
                if result.get("passed"):
                    return


if __name__ == "__main__":
    main()
