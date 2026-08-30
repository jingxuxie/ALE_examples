import argparse
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import least_squares, minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from model import EVEN_MODES, baseline, features, manufacturing_tail, pack, sample, unpack


def flatten_seed(mesh, mass):
    axis = np.linspace(-np.pi, np.pi, mesh, endpoint=False)
    horizontal, vertical = np.meshgrid(axis, axis, indexing="ij")
    offset, basis = features(horizontal.ravel(), vertical.ravel())
    raw = offset.copy()
    raw[:, 3] = mass + np.cos(horizontal.ravel()) + np.cos(vertical.ravel())
    raw[:, 1:] /= np.linalg.norm(raw[:, 1:], axis=1)[:, None]
    scale = np.mean(raw[:, 1] * np.sin(horizontal.ravel())) * 2.0
    raw /= scale
    parameters = np.linalg.lstsq(basis.reshape(-1, 30), (raw - offset).reshape(-1), rcond=None)[0]
    parameters[21:] = 0.0
    return parameters


class Search:
    def __init__(self, mesh, uncertainty_points):
        axis = np.linspace(-np.pi, np.pi, mesh, endpoint=False)
        horizontal, vertical = np.meshgrid(axis, axis, indexing="ij")
        self.horizontal = horizontal.ravel()
        self.vertical = vertical.ravel()
        self.offset, self.basis = features(self.horizontal, self.vertical)
        self.errors = [(mass, strain) for mass in np.linspace(-0.05, 0.05, uncertainty_points) for strain in np.linspace(-0.06, 0.06, uncertainty_points)]
        self.weights = np.array([0.0] + [np.sqrt(2.0)] * 11 + [1.0 if order == cross else 2.0 for order, cross in EVEN_MODES] * 2)
        _, special = features(np.array([0.0, np.pi, np.pi]), np.array([0.0, 0.0, np.pi]))
        self.topology_rows = special[:, 3] * np.array([1.0, -1.0, -1.0])[:, None]

    def spectral(self, parameters):
        nominal = self.offset + np.einsum("pij,j->pi", self.basis, parameters)
        spectra = []
        derivatives = []
        gaps = []
        for mass, strain in self.errors:
            values = nominal.copy()
            values[:, 3] += mass
            values[:, 1] += strain * np.sin(self.horizontal)
            values[:, 2] -= strain * np.sin(self.vertical)
            radius = np.linalg.norm(values[:, 1:], axis=1)
            lower = values[:, 0] - radius
            gradient = self.basis[:, 0] - np.einsum("pi,pij->pj", values[:, 1:] / np.maximum(radius[:, None], 1e-12), self.basis[:, 1:])
            spectra.append(lower)
            derivatives.append(gradient)
            gaps.append(float(np.min(2.0 * radius)))
        return np.array(spectra), np.array(derivatives), min(gaps)

    def polish(self, initial, support, iterations=150):
        support = np.array(sorted(support), dtype=int)
        base = np.zeros(30)
        base[support] = initial[support]
        temperature_schedule = [0.035, 0.012, 0.004, 0.0015]
        result = None
        for temperature in temperature_schedule:
            def objective(selected):
                parameters = base.copy()
                parameters[support] = selected
                spectra, gradient, gap = self.spectral(parameters)
                maximum = np.max(spectra, axis=1, keepdims=True)
                minimum = np.min(spectra, axis=1, keepdims=True)
                high_weight = np.exp((spectra - maximum) / temperature)
                low_weight = np.exp((minimum - spectra) / temperature)
                high_weight /= high_weight.sum(axis=1, keepdims=True)
                low_weight /= low_weight.sum(axis=1, keepdims=True)
                widths = (maximum - minimum).ravel() + temperature * (np.log(np.exp((spectra - maximum) / temperature).sum(axis=1)) + np.log(np.exp((minimum - spectra) / temperature).sum(axis=1)))
                scenario_weight = np.exp((widths - widths.max()) / temperature)
                scenario_weight /= scenario_weight.sum()
                score = float(widths.max() + temperature * np.log(np.exp((widths - widths.max()) / temperature).sum()))
                derivative = np.einsum("s,sp,spj->j", scenario_weight, high_weight - low_weight, gradient)
                score += 0.008 * np.dot(self.weights, np.sqrt(parameters * parameters + 1e-10))
                derivative += 0.008 * self.weights * parameters / np.sqrt(parameters * parameters + 1e-10)
                slack = np.maximum(1.1 - self.topology_rows @ parameters, 0.0)
                score += 100.0 * float(slack @ slack)
                derivative -= 200.0 * slack @ self.topology_rows
                return score, derivative[support]

            bounds = [(-1.9, -0.3) if index == 0 else (-0.75, 0.75) if index < 12 or index >= 21 else (-1.5, 1.5) for index in support]
            result = minimize(objective, base[support], jac=True, method="L-BFGS-B", bounds=bounds, options={"maxiter": iterations, "ftol": 1e-12, "gtol": 2e-7, "maxls": 30})
            base[support] = result.x
        return base, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh", type=int, default=29)
    parser.add_argument("--support", type=int, default=12)
    parser.add_argument("--starts", type=int, default=5)
    parser.add_argument("--seed", type=int, default=731)
    parser.add_argument("--initial", type=Path)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    search = Search(arguments.mesh, 3)
    generator = np.random.default_rng(arguments.seed)
    best_score = float("inf")
    started = time.monotonic()
    records = []
    for trial in range(arguments.starts):
        if arguments.initial:
            initial = pack(json.loads(arguments.initial.read_text()))
            initial[1:] += generator.normal(0, 0.02 if trial else 0.0, 29)
        else:
            initial = flatten_seed(65, float(generator.uniform(-1.4, -0.6)))
        parameters, result = search.polish(initial, list(range(30)), 80)
        support = [0] + (np.argsort(np.abs(parameters[1:]))[-arguments.support:] + 1).tolist()
        parameters, result = search.polish(parameters, support, 200)
        witness = unpack(parameters)
        metrics = sample(witness, mesh=121, uncertainty_points=5)
        record = {"trial": trial, "elapsed": time.monotonic() - started, "support": support, "metrics": metrics, "optimizer_message": str(result.message)}
        records.append(record)
        print(json.dumps(record), flush=True)
        (arguments.output / f"trial_{trial}.json").write_text(json.dumps(witness, indent=2) + "\n")
        if metrics["bandwidth_plus_tail"] < best_score and metrics["direct_gap_minus_tail"] > 1.2 and metrics["indirect_gap_minus_tail"] > 1.2:
            best_score = metrics["bandwidth_plus_tail"]
            (arguments.output / "best.json").write_text(json.dumps(witness, indent=2) + "\n")
        (arguments.output / "records.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
