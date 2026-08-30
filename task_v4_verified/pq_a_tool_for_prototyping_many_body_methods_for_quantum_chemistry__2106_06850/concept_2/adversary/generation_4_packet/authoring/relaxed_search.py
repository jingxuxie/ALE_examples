"""Private state-level relaxation; solutions here are not CCSD witnesses."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["JAX_ENABLE_X64"] = "true"
os.environ["XLA_FLAGS"] = "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1"

import jax
import jax.numpy as jnp
import numpy as np
from scipy.optimize import minimize

PACKET = Path(__file__).resolve().parents[1]
BASE = PACKET.parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
from oracle import DeterminantCC
from api import CONSTRAINTS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--starts", type=int, default=100)
    parser.add_argument("--iterations", type=int, default=700)
    parser.add_argument("--minutes", type=float, default=10)
    parser.add_argument("--dad", type=float, default=0.0009)
    parser.add_argument("--target", type=float, default=0.0201)
    parser.add_argument("--name", default="relaxation")
    parser.add_argument("--nearby-ground", action="store_true")
    parser.add_argument("--overlap", type=float, default=0.999)
    parser.add_argument("--reference", type=float, default=0.45)
    parser.add_argument("--upper", action="store_true")
    parser.add_argument("--rayleigh", action="store_true")
    arguments = parser.parse_args()
    if arguments.rayleigh and not arguments.nearby_ground:
        raise ValueError("Rayleigh compression requires a nearby exact-ground vector")
    started = time.monotonic()
    oracle = DeterminantCC()
    axes = []
    for row in range(15):
        for column in range(row, 15):
            direction = np.zeros((15, 15))
            direction[row, column] = direction[column, row] = 1 if row == column else 1 / np.sqrt(2)
            axes.append(oracle.hamiltonian(np.zeros(6), direction)[0])
    derivatives = jnp.array(axes)
    generators = jnp.array(oracle.generators)
    one = jnp.array(oracle.one)
    reference = jnp.array(oracle.ref)
    targets = jnp.array(oracle.targets)
    identity = jnp.eye(20)
    seeds = []
    for source in (BASE / "champions/generation_3/submission.json", BASE / "attempts/v_3_r2/submission.json",
                   BASE / "champions/generation_2/submission.json", BASE / "adversary/generation_3/private_centered_candidate.json"):
        if not source.exists():
            continue
        data = json.loads(source.read_text())
        matrix, amplitudes = np.array(data["pair_matrix"]), np.array(data["amplitudes"])
        hamiltonian = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], matrix)[0]
        solution = oracle.solve(hamiltonian, amplitudes, tolerance=2e-12)
        multipliers = oracle.lambda_state(solution)[0]
        values = np.r_[solution.amplitudes, multipliers]
        if arguments.nearby_ground:
            ground = np.linalg.eigh(hamiltonian)[1][:, 0]
            values = np.r_[values, ground]
        if arguments.rayleigh:
            left = oracle.lambda_state(solution)[1]
            normal = solution.inverse[-1]
            error = solution.energy - np.linalg.eigvalsh(hamiltonian)[0]
            right_residual = (hamiltonian @ solution.right - solution.energy * solution.right)[-1]
            left_residual = (left @ hamiltonian - solution.energy * left) @ normal / (normal @ normal)
            values = np.r_[values, error / 1e-4, right_residual, left_residual]
        seeds.append(values)
    if not seeds:
        raise ValueError("no completed private seed available")

    def compute(values):
        amplitudes, multipliers = values[:18], values[18:36]
        cluster = jnp.einsum("k,kij->ij", amplitudes, generators)
        square = cluster @ cluster
        cube = square @ cluster / 6
        positive = identity + cluster + square / 2 + cube
        negative = identity - cluster + square / 2 - cube
        right = positive @ reference
        left = reference.at[targets].set(multipliers) @ negative
        right_norm = right @ right
        exact = values[36:56] / jnp.linalg.norm(values[36:56]) if arguments.nearby_ground else right / jnp.sqrt(right_norm)
        gradient = jnp.einsum("i,kij,j->k", left, derivatives, right) - jnp.einsum("i,kij,j->k", exact, derivatives, exact)
        density = jnp.einsum("i,pqij,j->pq", left, one, right)
        anti = density - density.T
        dad = jnp.sqrt(jnp.sum(anti ** 2) / 3 + 1e-30)
        spectrum = jnp.linalg.eigvalsh((density + density.T) / 2)
        occupation = 1 - spectrum[-1] if arguments.upper else spectrum[0]
        constraints = jnp.array([(arguments.dad - dad) * 10, -occupation - arguments.target,
                                  1.25 ** 2 - amplitudes @ amplitudes, 1.5 ** 2 - multipliers @ multipliers,
                                  exact[oracle.reference] ** 2 - arguments.reference])
        if arguments.nearby_ground:
            constraints = jnp.r_[constraints, ((exact @ right) ** 2 / right_norm - arguments.overlap) * 10,
                                 4 - values[36:56] @ values[36:56], values[36:56] @ values[36:56] - 0.25]
        if arguments.rayleigh:
            error, right_residual, left_residual = values[56] * 1e-4, values[57], values[58]
            normal = negative[-1]
            projection_right, projection_left = exact @ right, exact @ left
            gram = jnp.array([[right_norm - projection_right ** 2, 1 - projection_right * projection_left],
                              [1 - projection_right * projection_left, left @ left - projection_left ** 2]])
            compression = jnp.array([[error * right_norm + right_residual * right[-1], error],
                                     [error, error * (left @ left) + left_residual * (normal @ left)]])
            constraints = jnp.r_[constraints, jnp.linalg.eigvalsh(compression - 0.1 * gram)[0],
                (error * projection_right + right_residual * exact[-1]) * 10,
                (error * projection_left + left_residual * (normal @ exact)) * 10]
        objective = gradient @ gradient
        return jnp.r_[objective, constraints], jnp.array([jnp.sqrt(objective), dad, -occupation, exact[oracle.reference] ** 2])

    function = jax.jit(compute)
    derivative = jax.jit(jax.jacfwd(lambda values: compute(values)[0]))
    random = np.random.default_rng(465193)
    best = float("inf")
    records = []
    inequality_slice = slice(1, -2) if arguments.rayleigh else slice(1, None)
    for index in range(arguments.starts):
        if time.monotonic() - started > arguments.minutes * 60:
            break
        initial = seeds[index % len(seeds)].copy()
        if index >= len(seeds):
            initial += random.normal(0, random.choice([0.01, 0.05, 0.15, 0.3]), len(initial))
        cached = {}

        def evaluate(values):
            key = values.tobytes()
            if key not in cached:
                output, information = function(values)
                cached.clear()
                cached[key] = np.array(output), np.array(derivative(values)), np.array(information)
            return cached[key]

        conditions = [{"type": "ineq", "fun": lambda values: evaluate(values)[0][inequality_slice],
                       "jac": lambda values: evaluate(values)[1][inequality_slice]}]
        if arguments.rayleigh:
            conditions.append({"type": "eq", "fun": lambda values: evaluate(values)[0][-2:],
                               "jac": lambda values: evaluate(values)[1][-2:]})
        bounds = [(-1.25, 1.25)] * 18 + [(-1.5, 1.5)] * 18 + ([(-2, 2)] * 20 if arguments.nearby_ground else [])
        if arguments.rayleigh:
            bounds += [(-1, 1), (-1e4, 1e4), (-1e4, 1e4)]
        result = minimize(lambda values: evaluate(values)[0][0], initial, jac=lambda values: evaluate(values)[1][0],
                          method="SLSQP", bounds=bounds, constraints=conditions,
                          options={"maxiter": arguments.iterations, "ftol": 1e-12})
        output, _, info = evaluate(result.x)
        equality_error = float(max(abs(output[-2:]))) if arguments.rayleigh else 0.0
        feasible = bool(min(output[inequality_slice]) >= -1e-7 and equality_error < 1e-7)
        record = {"start": index, "feasible_in_relaxation": feasible, "gradient_norm": float(info[0]),
                  "dad": float(info[1]), "violation": float(info[2]), "reference_weight": float(info[3]),
                  "minimum_margin": float(min(output[inequality_slice])), "equality_error": equality_error,
                  "iterations": result.nit, "message": str(result.message),
                  "elapsed_seconds": time.monotonic() - started}
        print(json.dumps(record), flush=True)
        records.append(record)
        if feasible and info[0] < best:
            best = float(info[0])
            seeds.append(result.x.copy())
            data = {"amplitudes": result.x[:18].tolist(), "multipliers": result.x[18:36].tolist(),
                    "metrics": record, "stationary_hamiltonian_known": False,
                    "warning": "State-level relaxation; not a CCSD Hamiltonian witness and not a proof."}
            if arguments.nearby_ground:
                data["ground_vector"] = (result.x[36:56] / np.linalg.norm(result.x[36:56])).tolist()
            if arguments.rayleigh:
                data["rayleigh_parameters"] = result.x[56:].tolist()
            (PACKET / "authoring" / (arguments.name + "_best.json")).write_text(json.dumps(data, indent=2))
        if feasible and info[0] < 0.085:
            break
    summary = {"best_relaxed_gradient_norm": best if np.isfinite(best) else None, "records": records,
               "runtime_seconds": time.monotonic() - started, "not_a_feasibility_or_impossibility_proof": True}
    (PACKET / "authoring" / (arguments.name + "_summary.json")).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
