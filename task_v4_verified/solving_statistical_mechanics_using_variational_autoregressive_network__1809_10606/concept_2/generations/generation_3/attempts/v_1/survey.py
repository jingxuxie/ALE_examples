import argparse
import json
import time
from pathlib import Path

import numpy as np

from exact import FEATURES, STATES, frustration


POPCOUNT = np.array([number.bit_count() for number in range(65536)], dtype=np.int8)


def components(ground):
    remaining = set(ground.tolist())
    clusters = []
    while remaining:
        cluster = [remaining.pop()]
        pending = cluster.copy()
        while pending:
            state = pending.pop()
            for mask in [1 << spin for spin in range(15)] + [32767]:
                neighbor = state ^ mask
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    cluster.append(neighbor)
                    pending.append(neighbor)
        clusters.append(np.array(cluster))
    return clusters


def survey(count, seed, output, minimum=6, maximum=1000):
    random = np.random.default_rng(seed)
    candidates = []
    start = time.time()
    for batch in range((count + 127) // 128):
        bonds_batch = random.choice([-1, 1], (32, 128))
        energies = -FEATURES[32768:] @ bonds_batch
        for index in range(128):
            bonds = bonds_batch[:, index]
            frustrated = int(frustration(bonds))
            if not 4 <= frustrated <= 12:
                continue
            energy = energies[:, index]
            ground = np.flatnonzero(energy == energy.min())
            if len(ground) < 2 * minimum:
                continue
            clusters = components(ground)
            if len(clusters) < 2:
                continue
            distances = POPCOUNT[np.bitwise_xor(ground[:, None], ground[None, :])]
            distances = np.minimum(distances, 16 - distances)
            for cluster in clusters:
                if not minimum <= len(cluster) <= maximum:
                    continue
                selected = np.isin(ground, cluster)
                separation = distances[selected].min(axis=0)
                for radius in [2, 3, 4]:
                    coverage = (distances <= radius).mean(axis=0)
                    eligible = np.flatnonzero((coverage >= .36) & (separation >= radius + 2))
                    if len(eligible) == 0:
                        continue
                    choice = eligible[np.argmax(coverage[eligible] + .1 * separation[eligible])]
                    quality = float(np.log(len(cluster)) + .6 * (separation[choice] - radius) + coverage[choice])
                    candidates.append({'bonds': bonds.tolist(), 'cluster': (cluster + 32768).tolist(),
                                       'pattern': STATES[ground[choice] + 32768].astype(int).tolist(),
                                       'radius': radius, 'ground_count': len(ground),
                                       'ground_energy': float(energy.min()), 'frustrated': frustrated,
                                       'coverage': float(coverage[choice]), 'gap': int(separation[choice] - radius),
                                       'quality': quality})
        if batch % 10 == 0:
            print(batch * 128, len(candidates), round(time.time() - start, 1), flush=True)
    candidates.sort(key=lambda candidate: -candidate['quality'])
    Path(output).write_text(json.dumps(candidates))
    print('finished',len(candidates), 'seconds',time.time() - start, flush=True)
    for candidate in candidates[:20]:
        print({key: value if key != 'cluster' else len(value) for key, value in candidate.items() if key != 'bonds'}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=4096)
    parser.add_argument('--seed', type=int, default=725)
    parser.add_argument('--output', default='survey.json')
    parser.add_argument('--minimum', type=int, default=6)
    parser.add_argument('--maximum', type=int, default=1000)
    arguments = parser.parse_args()
    survey(arguments.count, arguments.seed, arguments.output, arguments.minimum, arguments.maximum)
