import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import expm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import LOWER, UPPER, OCCUPATIONS, STATES, hamiltonian, probabilities, validate_experiment


def independent_matrix(parameters):
    matrix = np.zeros((64, 64))
    fields = np.append(parameters[6:11], -sum(parameters[6:11]))
    for state in range(64):
        for site in range(6):
            spin = ((state >> site) & 1) - 0.5
            matrix[state, state] += fields[site] * spin
            for offset in (1, 2):
                neighbor = (site + offset) % 6
                other_spin = ((state >> neighbor) & 1) - 0.5
                coupling = parameters[site] if offset == 1 else parameters[12 + site % 2]
                matrix[state, state] += coupling * parameters[11] * spin * other_spin
                if spin != other_spin:
                    matrix[state ^ (1 << site) ^ (1 << neighbor), state] += 0.5 * coupling
    return matrix


def main():
    random = np.random.default_rng(59192)
    errors = []
    for iteration in range(30):
        parameters = LOWER + random.random(len(LOWER)) * (UPPER - LOWER)
        full = independent_matrix(parameters)
        assert np.max(np.abs(full[np.ix_(STATES, STATES)] - hamiltonian(parameters))) < 2e-14
        experiment = {"type": "query", "preparation": int(random.choice(STATES)), "time": float(random.uniform(0, 6)), "phases": random.uniform(-np.pi, np.pi, 6).tolist()}
        initial = np.zeros(64, dtype=complex)
        initial[experiment["preparation"]] = 1
        propagator = expm(-0.5j * experiment["time"] * full)
        all_bits = (np.arange(64)[:, None] >> np.arange(6)) & 1
        state = propagator @ (np.exp(-1j * (all_bits @ experiment["phases"])) * (propagator @ initial))
        independent = np.zeros(64)
        for actual in range(64):
            for recorded in range(64):
                weight = abs(state[actual]) ** 2
                for site in range(6):
                    error = parameters[14 + site]
                    weight *= error if ((actual ^ recorded) >> site) & 1 else 1 - error
                independent[recorded] += weight
        errors.append(float(np.max(np.abs(independent - probabilities(parameters, experiment)))))
        assert errors[-1] < 2e-13
        assert abs(independent.sum() - 1) < 1e-13
    rejected = 0
    for experiment in ({"type": "query", "preparation": 0, "time": 0, "phases": [0] * 6}, {"type": "query", "preparation": 7, "time": float("nan"), "phases": [0] * 6}, {"type": "query", "preparation": 7, "time": 2, "phases": [4] * 6}):
        try:
            validate_experiment(experiment)
        except ValueError:
            rejected += 1
    assert rejected == 3
    report = {"valid": True, "independent_full_space_expm_cases": len(errors), "max_probability_disagreement": max(errors), "invalid_query_rejections": rejected, "note": "Full 64-state Hamiltonian and explicit detector convolution are independent of the 20-state device implementation."}
    (ROOT / "adversary/evaluator_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
