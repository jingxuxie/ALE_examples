import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import block_diag, null_space
from scipy.optimize import LinearConstraint, linprog, minimize

PARTICIPANT = Path("/participant")
sys.path.insert(0, str(PARTICIPANT / "workspace"))
from physics import EliashbergSolver, constraint_report, load_instance


class Search:
    def __init__(self, count, output):
        self.instance = load_instance()
        self.reference = self.instance["reference"]
        self.config = self.instance["config"]
        self.edges = np.triu_indices(self.reference.shape[1], 1)
        incidence = np.zeros((self.reference.shape[1], len(self.edges[0])))
        for edge, (first, second) in enumerate(zip(*self.edges)):
            incidence[first, edge] = self.instance["weights"][second]
            incidence[second, edge] = self.instance["weights"][first]
        self.basis = np.kron(null_space(np.ones((1, 3))), null_space(incidence))
        self.dimension = self.basis.shape[1]
        self.reference_edges = self.reference[:, self.edges[0], self.edges[1]].ravel()
        self.lower = self.config["entry_lower"] + 1e-11 - self.reference_edges
        self.upper = self.config["entry_upper"] - 1e-11 - self.reference_edges
        self.count = count
        self.output = output
        self.solvers = [
            EliashbergSolver(
                self.instance["weights"], self.instance["row_sums"],
                self.instance["energies_mev"] * family["energy_factors"], self.config,
            ) for family in self.config["families"]
        ]
        self.cached_coordinates = None
        self.best = 1.0
        self.iteration = 0
        self.started = time.perf_counter()

    def modes(self, coordinates):
        values = (self.reference_edges + self.basis @ coordinates).reshape(3, -1)
        modes = self.reference.copy()
        modes[:, self.edges[0], self.edges[1]] = values
        modes[:, self.edges[1], self.edges[0]] = values
        return modes

    def coordinates(self, modes):
        return self.basis.T @ (modes[:, self.edges[0], self.edges[1]].ravel() - self.reference_edges)

    def evaluate(self, coordinates):
        pair_coordinates = coordinates[:2 * self.dimension]
        if self.cached_coordinates is not None and np.array_equal(pair_coordinates, self.cached_coordinates):
            return self.cached_values
        modes = [self.modes(part) for part in pair_coordinates.reshape(2, self.dimension)]
        temperatures = np.empty((2, len(self.solvers)))
        gradients = np.empty((2, len(self.solvers), self.dimension))
        for candidate, kernel in enumerate(modes):
            for family, solver in enumerate(self.solvers):
                temperature = solver.critical_temperature(kernel, self.count)["tc_kelvin"]
                details = solver.eigenpair(kernel, temperature, self.count, gradient=True)
                step = temperature * 1e-4
                derivative = (
                    solver.eigenpair(kernel, temperature + step, self.count)["eigenvalue"]
                    - solver.eigenpair(kernel, temperature - step, self.count)["eigenvalue"]
                ) / (2 * step)
                edge_gradient = 2 * details["gradient"][:, self.edges[0], self.edges[1]].ravel()
                gradients[candidate, family] = -(edge_gradient @ self.basis) / (temperature * derivative)
                temperatures[candidate, family] = temperature
        ratios = temperatures[0] / temperatures[1]
        score = float(ratios.min())
        constraints, _ = constraint_report(np.stack(modes), self.instance)
        if score > self.best and constraints["admissible"]:
            self.best = score
            with self.output.open("wb") as stream:
                np.savez_compressed(stream, kernels=np.stack(modes))
            self.output.with_suffix(".search.json").write_text(json.dumps({
                "count": self.count, "ratios": ratios.tolist(), "temperatures": temperatures.tolist(),
                "score": score, "constraints": constraints,
            }, indent=2) + "\n")
        self.cached_coordinates = pair_coordinates.copy()
        self.cached_values = np.log(ratios), gradients, temperatures
        return self.cached_values

    def constraint(self, coordinates):
        return self.evaluate(coordinates)[0] - coordinates[-1]

    def jacobian(self, coordinates):
        gradients = self.evaluate(coordinates)[1]
        return np.column_stack((gradients[0], -gradients[1], -np.ones(len(self.solvers))))

    def callback(self, coordinates):
        self.iteration += 1
        if self.iteration % 5 == 0:
            ratios = np.exp(self.evaluate(coordinates)[0])
            print("iteration", self.iteration, "ratios", ratios, "best", self.best,
                  "seconds", round(time.perf_counter() - self.started, 2), flush=True)

    def random_start(self, generator):
        coordinates = []
        for candidate in range(2):
            solution = linprog(
                generator.normal(size=self.dimension),
                A_ub=np.vstack((self.basis, -self.basis)),
                b_ub=np.concatenate((self.upper, -self.lower)),
                bounds=[(None, None)] * self.dimension,
                method="highs",
            )
            if not solution.success:
                raise RuntimeError(solution.message)
            coordinates.append(solution.x * 0.95)
        return np.concatenate((*coordinates, [0.0]))

    def optimize(self, initial, maxiter):
        linear_matrix = np.column_stack((block_diag(self.basis, self.basis), np.zeros(2 * self.reference_edges.size)))
        linear_constraint = LinearConstraint(linear_matrix, np.tile(self.lower, 2), np.tile(self.upper, 2))
        initial[-1] = self.evaluate(initial)[0].min()
        objective_gradient = np.zeros(len(initial))
        objective_gradient[-1] = -1
        result = minimize(
            lambda coordinates: -coordinates[-1], initial, jac=lambda coordinates: objective_gradient,
            constraints=[linear_constraint, {"type": "ineq", "fun": self.constraint, "jac": self.jacobian}],
            method="SLSQP", callback=self.callback,
            options={"maxiter": maxiter, "ftol": 1e-11, "disp": True},
        )
        print("result", result.success, result.message, "ratios", np.exp(self.evaluate(result.x)[0]), flush=True)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--starts", type=int, default=1)
    parser.add_argument("--maxiter", type=int, default=300)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--initial", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "witness.npz")
    arguments = parser.parse_args()
    search = Search(arguments.count, arguments.output)
    generator = np.random.default_rng(arguments.seed)
    initial = np.zeros(2 * search.dimension + 1)
    if arguments.initial:
        with np.load(arguments.initial) as archive:
            initial[:-1] = np.concatenate([search.coordinates(kernel) for kernel in archive["kernels"]])
    for start in range(arguments.starts):
        print("start", start, "count", arguments.count, flush=True)
        if start:
            initial = search.random_start(generator)
        search.optimize(initial, arguments.maxiter)


if __name__ == "__main__":
    main()
