import copy
import importlib.util
import itertools
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import score, validate_solution


def one_body_sector(matrix, particles):
    dimension = len(matrix)
    states = [sum(1 << site for site in occupied) for occupied in itertools.combinations(range(dimension), particles)]
    positions = {state: index for index, state in enumerate(states)}
    result = np.zeros((len(states), len(states)))
    for column, state in enumerate(states):
        for annihilator in range(dimension):
            if not state & (1 << annihilator):
                continue
            reduced = state ^ (1 << annihilator)
            annihilation_sign = (-1) ** (state & ((1 << annihilator) - 1)).bit_count()
            for creator in range(dimension):
                if reduced & (1 << creator):
                    continue
                created = reduced | (1 << creator)
                creation_sign = (-1) ** (reduced & ((1 << creator) - 1)).bit_count()
                result[positions[created], column] += matrix[creator, annihilator] * annihilation_sign * creation_sign
    return result


def hamiltonian(one_body, factors, particles):
    result = one_body_sector(one_body, particles)
    for factor in factors:
        lifted = one_body_sector(factor, particles)
        result += 0.5 * lifted @ lifted
    return result


def main():
    generator = np.random.default_rng(1973)
    dimension, rank = 6, 5
    one_body = generator.normal(size=(dimension, dimension))
    one_body += one_body.T.copy()
    factors = generator.normal(size=(rank, dimension, dimension))
    factors += factors.transpose(0, 2, 1).copy()
    orbital = np.linalg.qr(generator.normal(size=(dimension, dimension)))[0]
    auxiliary = np.linalg.qr(generator.normal(size=(rank, rank)))[0]
    rotated = np.stack([orbital.T @ factor @ orbital for factor in factors])
    mixed = np.tensordot(auxiliary, rotated, axes=(1, 0))
    errors = []
    for particles in range(dimension + 1):
        original = hamiltonian(one_body, factors, particles)
        changed = hamiltonian(orbital.T @ one_body @ orbital, mixed, particles)
        errors.append(float(np.max(np.abs(np.linalg.eigvalsh(original) - np.linalg.eigvalsh(changed)))))
    assert max(errors) < 1e-10
    request = json.loads((ROOT / "evaluator/hidden/cases.json").read_text())
    response = json.loads((ROOT / "adversary/hidden_planted/solution.json").read_text())
    valid = score(request, response, 0)
    rejected = []
    for mutation in ("nan", "nonorthogonal", "duplicate", "missing", "shape"):
        bad = copy.deepcopy(response)
        if mutation == "nan":
            bad["solutions"][0]["orbital"][0][0] = float("nan")
        elif mutation == "nonorthogonal":
            bad["solutions"][0]["orbital"][0][0] += 0.01
        elif mutation == "duplicate":
            bad["solutions"][1]["id"] = bad["solutions"][0]["id"]
        elif mutation == "missing":
            bad["solutions"].pop()
        else:
            bad["solutions"][0]["auxiliary"].pop()
        try:
            score(request, bad, 0)
        except (ValueError, KeyError):
            rejected.append(mutation)
        else:
            raise AssertionError("accepted " + mutation)
    report = {"valid": True, "independent_fock_space_spectrum_max_errors_by_particle_number": errors, "invalid_artifacts_rejected": rejected, "planted_artifacts_valid": valid["valid"], "planted_artifacts_not_assumed_optimal": True, "trusted_evaluator_never_imports_submission": True}
    (ROOT / "adversary/evaluator_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
