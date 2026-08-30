import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

from exact import STATES, FEATURES, EDGES, LIMIT, frustration, evaluate
from sectors import best_sector, ball_masses


def generate(count, seed, prefix):
    random = np.random.default_rng(seed)
    independent = [list(sites) for sites in itertools.combinations(range(16), 4)
                   if not any(first in sites and second in sites for first, second in EDGES)]
    incident = [[index for index, edge in enumerate(EDGES) if site in edge] for site in range(16)]
    records = []
    seen = set()
    start = time.time()
    for batch in range((count + 63) // 64):
        samples = []
        for index in range(64):
            free = independent[random.integers(len(independent))]
            bonds = np.ones(32, dtype=int)
            for site in free:
                bonds[random.choice(incident[site], 2, replace=False)] = -1
            samples.append((bonds, free))
        energies = -FEATURES @ np.column_stack([sample[0] for sample in samples])
        for index, (bonds, free) in enumerate(samples):
            key = (tuple(bonds), tuple(free))
            if key in seen:
                continue
            seen.add(key)
            if not 4 <= frustration(bonds) <= 12:
                continue
            energy = energies[:, index]
            if energy.min() != -16 or np.sum(energy == -16) < 64:
                continue
            frozen = [site for site in range(16) if site not in free]
            target = np.exp(-energy - logsumexp(-energy))
            masses = ball_masses(target)
            distance = (STATES[:, frozen] < 0).sum(axis=1)
            separation = np.minimum(distance, 12 - distance)
            eligible = separation[None, :] >= np.arange(2, 5)[:, None] + 2
            masses[~eligible] = 0
            choice = np.unravel_index(masses.argmax(), masses.shape)
            if masses[choice] < .35:
                continue
            local_fields = np.array([bonds[incident[site]].sum() for site in range(16)])
            if np.any(local_fields[frozen] == 0):
                root = random.choice([site for site in frozen if local_fields[site] == 0])
            else:
                root = random.choice([site for site in frozen if local_fields[site] == local_fields[frozen].max()])
            order = [int(root)] + random.permutation([site for site in frozen if site != root]).tolist() + list(free)
            weights = np.zeros((16, 16))
            weights[1:12, 0] = LIMIT - 2e-12
            for position, site in enumerate(order[12:], 12):
                for edge_index in incident[site]:
                    first, second = EDGES[edge_index]
                    parent = second if first == site else first
                    weights[position, order.index(parent)] = bonds[edge_index] * (LIMIT - 2e-12) / 4
                if random.random() < .65:
                    positive = np.flatnonzero(weights[position] > 0)
                    negative = np.flatnonzero(weights[position] < 0)
                    weights[position, random.choice(positive)] *= -1
                    weights[position, random.choice(negative)] *= -1
            witness = {'schema_version': 1, 'bonds': bonds.tolist(), 'beta': 1.0, 'order': order,
                       'weights': weights.tolist(), 'pattern': STATES[choice[1]].astype(int).tolist(),
                       'radius': int(choice[0] + 2)}
            report = evaluate(witness)
            records.append((report['core_score'], witness, report))
        if batch % 10 == 0:
            print(batch * 64, len(records), round(time.time() - start, 1), flush=True)
    records.sort(key=lambda record: -record[0])
    Path(prefix + '_records.json').write_text(json.dumps(records))
    print('final',len(records), 'seconds',time.time() - start, flush=True)
    for score, witness, report in records[:10]:
        print(report, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=8192)
    parser.add_argument('--seed', type=int, default=134)
    parser.add_argument('--prefix', default='cubes')
    arguments = parser.parse_args()
    generate(arguments.count, arguments.seed, arguments.prefix)
