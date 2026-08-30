import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time

import numpy as np
from scipy.optimize import minimize
from physics import LOWER, UPPER, STATES
from derivatives import predict_with_jac


def emit(message):
    print(json.dumps(message), flush=True)


def main():
    config = json.loads(input())["config"]
    started = time.monotonic()
    random = np.random.default_rng(492724)
    experiments = []
    observations = []
    normalized = np.full(20, 0.5)
    best_loss = np.inf

    def query(experiment):
        emit(experiment)
        counts = json.loads(input())["counts"]
        experiments.append(experiment)
        observations.append(counts)

    def fit(initial, iterations=180):
        counts = np.asarray(observations)

        def objective(values):
            prediction, jacobian = predict_with_jac(values, experiments)
            prediction = np.maximum(prediction, 1e-14)
            loss = -np.sum(counts * np.log(prediction)) / counts.sum()
            gradient = -np.einsum("qa,qap->p", counts / prediction, jacobian) / counts.sum()
            return loss, gradient

        return minimize(objective, initial, jac=True, bounds=[(0.000001, 0.999999)] * 20, method="L-BFGS-B", options={"maxiter": iterations, "ftol": 2e-11, "gtol": 2e-7, "maxls": 25})

    for index in range(10):
        experiment = {"type": "query", "preparation": int(STATES[(index * 7) % len(STATES)]), "time": [0, 0.35, 0.55, 0.8, 1.0, 1.2, 1.45, 1.7, 1.9, 2.2][index], "phases": random.uniform(-1.6, 1.6, 6).tolist()}
        query(experiment)
    candidates = [normalized.copy()]
    for direction in (-1, 1):
        guess = normalized.copy()
        guess[6:11] = 0.5 + direction * 0.28
        candidates.append(guess)
    for initial in candidates:
        fitted = fit(initial)
        if fitted.fun < best_loss:
            best_loss = fitted.fun
            normalized = fitted.x
    for index in range(10, config["query_budget"]):
        candidate_experiments = [{"type": "query", "preparation": int(random.choice(STATES)), "time": float(random.uniform(1.0, 5.9)), "phases": random.uniform(-np.pi, np.pi, 6).tolist()} for candidate_index in range(48)]
        prediction, jacobian = predict_with_jac(normalized, experiments)
        information = config["shots"] * np.einsum("qap,qak,qa->pk", jacobian, jacobian, 1.0 / np.maximum(prediction, 1e-12)) + 1e-5 * np.eye(20)
        prediction, jacobian = predict_with_jac(normalized, candidate_experiments)
        candidate_information = config["shots"] * np.einsum("qap,qak,qa->qpk", jacobian, jacobian, 1.0 / np.maximum(prediction, 1e-12))
        risks = [np.trace(np.linalg.inv(information + matrix)) for matrix in candidate_information]
        query(candidate_experiments[int(np.argmin(risks))])
        normalized = fit(normalized, iterations=90).x
    fitted = fit(normalized, iterations=230)
    normalized = fitted.x
    best_loss = fitted.fun
    if time.monotonic() - started < 65:
        guess = np.clip(normalized + random.normal(0, 0.13, 20), 0.001, 0.999)
        alternative = fit(guess, iterations=180)
        if alternative.fun < best_loss:
            normalized = alternative.x
    emit({"type": "answer", "parameters": (LOWER + (UPPER - LOWER) * normalized).tolist()})


if __name__ == "__main__":
    main()
