"""Private analytic-gradient DAD minimization; never participant-visible."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import solve
from scipy.optimize import minimize

BASE = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "participant" / "workspace"))
sys.path.insert(0, str(BASE / "champions" / "generation_1"))
sys.path.insert(0, str(BASE / "evaluator"))

from api import artifact, check_continuation, endpoint_failures
from evaluate import evaluate_artifact
from optimize import Search


class DADSearch(Search):
    def __init__(self, mode, directory, target):
        super().__init__(mode)
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.target = target
        self.dad_parameters = None
        self.dad_values = None
        self.best_dad = float("inf")
        self.iteration = 0
        self.passing = False

    def evaluate(self, parameters):
        if self.dad_parameters is not None and np.array_equal(parameters, self.dad_parameters):
            return self.dad_values
        population, population_derivative, margins, derivatives = super().evaluate(parameters)
        oracle = self.oracle
        result = self.result
        positive, inverse = oracle.exponentials(result.amplitudes)
        multipliers, left, _ = oracle.lambda_state(result)
        right = result.right
        fixed = inverse @ self.basis @ positive
        amplitude_derivative = solve(result.jacobian, -fixed[:, oracle.targets, oracle.reference].T).T
        cluster_derivative = (amplitude_derivative @ oracle.generator_flat).reshape(120, 20, 20)
        hbar_derivative = fixed + result.hbar @ cluster_derivative - cluster_derivative @ result.hbar
        jacobian_derivative = hbar_derivative[:, oracle.targets[:, None], oracle.targets]
        jacobian_derivative -= np.einsum("nij,kj->kin", oracle.generators[:, oracle.targets, :],
                                        hbar_derivative[:, :, oracle.reference])
        gradient_derivative = hbar_derivative[:, oracle.reference, oracle.targets]
        multiplier_derivative = solve(result.jacobian.T, -(gradient_derivative
                                     + np.einsum("kin,i->kn", jacobian_derivative, multipliers)).T).T
        right_derivative = np.einsum("kij,j->ki", cluster_derivative, right)
        left_derivative = multiplier_derivative @ inverse[oracle.targets, :] - np.einsum("i,kij->kj", left, cluster_derivative)
        density = oracle.rdm(left, right)
        density_derivative = (np.einsum("ki,pqij,j->kpq", left_derivative, oracle.one, right)
                              + np.einsum("i,pqij,kj->kpq", left, oracle.one, right_derivative))
        antisymmetric = density - density.T
        antisymmetric_derivative = density_derivative - density_derivative.transpose(0, 2, 1)
        dad = float(np.linalg.norm(antisymmetric, ord="fro") / np.sqrt(3))
        dad_derivative = np.einsum("pq,kpq->k", antisymmetric, antisymmetric_derivative) / max(3 * dad, 1e-30)
        margins = np.append(margins, -population - self.target)
        derivatives = np.vstack((derivatives, -population_derivative))
        self.info["rdm_dad"] = dad
        self.dad_parameters = parameters.copy()
        self.dad_values = (dad, dad_derivative, margins, derivatives)
        return self.dad_values

    def callback(self, parameters):
        dad, _, margins, _ = self.evaluate(parameters)
        self.iteration += 1
        if self.iteration % 5 == 0:
            print(json.dumps({"iteration": self.iteration, "min_margin": float(min(margins)),
                              "evaluations": self.evaluations, **self.info}), flush=True)
        if min(margins) >= -1e-7 and self.result.residual < 2e-9 and dad < self.best_dad:
            self.best_dad = dad
            candidate = artifact(self.unpack(parameters), self.result.amplitudes)
            path = self.directory / "closest_candidate.json"
            path.write_text(json.dumps(candidate, indent=2, allow_nan=False))
            (self.directory / "closest_diagnostics.json").write_text(json.dumps(self.info, indent=2, allow_nan=False))
            if dad <= 0.001:
                report = evaluate_artifact(path, self.directory)
                (self.directory / "independent_evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False))
                self.passing = report["passed"]
                if self.passing:
                    raise StopIteration("independently verified generation-two witness")

    def run_private(self, parameters, iterations):
        self.callback(parameters)
        return minimize(lambda value: self.evaluate(value)[0], parameters,
                        jac=lambda value: self.evaluate(value)[1], method="SLSQP",
                        bounds=[(-1.49, 1.49)] * 120,
                        constraints={"type": "ineq", "fun": lambda value: self.evaluate(value)[2],
                                     "jac": lambda value: self.evaluate(value)[3]}, callback=self.callback,
                        options={"maxiter": iterations, "ftol": 1e-12, "disp": True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["low", "high"], default="high")
    parser.add_argument("--target", type=float, default=0.0202)
    parser.add_argument("--iterations", type=int, default=350)
    parser.add_argument("--check-gradient", action="store_true")
    arguments = parser.parse_args()
    started = time.monotonic()
    data = json.loads(arguments.source.read_text())
    search = DADSearch(arguments.mode, arguments.output, arguments.target)
    parameters = np.array(data["pair_matrix"])[search.rows, search.cols]
    search.initial = np.array(data["amplitudes"])
    if arguments.check_gradient:
        direction = np.random.default_rng(129003).normal(size=120)
        direction /= np.linalg.norm(direction)
        values = search.evaluate(parameters)
        plus = search.evaluate(parameters + 1e-5 * direction)
        minus = search.evaluate(parameters - 1e-5 * direction)
        print(json.dumps({"analytic": float(values[1] @ direction),
                          "finite_difference": (plus[0] - minus[0]) / 2e-5,
                          "max_constraint_derivative_error": float(max(abs(values[3] @ direction
                                                                          - (plus[2] - minus[2]) / 2e-5)))}, indent=2))
        return
    message = ""
    try:
        answer = search.run_private(parameters, arguments.iterations)
        search.callback(answer.x)
        message = str(answer.message)
    except Exception as error:
        message = type(error).__name__ + ": " + str(error)
    summary = {"source": str(arguments.source), "mode": arguments.mode, "target": arguments.target,
               "verified_passing": search.passing, "closest_feasible_dad": search.best_dad if np.isfinite(search.best_dad) else None,
               "evaluations": search.evaluations, "iterations": search.iteration,
               "message": message, "runtime_seconds": time.monotonic() - started}
    (arguments.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
