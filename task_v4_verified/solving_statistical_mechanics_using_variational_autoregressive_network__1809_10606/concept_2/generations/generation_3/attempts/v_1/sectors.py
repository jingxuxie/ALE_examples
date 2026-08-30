import json
import sys
from pathlib import Path

import numpy as np

from exact import STATES, evaluate


def ball_masses(probability):
    indices = np.arange(65536)
    previous = np.zeros_like(probability)
    current = probability.copy()
    total = probability.copy()
    masses = []
    for radius in range(1, 5):
        adjacency = sum(current[indices ^ (1 << spin)] for spin in range(16))
        following = (adjacency - (18 - radius) * previous) / radius
        total += following
        previous, current = current, following
        if radius >= 2:
            masses.append(np.maximum(0, 2 * total))
    return np.array(masses)


def best_sector(witness, strict=True):
    report, (energy, proposal, target, logq, gradient) = evaluate(witness, True)
    target_mass = ball_masses(target)
    proposal_mass = ball_masses(proposal)
    scores = np.minimum(target_mass / .35, .001 / np.maximum(proposal_mass, 1e-100))
    if strict:
        eligible = target_mass >= .35000001
        if eligible.any():
            scores = np.where(eligible, -proposal_mass, -np.inf)
    index = np.unravel_index(scores.argmax(), scores.shape)
    result = dict(witness, pattern=STATES[index[1]].astype(int).tolist(), radius=int(index[0] + 2))
    return result, float(target_mass[index]), float(proposal_mass[index])


if __name__ == '__main__':
    source = Path(sys.argv[1])
    witness = json.loads(source.read_text())
    result, target_mass, proposal_mass = best_sector(witness)
    print(target_mass, proposal_mass)
    print(json.dumps(evaluate(result), indent=2))
    Path(sys.argv[2]).write_text(json.dumps(result))
