"""Private inverse Hamiltonian feasibility at fixed relaxed right/left states."""

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
from scipy.linalg import null_space
from scipy.optimize import minimize

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact, endpoint_failures, robust_screen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--condition", action="store_true")
    parser.add_argument("--iterations", type=int, default=1000)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    data = json.loads(arguments.source.read_text())
    oracle = DeterminantCC()
    amplitudes = np.array(data["amplitudes"])
    multipliers = np.array(data["multipliers"])
    positive, negative = oracle.exponentials(amplitudes)
    right = positive @ oracle.ref
    ground = np.array(data.get("ground_vector", right / np.linalg.norm(right)))
    orthogonal = null_space(ground[None, :])
    axes = []
    for row in range(15):
        for column in range(row, 15):
            axis = np.zeros((15, 15))
            axis[row, column] = axis[column, row] = 1 if row == column else 1 / np.sqrt(2)
            axes.append(axis)
    axes = np.array(axes)
    hzero = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], np.zeros((15, 15)))[0]
    haxes = np.array([oracle.hamiltonian(np.zeros(6), axis)[0] for axis in axes])

    def linear_equations(hamiltonian):
        hbar = negative @ hamiltonian @ positive
        commutators = hbar @ oracle.generators - oracle.generators @ hbar
        jacobian = commutators[:, oracle.targets, oracle.reference].T
        lambda_residual = jacobian.T @ multipliers + commutators[:, oracle.reference, oracle.reference]
        return np.r_[hbar[oracle.targets, oracle.reference], lambda_residual, orthogonal.T @ hamiltonian @ ground]

    constraint_matrix = np.array([linear_equations(hamiltonian) for hamiltonian in haxes]).T
    offset = linear_equations(hzero)
    particular = np.linalg.lstsq(constraint_matrix, -offset, rcond=1e-11)[0]
    kernel = null_space(constraint_matrix, rcond=1e-11)
    consistency = float(max(abs(constraint_matrix @ particular + offset)))
    print(json.dumps({"linear_consistency_error": consistency, "null_dimension": kernel.shape[1],
                      "particular_frobenius_norm": float(np.linalg.norm(particular))}), flush=True)
    if consistency > 1e-8:
        (arguments.output / "summary.json").write_text(json.dumps({"fixed_state_linear_inconsistency": consistency,
            "scope": "this fixed relaxed state only, not a universal obstruction"}, indent=2))
        return
    hzero_j, haxes_j, axes_j = jnp.array(hzero), jnp.array(haxes), jnp.array(axes)
    particular_j, kernel_j = jnp.array(particular), jnp.array(kernel)
    ground_j, orthogonal_j = jnp.array(ground), jnp.array(orthogonal)
    hfzero = jnp.array(oracle.hf_stability(hzero))
    hfax = jnp.array([oracle.hf_stability(hamiltonian) for hamiltonian in haxes])
    positive_j, negative_j = jnp.array(positive), jnp.array(negative)
    generators_j = jnp.array(oracle.generators)
    targets_j = jnp.array(oracle.targets)

    def calculate(values):
        coordinates = particular_j + kernel_j @ values[:-1]
        slack = values[-1]
        hamiltonian = hzero_j + jnp.einsum("k,kij->ij", coordinates, haxes_j)
        matrix = jnp.einsum("k,kij->ij", coordinates, axes_j)
        exact_energy = ground_j @ hamiltonian @ ground_j
        hbar = negative_j @ hamiltonian @ positive_j
        error = hbar[oracle.reference, oracle.reference] - exact_energy
        gap = jnp.linalg.eigvalsh(orthogonal_j.T @ hamiltonian @ orthogonal_j)[0] - exact_energy
        hf = jnp.linalg.eigvalsh(hfzero + jnp.einsum("k,klij->lij", coordinates, hfax))[:, 0]
        inequalities = jnp.r_[(1e-4 - error) * 100, (1e-4 + error) * 100, gap - 0.1,
                              hf - 0.05, (49 - coordinates @ coordinates) / 7,
                              (1.4989 - matrix).reshape(-1), (1.4989 + matrix).reshape(-1)]
        if arguments.condition:
            commutators = hbar @ generators_j - generators_j @ hbar
            jacobian = commutators[:, targets_j, oracle.reference].T
            singular = jnp.linalg.svd(jacobian, compute_uv=False)
            eom = jnp.linalg.eigvals(jacobian)
            inequalities = jnp.r_[inequalities, singular[-1] - singular[0] / 100, jnp.min(eom.real) - 0.05]
        objective = slack + 1e-6 * coordinates @ coordinates
        return jnp.r_[objective, inequalities + slack], jnp.array([slack, error, gap, hf[0], hf[1], jnp.linalg.norm(coordinates)])

    function = jax.jit(calculate)
    derivative = jax.jit(jax.jacfwd(lambda values: calculate(values)[0]))
    initial = np.r_[np.zeros(kernel.shape[1]), 10.0]
    cache = {}
    iterations = 0

    def evaluate(values):
        key = values.tobytes()
        if key not in cache:
            output, information = function(values)
            cache.clear()
            cache[key] = np.array(output), np.array(derivative(values)), np.array(information)
        return cache[key]

    def callback(values):
        nonlocal iterations
        iterations += 1
        if iterations % 25 == 0:
            print(json.dumps({"iteration": iterations, "information": evaluate(values)[2].tolist(),
                              "elapsed_seconds": time.monotonic() - started}), flush=True)

    result = minimize(lambda values: evaluate(values)[0][0], initial, jac=lambda values: evaluate(values)[1][0],
                      method="SLSQP", bounds=[(-100, 100)] * kernel.shape[1] + [(0, 100)],
                      constraints=[{"type": "ineq", "fun": lambda values: evaluate(values)[0][1:],
                                    "jac": lambda values: evaluate(values)[1][1:]}],
                      callback=callback, options={"maxiter": arguments.iterations, "ftol": 1e-12})
    coordinates = particular + kernel @ result.x[:-1]
    matrix = np.einsum("k,kij->ij", coordinates, axes)
    hamiltonian = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], matrix)[0]
    solution = oracle.solve(hamiltonian, amplitudes, tolerance=2e-12)
    diagnostics = oracle.diagnostics(hamiltonian, solution)
    (arguments.output / "candidate.json").write_text(json.dumps(artifact(matrix, solution.amplitudes), indent=2))
    (arguments.output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
    report = {"linear_consistency_error": consistency, "slack": float(result.x[-1]), "message": str(result.message),
              "information": evaluate(result.x)[2].tolist(), "endpoint_failures": endpoint_failures(diagnostics),
              "actual_gradient_scope": "fixed state only; no universal conclusion", "runtime_seconds": time.monotonic() - started}
    (arguments.output / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
