import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.linalg import block_diag, null_space
from scipy.optimize import LinearConstraint, minimize

PARTICIPANT = Path(__file__).resolve().parents[2] / "participant"
sys.path.insert(0, str(PARTICIPANT / "workspace"))
from physics import EliashbergSolver, constraint_report, load_instance


class Search:
    def __init__(self, count):
        self.instance = load_instance()
        self.reference = self.instance["reference"]
        self.count = count
        self.edge_row, self.edge_col = np.triu_indices(8, 1)
        incidence = np.zeros((8, 28))
        incidence[self.edge_row, np.arange(28)] = self.instance["weights"][self.edge_col]
        incidence[self.edge_col, np.arange(28)] = self.instance["weights"][self.edge_row]
        basis = null_space(incidence)
        zero = np.zeros_like(basis)
        self.basis = np.block([[basis, zero], [zero, basis], [-basis, -basis]])
        self.reference_edges = self.reference[:, self.edge_row, self.edge_col].ravel()
        self.solvers = [
            EliashbergSolver(
                self.instance["weights"], self.instance["row_sums"],
                self.instance["energies_mev"] * family["energy_factors"], self.instance["config"],
            )
            for family in self.instance["config"]["families"]
        ]
        self.last = None
        self.evaluations = 0
        self.start = time.time()
        self.best_score = 0.0

    def decode(self, coordinates):
        modes = self.reference.copy()
        edges = (self.reference_edges + self.basis @ coordinates).reshape(3, 28)
        modes[:, self.edge_row, self.edge_col] = edges
        modes[:, self.edge_col, self.edge_row] = edges
        return modes

    def temperatures(self, coordinates):
        if self.last is not None and np.array_equal(self.last[0], coordinates[:80]):
            return self.last[1:]
        logs = np.zeros((2, 4))
        derivatives = np.zeros((2, 4, 40))
        kernels = np.stack([self.decode(coordinates[:40]), self.decode(coordinates[40:80])])
        for kernel_index, modes in enumerate(kernels):
            for family_index, solver in enumerate(self.solvers):
                temperature = solver.critical_temperature(modes, self.count)["tc_kelvin"]
                details = solver.eigenpair(modes, temperature, self.count, gradient=True)
                step = 0.0001 * temperature
                slope = (
                    solver.eigenpair(modes, temperature + step, self.count)["eigenvalue"]
                    - solver.eigenpair(modes, temperature - step, self.count)["eigenvalue"]
                ) / (2 * step)
                logs[kernel_index, family_index] = np.log(temperature)
                edge_gradient = 2 * details["gradient"][:, self.edge_row, self.edge_col].ravel()
                derivatives[kernel_index, family_index] = -(edge_gradient @ self.basis) / (temperature * slope)
        self.evaluations += 1
        self.last = (coordinates[:80].copy(), logs, derivatives)
        score = np.exp(np.min(logs[0] - logs[1]))
        if score > self.best_score and constraint_report(kernels, self.instance)[0]["admissible"]:
            self.best_score = score
            np.savez_compressed(Path(__file__).with_name("witness.npz"), kernels=kernels)
            np.save(Path(__file__).with_name("best_coordinates.npy"), coordinates)
            print(f"best {score:.10f} evaluations {self.evaluations} elapsed {time.time()-self.start:.1f} ratios {np.exp(logs[0]-logs[1])}", flush=True)
        return logs, derivatives

    def constraint(self, coordinates):
        logs, derivatives = self.temperatures(coordinates)
        return logs[0] - logs[1] - coordinates[80]

    def jacobian(self, coordinates):
        logs, derivatives = self.temperatures(coordinates)
        return np.column_stack([derivatives[0], -derivatives[1], -np.ones(4)])

    def run(self, initial, maxiter):
        bounds_matrix = np.column_stack([block_diag(self.basis, self.basis), np.zeros(168)])
        lower = np.tile(0.005 - self.reference_edges, 2)
        upper = np.tile(5.0 - self.reference_edges, 2)
        objective_gradient = np.zeros(81)
        objective_gradient[-1] = -1
        result = minimize(
            lambda coordinates: -coordinates[-1], initial, jac=lambda coordinates: objective_gradient,
            method="SLSQP", constraints=[
                LinearConstraint(bounds_matrix, lower, upper),
                {"type": "ineq", "fun": self.constraint, "jac": self.jacobian},
            ], options={"ftol": 1e-11, "maxiter": maxiter, "disp": True},
        )
        print(result.message, result.fun, result.nit, flush=True)
        print(constraint_report(np.stack([self.decode(result.x[:40]), self.decode(result.x[40:80])]), self.instance)[0], flush=True)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=48)
    parser.add_argument("--initial", type=Path)
    parser.add_argument("--maxiter", type=int, default=400)
    arguments = parser.parse_args()
    initial = np.zeros(81) if arguments.initial is None else np.load(arguments.initial)
    search = Search(arguments.count)
    result = search.run(initial, arguments.maxiter)
    Path(__file__).with_name("search_result.json").write_text(json.dumps({
        "success": bool(result.success), "message": result.message,
        "iterations": int(result.nit), "count": arguments.count,
        "best_score": search.best_score,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
