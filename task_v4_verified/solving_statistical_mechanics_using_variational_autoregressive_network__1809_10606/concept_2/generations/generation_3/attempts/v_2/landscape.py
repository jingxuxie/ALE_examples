import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

from verify import STATES, PRODUCTS, evaluate, frustrated


def fwht(values):
    result = np.array(values, dtype=float, copy=True)
    width = 1
    while width < result.size:
        blocks = result.reshape(-1, 2 * width)
        first, second = blocks[:, :width].copy(), blocks[:, width:].copy()
        blocks[:, :width] = first + second
        blocks[:, width:] = first - second
        width *= 2
    return result


HAMMING = np.count_nonzero(STATES > 0, axis=1)
KERNELS = {radius: fwht((np.minimum(HAMMING, 16 - HAMMING) <= radius).astype(float))
           for radius in (2, 3, 4)}


def best_sector(witness, minimum=.35):
    result, target, proposal, energy, gradients = evaluate(witness, True)
    target_transform, proposal_transform = fwht(target), fwht(proposal)
    best = None
    for radius, kernel in KERNELS.items():
        target_masses = fwht(target_transform * kernel) / 65536
        proposal_masses = fwht(proposal_transform * kernel) / 65536
        scores = np.minimum(1., np.minimum(target_masses / minimum,
                                          .001 / np.maximum(proposal_masses, 1e-100)))
        maximum_score = scores.max()
        candidates = scores >= maximum_score - 1e-14
        center = np.argmin(np.where(candidates, proposal_masses, np.inf))
        key = (scores[center], -proposal_masses[center])
        if best is None or key > best[0]:
            best = (key, radius, center, target_masses[center], proposal_masses[center])
    witness = json.loads(json.dumps(witness))
    witness['radius'] = int(best[1])
    witness['pattern'] = STATES[best[2]].astype(int).tolist()
    return witness, best


def components(bonds):
    energy = -PRODUCTS @ bonds
    ground = np.flatnonzero(energy == energy.min())
    unseen = set(ground)
    groups = []
    while unseen:
        seed = unseen.pop()
        group, pending = [seed], [seed]
        while pending:
            state = pending.pop()
            for site in range(16):
                neighbor = state ^ (1 << site)
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    group.append(neighbor)
                    pending.append(neighbor)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    return energy, groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--components', action='store_true')
    arguments = parser.parse_args()
    witness = json.loads(arguments.input.read_text())
    if arguments.components:
        energy, groups = components(witness['bonds'])
        print('frustration', frustrated(witness['bonds']), 'ground', energy.min(), 'groups', [len(group) for group in groups])
    witness, best = best_sector(witness)
    print('best sector', best)
    print(json.dumps(evaluate(witness), indent=2))
    if arguments.output:
        arguments.output.write_text(json.dumps(witness, indent=2) + '\n')


if __name__ == '__main__':
    main()
