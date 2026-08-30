import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import null_space, qr
from scipy.optimize import Bounds, LinearConstraint, linprog, minimize

PARTICIPANT = Path("/participant")
sys.path.insert(0, str(PARTICIPANT / "workspace"))
from physics import EliashbergSolver, constraint_report, load_instance


class Search:
    def __init__(self, count, family):
        self.instance = load_instance()
        self.config = self.instance["config"]
        self.count = count
        self.patch_count = len(self.instance["weights"])
        self.rows, self.columns = np.triu_indices(self.patch_count, 1)
        self.edge_count = len(self.rows)
        self.reference = self.instance["reference"]
        self.initial = self.reference[:, self.rows, self.columns].ravel()
        self.diagonal = np.zeros_like(self.reference)
        for mode in range(3):
            np.fill_diagonal(self.diagonal[mode], self.instance["diagonal"][mode])
        equations = []
        targets = []
        for edge in range(self.edge_count):
            equation = np.zeros((3, self.edge_count))
            equation[:, edge] = 1
            equations.append(equation.ravel())
            targets.append(self.instance["static"][self.rows[edge], self.columns[edge]])
        for mode in range(3):
            for patch in range(self.patch_count):
                equation = np.zeros((3, self.edge_count))
                for edge, (row, column) in enumerate(zip(self.rows, self.columns)):
                    if row == patch:
                        equation[mode, edge] = self.instance["weights"][column]
                    elif column == patch:
                        equation[mode, edge] = self.instance["weights"][row]
                equations.append(self.patch_count * equation.ravel())
                targets.append(self.patch_count * (self.instance["row_sums"][mode, patch] - self.instance["weights"][patch] * self.instance["diagonal"][mode, patch]))
        self.full_matrix = np.array(equations)
        self.full_target = np.array(targets)
        rank = np.linalg.matrix_rank(self.full_matrix)
        _, _, pivot = qr(self.full_matrix.T, pivoting=True)
        self.matrix = self.full_matrix[pivot[:rank]]
        self.target = self.full_target[pivot[:rank]]
        self.null = null_space(self.matrix)
        self.lower = self.config["entry_lower"]
        self.upper = self.config["entry_upper"]
        factors = next(item["energy_factors"] for item in self.config["families"] if item["name"] == family)
        self.solver = EliashbergSolver(self.instance["weights"], self.instance["row_sums"], self.instance["energies_mev"] * factors, self.config)
        self.reference_tc = self.tc(self.initial)
        print("SETUP", count, family, "rank", rank, "freedom", self.null.shape[1], "reference_tc", self.reference_tc, flush=True)

    def unpack(self, variables):
        modes = self.diagonal.copy()
        modes[:, self.rows, self.columns] = variables.reshape(3, self.edge_count)
        modes[:, self.columns, self.rows] = variables.reshape(3, self.edge_count)
        return modes

    def tc(self, variables):
        return self.solver.critical_temperature(self.unpack(variables), self.count)["tc_kelvin"]

    def eigen_gradient(self, variables, temperature):
        result = self.solver.eigenpair(self.unpack(variables), temperature, self.count, gradient=True)
        gradient = 2 * result["gradient"][:, self.rows, self.columns].ravel()
        return result["eigenvalue"], self.null @ (self.null.T @ gradient)

    def corner(self, direction):
        scale = np.max(np.abs(direction))
        result = linprog(direction / max(scale, 1e-20), A_eq=self.matrix, b_eq=self.target,
                         bounds=(self.lower, self.upper), method="highs",
                         options={"dual_feasibility_tolerance": 1e-9, "primal_feasibility_tolerance": 1e-9})
        if not result.success:
            raise RuntimeError(result.message)
        return result.x

    def maximize(self, variables):
        temperature = self.tc(variables)
        for iteration in range(80):
            _, gradient = self.eigen_gradient(variables, temperature)
            candidate = self.corner(-gradient)
            gain = gradient @ (candidate - variables)
            if gain < 1e-12:
                break
            next_temperature = self.tc(candidate)
            if next_temperature < temperature - 1e-6:
                raise RuntimeError("ascent lost monotonicity")
            variables = candidate
            temperature = next_temperature
        return variables, temperature, iteration

    def minimize(self, variables):
        calls = 0

        def objective(candidate):
            nonlocal calls
            calls += 1
            temperature = self.tc(candidate)
            _, gradient = self.eigen_gradient(candidate, temperature)
            step = temperature * 1e-4
            plus = self.solver.eigenpair(self.unpack(candidate), temperature + step, self.count)["eigenvalue"]
            minus = self.solver.eigenpair(self.unpack(candidate), temperature - step, self.count)["eigenvalue"]
            slope = (plus - minus) / (2 * step)
            if calls % 25 == 0:
                print("MIN", calls, temperature, flush=True)
            return temperature / self.reference_tc, -gradient / (slope * self.reference_tc)

        result = minimize(objective, variables, jac=True, method="SLSQP",
                          bounds=Bounds(self.lower, self.upper),
                          constraints=[LinearConstraint(self.matrix, self.target, self.target)],
                          options={"ftol": 1e-12, "maxiter": 700, "disp": False})
        print("MIN_RESULT", result.success, result.message, "calls", calls, "tc", result.fun * self.reference_tc, flush=True)
        if np.max(np.abs(self.full_matrix @ result.x - self.full_target)) > 1e-8:
            raise RuntimeError("minimum infeasible")
        return result.x, self.tc(result.x)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=48)
    parser.add_argument("--starts", type=int, default=16)
    parser.add_argument("--family", default="compressed_spectrum")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("witness.npz"))
    parser.add_argument("--resume", type=Path)
    arguments = parser.parse_args()
    started = time.monotonic()
    search = Search(arguments.count, arguments.family)
    initial_low = search.initial.copy()
    initial_high = search.initial.copy()
    if arguments.resume:
        with np.load(arguments.resume) as archive:
            initial_low = archive["kernels"][0, :, search.rows, search.columns].T.ravel()
            initial_high = archive["kernels"][1, :, search.rows, search.columns].T.ravel()
    low, low_tc = search.minimize(initial_low)
    high, high_tc, iterations = search.maximize(initial_high)
    random = np.random.default_rng(1907)
    history = []
    for start in range(arguments.starts + 1):
        if start:
            direction = search.null @ random.normal(size=search.null.shape[1])
            candidate, temperature, iterations = search.maximize(search.corner(direction))
            if temperature > high_tc:
                high, high_tc = candidate, temperature
        kernels = np.stack([search.unpack(low), search.unpack(high)])
        report, _ = constraint_report(kernels, search.instance)
        if not report["admissible"]:
            raise RuntimeError(str(report))
        with arguments.output.open("wb") as stream:
            np.savez_compressed(stream, kernels=kernels)
        entry = {"start": start, "low_tc": low_tc, "high_tc": high_tc, "ratio": high_tc / low_tc,
                 "iterations": iterations, "elapsed_seconds": time.monotonic() - started}
        history.append(entry)
        print("WITNESS", json.dumps(entry), flush=True)
        arguments.output.with_suffix(".search.json").write_text(json.dumps(history, indent=2) + "\n")


if __name__ == "__main__":
    main()
