import csv
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


def read_rows(path):
    with open(path, newline="") as stream:
        return list(csv.DictReader(stream))


def family(row):
    return row["circuit_style"], row["decoder"], row["preserved_observable"]


def features(rows):
    distance = np.array([float(row["code_distance"]) / 10 for row in rows])
    noise = np.log([float(row["noise"]) / 0.001 for row in rows])
    return np.column_stack([np.ones(len(rows)), distance, noise, distance * noise])


def fit(rows):
    matrix = features(rows)
    shots = np.array([int(row["num_shots"]) for row in rows], dtype=float)
    errors = shots - np.array([int(row["num_correct"]) for row in rows], dtype=float)
    empirical = np.clip((errors + 0.5) / (shots + 1), 1e-12, 0.499)
    target = np.log(2 * empirical) - np.log1p(-2 * empirical)
    weights = np.sqrt(np.minimum(errors + 0.5, 1000))
    initial = np.linalg.lstsq(matrix * weights[:, None], target * weights, rcond=None)[0]
    scale = max(float(errors.sum()), 1)

    def objective(coefficients):
        probability = np.clip(0.5 * expit(matrix @ coefficients), 1e-15, 0.5)
        loss = -np.sum(errors * np.log(probability) + (shots - errors) * np.log1p(-probability)) / scale
        derivative = (shots * probability - errors) * (1 - 2 * probability) / (1 - probability)
        gradient = matrix.T @ derivative / scale
        return loss + 1e-6 * np.sum(coefficients**2), gradient + 2e-6 * coefficients

    result = minimize(objective, initial, jac=True, method="L-BFGS-B",
                      bounds=[(-100, 100)] * matrix.shape[1],
                      options={"maxiter": 600, "ftol": 1e-12, "gtol": 1e-8})
    if not np.isfinite(result.x).all():
        raise ValueError("nonfinite fitted parameters")
    return result.x


def main():
    training_path, query_path, output_path = sys.argv[1:]
    training = read_rows(training_path)
    queries = read_rows(query_path)
    coefficients = {key: fit([row for row in training if family(row) == key])
                    for key in sorted({family(row) for row in training})}
    with open(output_path, "w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["query_id", "p_failure"])
        for row in queries:
            probability = float(np.clip(0.5 * expit(features([row]) @ coefficients[family(row)])[0], 1e-15, 0.5))
            writer.writerow([row["query_id"], format(probability, ".17g")])


if __name__ == "__main__":
    main()
