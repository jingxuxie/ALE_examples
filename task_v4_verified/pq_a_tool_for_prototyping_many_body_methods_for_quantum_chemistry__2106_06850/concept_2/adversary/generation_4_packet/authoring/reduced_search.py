"""Private Hamiltonian-only optimization with implicit stationary-CC derivatives."""

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
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact, check_continuation, endpoint_failures, robust_screen


class ReducedModel:
    def __init__(self, source, dad, energy, target):
        self.oracle = oracle = DeterminantCC()
        self.energies = np.array(CONSTRAINTS["orbital_energies"])
        data = json.loads(Path(source).read_text())
        self.amplitudes = np.array(data["amplitudes"])
        self.axes = []
        bounds = []
        for row in range(15):
            for column in range(row, 15):
                axis = np.zeros((15, 15))
                axis[row, column] = axis[column, row] = 1 if row == column else 1 / np.sqrt(2)
                self.axes.append(axis)
                limit = 1.4989 if row == column else 1.4989 * np.sqrt(2)
                bounds.append((-limit, limit))
        self.axes = np.array(self.axes)
        self.bounds = np.array(bounds)
        self.initial = np.einsum("kij,ij->k", self.axes, data["pair_matrix"])
        self.hzero = oracle.hamiltonian(self.energies, np.zeros((15, 15)))[0]
        self.haxes = np.array([oracle.hamiltonian(np.zeros(6), axis)[0] for axis in self.axes])
        hzero, haxes = jnp.array(self.hzero), jnp.array(self.haxes)
        hfzero = jnp.array(oracle.hf_stability(self.hzero))
        hfax = jnp.array([oracle.hf_stability(hamiltonian) for hamiltonian in self.haxes])
        generators = jnp.array(oracle.generators)
        targets = jnp.array(oracle.targets)
        reference = jnp.array(oracle.ref)
        identity = jnp.eye(20)
        one = jnp.array(oracle.one)
        self.last = None

        def calculate(values):
            coordinates, amplitudes, multipliers = values[:120], values[120:138], values[138:]
            hamiltonian = hzero + jnp.einsum("k,kij->ij", coordinates, haxes)
            cluster = jnp.einsum("k,kij->ij", amplitudes, generators)
            square = cluster @ cluster
            cube = square @ cluster / 6
            positive = identity + cluster + square / 2 + cube
            negative = identity - cluster + square / 2 - cube
            hbar = negative @ hamiltonian @ positive
            commutators = hbar @ generators - generators @ hbar
            jacobian = commutators[:, targets, oracle.reference].T
            residual = hbar[targets, oracle.reference]
            lambda_residual = jacobian.T @ multipliers + commutators[:, oracle.reference, oracle.reference]
            left = reference.at[targets].set(multipliers) @ negative
            right = positive @ reference
            exact_values, exact_vectors = jnp.linalg.eigh(hamiltonian)
            exact = exact_vectors[:, 0]
            error = hbar[oracle.reference, oracle.reference] - exact_values[0]
            response = jnp.einsum("i,kij,j->k", left, haxes, right) - jnp.einsum("i,kij,j->k", exact, haxes, exact)
            density = jnp.einsum("i,pqij,j->pq", left, one, right)
            antisymmetry = density - density.T
            asymmetry = jnp.sqrt(jnp.sum(antisymmetry ** 2) / 3 + 1e-16)
            occupation = jnp.linalg.eigvalsh((density + density.T) / 2)[0]
            overlap = (exact @ right) ** 2 / (right @ right)
            hessian = hfzero + jnp.einsum("k,klij->lij", coordinates, hfax)
            real_min, imaginary_min = jnp.linalg.eigvalsh(hessian)[:, 0]
            singular = jnp.linalg.svd(jacobian, compute_uv=False)
            eom_min = jnp.min(jnp.linalg.eigvals(jacobian).real)
            inequalities = jnp.array([(energy - error) * 100, (energy + error) * 100,
                (overlap - 0.999) * 100, exact[oracle.reference] ** 2 - 0.4502,
                exact_values[1] - exact_values[0] - 0.10005, real_min - 0.05005, imaginary_min - 0.05005,
                singular[-1] - singular[0] / 99.9, 1.499 ** 2 - multipliers @ multipliers,
                1.249 ** 2 - amplitudes @ amplitudes, 6.998 ** 2 - coordinates @ coordinates,
                eom_min - 0.05005, (dad - asymmetry) * 100, -occupation - target])
            information = jnp.array([jnp.linalg.norm(response), error, overlap, exact[oracle.reference] ** 2,
                exact_values[1] - exact_values[0], real_min, imaginary_min, singular[0] / singular[-1], asymmetry, -occupation])
            return jnp.r_[response @ response, residual, lambda_residual, inequalities], information, response

        self.function = jax.jit(lambda values: calculate(values)[:2])
        self.derivative = jax.jit(jax.jacfwd(lambda values: calculate(values)[0]))
        self.response_function = jax.jit(lambda values: calculate(values)[2])
        self.response_derivative = jax.jit(jax.jacfwd(lambda values: calculate(values)[2]))
        self.cache = {}

    def evaluate(self, coordinates):
        key = coordinates.tobytes()
        if key not in self.cache:
            hamiltonian = self.hzero + np.einsum("k,kij->ij", coordinates, self.haxes)
            solution = self.oracle.solve(hamiltonian, self.amplitudes, tolerance=2e-12, max_evaluations=300)
            if not solution.converged or solution.residual > 1e-9:
                solution = self.oracle.solve(hamiltonian, tolerance=2e-12, max_evaluations=300)
            if not solution.converged or solution.residual > 1e-9:
                raise ValueError("Hamiltonian-only step left convergent branch")
            multipliers = self.oracle.lambda_state(solution)[0]
            values = np.r_[coordinates, solution.amplitudes, multipliers]
            output, info = self.function(values)
            output, info = np.array(output), np.array(info)
            derivative = np.array(self.derivative(values))
            implicit = np.linalg.solve(derivative[1:37, 120:], -derivative[1:37, :120])
            reduced = derivative[:, :120] + derivative[:, 120:] @ implicit
            self.last = values.copy()
            self.cache.clear()
            self.cache[key] = output, reduced, info, values
        return self.cache[key]

    def stationary_response(self, coordinates):
        values = self.evaluate(coordinates)[3]
        derivative = np.array(self.derivative(values))
        implicit = np.linalg.solve(derivative[1:37, 120:], -derivative[1:37, :120])
        response_derivative = np.array(self.response_derivative(values))
        return np.array(self.response_function(values)), response_derivative[:, :120] + response_derivative[:, 120:] @ implicit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stages", type=int, default=12)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--minutes", type=float, default=15)
    parser.add_argument("--dad", type=float, default=0.0002)
    parser.add_argument("--energy", type=float, default=5e-6)
    parser.add_argument("--target", type=float, default=0.0201)
    parser.add_argument("--step", type=float, default=0.08)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    model = ReducedModel(arguments.source, arguments.dad, arguments.energy, arguments.target)
    center = model.initial.copy()
    best = float("inf")
    iterations = 0
    records = []
    retained = None

    def callback(coordinates):
        nonlocal iterations, best, retained
        output, _, info, full = model.evaluate(coordinates)
        if info[2] > 0.995:
            model.amplitudes = full[120:138].copy()
        iterations += 1
        margin = float(min(output[37:]))
        if iterations % 10 == 0:
            print(json.dumps({"iteration": iterations, "minimum_margin": margin, "information": info.tolist(),
                              "elapsed_seconds": time.monotonic() - started}), flush=True)
        if margin >= -1e-8 and info[0] < best:
            best = float(info[0])
            matrix = np.einsum("k,kij->ij", coordinates, model.axes)
            retained = coordinates.copy()
            data = artifact(matrix, full[120:138])
            (arguments.output / "candidate.json").write_text(json.dumps(data, indent=2))
            (arguments.output / "candidate_metrics.json").write_text(json.dumps({"gradient_norm": best, "information": info.tolist()}))
            if best < 0.1:
                check = robust_screen(matrix, full[120:138], model.oracle, check_paths=False)
                (arguments.output / "endpoint_screen.json").write_text(json.dumps(check, indent=2))
                if check.get("endpoint_feasible") and check["worst_population_violation"] >= 0.02:
                    raise StopIteration("all 243 endpoints pass; independent certificates required")
        if time.monotonic() - started > arguments.minutes * 60:
            raise StopIteration("private search time budget")

    for stage in range(arguments.stages):
        lower = np.maximum(model.bounds[:, 0], center - arguments.step)
        upper = np.minimum(model.bounds[:, 1], center + arguments.step)
        try:
            result = minimize(lambda values: model.evaluate(values)[0][0], center,
                              jac=lambda values: model.evaluate(values)[1][0], method="SLSQP",
                              bounds=list(zip(lower, upper)),
                              constraints=[{"type": "ineq", "fun": lambda values: model.evaluate(values)[0][37:],
                                            "jac": lambda values: model.evaluate(values)[1][37:]}],
                              callback=callback, options={"maxiter": arguments.iterations, "ftol": 1e-12})
            callback(result.x)
            center = result.x.copy()
            output, _, info, full = model.evaluate(center)
            matrix = np.einsum("k,kij->ij", center, model.axes)
            (arguments.output / "last_iterate.json").write_text(json.dumps(artifact(matrix, full[120:138]), indent=2))
            record = {"stage": stage, "message": str(result.message), "minimum_margin": float(min(output[37:])),
                      "information": info.tolist(), "elapsed_seconds": time.monotonic() - started}
            records.append(record)
            print(json.dumps(record), flush=True)
        except StopIteration as error:
            records.append({"stage": stage, "stop": str(error)})
            break
        except Exception as error:
            records.append({"stage": stage, "error": type(error).__name__ + ": " + str(error)})
            print(json.dumps(records[-1]), flush=True)
            if retained is not None:
                center = retained.copy()
            arguments.step *= 0.5
        if time.monotonic() - started > arguments.minutes * 60:
            break
    summary = {"best_base_feasible_gradient_norm": best if np.isfinite(best) else None,
               "records": records, "runtime_seconds": time.monotonic() - started}
    (arguments.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
