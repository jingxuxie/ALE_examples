"""Privileged numerical witness; no fixture access and no material identifiers."""

import time

import numpy as np
from scipy.sparse.linalg import LinearOperator, gmres


def solve(instance, model, cpu_budget=300.0, initial_factor=1.0):
    started = time.process_time()
    delta = initial_factor * instance["initial_delta"].copy()
    size = delta.size
    iterations = 0
    for iteration in range(60):
        delta = 0.15 * delta + 0.85 * model.map(delta)[1]
    history = []
    for iteration in range(48):
        renormalization, mapped = model.map(delta)
        scales = np.maximum(np.max(np.abs(delta), axis=1), np.pi * model.temperature * 1e-12)[:, None]
        residual = (delta - mapped) / scales
        error = float(np.max(np.abs(residual)))
        history.append(error)
        if error < 2e-13 or time.process_time() - started > cpu_budget:
            break
        derivative = model.linearize(delta)

        def action(direction):
            return (derivative(direction.reshape(model.shape) * scales) / scales).ravel()

        operator = LinearOperator((size, size), matvec=action, dtype=np.float64)
        change, info = gmres(operator, -residual.ravel(), tol=2e-8, atol=0, restart=50, maxiter=8)
        change = change.reshape(model.shape) * scales
        damping = 1.0
        accepted = False
        for trial_index in range(24):
            trial = delta + damping * change
            if np.all(trial[:, 0] > 0):
                trial_error = float(np.max(np.abs(trial - model.map(trial)[1]) / scales))
                if trial_error < error * (1 - 1e-4 * damping):
                    delta = trial
                    accepted = True
                    break
            damping *= 0.5
        if not accepted:
            for fallback in range(40):
                delta = 0.25 * delta + 0.75 * model.map(delta)[1]
        iterations += 1
    return delta, model.map(delta)[0], {"newton_iterations": iterations, "scaled_residual_history": history,
                                      "cpu_seconds": time.process_time() - started}
