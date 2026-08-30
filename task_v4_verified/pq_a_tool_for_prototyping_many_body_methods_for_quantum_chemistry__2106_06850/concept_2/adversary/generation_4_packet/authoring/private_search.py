"""Private joint stationary-CC response-gradient minimization using completed seeds."""

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
sys.path.insert(0, str(BASE / "participant" / "workspace"))
sys.path.insert(0, str(BASE / "champions" / "generation_3"))
from api import CONSTRAINTS, artifact, endpoint_failures, check_continuation
from search import Model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=350)
    parser.add_argument("--dad", type=float, default=0.0)
    parser.add_argument("--energy", type=float, default=1e-7)
    parser.add_argument("--target", type=float, default=0.0205)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    model = Model(full=True, dad=arguments.dad, energy=arguments.energy, target=arguments.target, condition=85, gap=0.11)
    data = json.loads(arguments.source.read_text())
    initial = model.pack(np.array(data["pair_matrix"]), np.array(data["amplitudes"]))
    generators = jnp.array(model.oracle.generators)
    targets = jnp.array(model.oracle.targets)
    reference = jnp.array(model.oracle.ref)
    identity = jnp.eye(model.oracle.size)
    haxes = jnp.array(model.haxes)
    hzero = jnp.array(model.oracle.hamiltonian(CONSTRAINTS["orbital_energies"], np.zeros((15, 15)))[0])

    def equations(values):
        _, equalities, inequalities, information = model.calc(values)
        hamiltonian = hzero + jnp.einsum("k,kij->ij", values[:120], haxes)
        cluster = jnp.einsum("k,kij->ij", values[120:138], generators)
        square = cluster @ cluster
        cube = square @ cluster / 6
        positive = identity + cluster + square / 2 + cube
        negative = identity - cluster + square / 2 - cube
        left = reference.at[targets].set(values[138:]) @ negative
        right = positive @ reference
        _, vectors = jnp.linalg.eigh(hamiltonian)
        gradient = (jnp.einsum("i,kij,j->k", left, haxes, right)
                    - jnp.einsum("i,kij,j->k", vectors[:, 0], haxes, vectors[:, 0]))
        objective = gradient @ gradient + 1e-5 * jnp.sum((values - jnp.array(initial)) ** 2)
        return jnp.concatenate((jnp.array([objective]), equalities, inequalities)), jnp.concatenate((information, jnp.array([jnp.linalg.norm(gradient)])))

    combined = jax.jit(equations)
    derivative = jax.jit(jax.jacfwd(lambda values: equations(values)[0]))
    equality_count = len(np.array(model.calc(initial)[1]))
    cache = {}
    iterations = 0
    best = float("inf")

    def evaluate(values):
        key = values.tobytes()
        if key not in cache:
            output, info = combined(values)
            cache.clear()
            cache[key] = np.array(output), np.array(derivative(values)), np.array(info)
        return cache[key]

    def callback(values):
        nonlocal iterations, best
        output, _, info = evaluate(values)
        iterations += 1
        residual = float(np.max(abs(output[1:1 + equality_count])))
        margin = float(min(output[1 + equality_count:]))
        if iterations % 10 == 0:
            print(json.dumps({"iteration": iterations, "equations": residual, "margin": margin,
                              "gradient_norm": float(info[-1]), "information": info.tolist(),
                              "runtime_seconds": time.monotonic() - started}), flush=True)
        if residual < 2e-8 and margin >= -2e-7 and info[-1] < best:
            matrix, amplitudes = model.unpack(values)
            solved = model.oracle.solve(model.oracle.hamiltonian(CONSTRAINTS["orbital_energies"], matrix)[0], amplitudes,
                                        tolerance=2e-12, max_evaluations=250)
            diagnostics = model.oracle.diagnostics(model.oracle.hamiltonian(CONSTRAINTS["orbital_energies"], matrix)[0], solved)
            if not endpoint_failures(diagnostics):
                best = float(info[-1])
                (arguments.output / "candidate.json").write_text(json.dumps(artifact(matrix, solved.amplitudes), indent=2))
                (arguments.output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
                if best < 0.08 and check_continuation(matrix, solved.amplitudes, model.oracle)["passed"]:
                    raise StopIteration("small-gradient stationary candidate with valid base path")

    message = ""
    try:
        result = minimize(lambda values: evaluate(values)[0][0], initial,
                          jac=lambda values: evaluate(values)[1][0], method="SLSQP", bounds=model.bounds,
                          constraints=[{"type": "eq", "fun": lambda values: evaluate(values)[0][1:1 + equality_count],
                                        "jac": lambda values: evaluate(values)[1][1:1 + equality_count]},
                                       {"type": "ineq", "fun": lambda values: evaluate(values)[0][1 + equality_count:],
                                        "jac": lambda values: evaluate(values)[1][1 + equality_count:]}],
                          callback=callback, options={"maxiter": arguments.iterations, "ftol": 1e-12, "disp": True})
        callback(result.x)
        matrix, amplitudes = model.unpack(result.x)
        (arguments.output / "last_iterate.json").write_text(json.dumps(artifact(matrix, amplitudes), indent=2))
        message = str(result.message)
    except Exception as error:
        message = type(error).__name__ + ": " + str(error)
    summary = {"source": str(arguments.source), "best_stationary_gradient_norm": best if np.isfinite(best) else None,
               "iterations": iterations, "message": message, "runtime_seconds": time.monotonic() - started}
    (arguments.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
