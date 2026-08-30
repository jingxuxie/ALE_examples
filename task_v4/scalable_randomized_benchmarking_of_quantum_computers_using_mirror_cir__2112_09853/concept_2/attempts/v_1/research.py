import sys
import time
import argparse
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent.parent / 'participant' / 'workspace'
sys.path.insert(0, str(PUBLIC))
sys.path.insert(0, str(ROOT / 'submission'))
from model import Episode, FAMILIES, SHAPES
from policy import Policy


def run(seed, family, shape):
    episode = Episode(seed, family, shape)
    policy = Policy(episode.hello(), episode.handle)
    started = time.perf_counter()
    policy.run()
    truth = dict(zip(episode.grid.pairs, episode.crosstalk))
    coefficient_truth = np.array([truth[tuple(pair)] for pair in policy.pairs])
    selected = policy.beta[policy.offset:] > .5
    actual = coefficient_truth > 0
    metrics = episode.metrics()
    metrics.update(seed=seed, family=family, shape=shape, seconds=time.perf_counter() - started,
                   found=int(np.sum(actual & selected)), missing=int(np.sum(actual & ~selected)),
                   extra=int(np.sum(~actual & selected)),
                   base_rmse=float(np.sqrt(np.mean((episode.base - .01 * policy.beta[1:policy.offset]) ** 2))))
    print(json.dumps(metrics), flush=True)
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--seeds', type=int, default=1)
    parser.add_argument('--family', default='all')
    parser.add_argument('--shape', default='all')
    args = parser.parse_args()
    records = []
    for seed_index in range(args.seeds):
        for family_index, family in enumerate(FAMILIES):
            if args.family not in ('all', family):
                continue
            for shape_index, shape in enumerate(SHAPES):
                if args.shape not in ('all', 'x'.join(map(str, shape))):
                    continue
                seed = args.seed + 100003 * seed_index + 1009 * family_index + 53 * shape_index
                records.append(run(seed, family, shape))
    scores = {}
    for family in FAMILIES:
        losses = [record['normalized_mse'] for record in records if record['family'] == family]
        if losses:
            scores[family] = 1 / (1 + np.mean(losses))
    print(json.dumps({'scores': scores, 'mean': np.mean(list(scores.values()))}), flush=True)
