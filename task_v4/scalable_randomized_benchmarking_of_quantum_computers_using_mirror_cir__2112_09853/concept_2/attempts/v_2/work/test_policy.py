import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'participant' / 'workspace'))
sys.path.insert(0, str(ROOT / 'submission'))
from model import Episode, FAMILIES, SHAPES
from policy import Policy

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=2026)
parser.add_argument('--family', default='all')
parser.add_argument('--shape', default='all')
parser.add_argument('--save', default='')
args = parser.parse_args()
records = []
for family in FAMILIES:
    if args.family not in ('all', family):
        continue
    for shape in SHAPES:
        if args.shape not in ('all', 'x'.join(map(str, shape))):
            continue
        seed = args.seed + 1009 * FAMILIES.index(family) + 53 * SHAPES.index(shape)
        episode = Episode(seed, family, shape)
        policy = Policy(episode.hello(), episode.handle)
        start = time.monotonic()
        cpu_start = time.process_time()
        policy.run()
        elapsed = time.monotonic() - start
        record = dict(family=family, shape=shape, seed=seed, elapsed=elapsed,
                      cpu=time.process_time() - cpu_start, **episode.metrics())
        inclusion = (policy.samples[:, 1 + policy.edge_count:policy.rate_count] > 0).mean(axis=0)
        lookup = {tuple(pair): index for index, pair in enumerate(episode.grid.pairs)}
        truth = episode.crosstalk[[lookup[tuple(pair)] for pair in policy.pairs]]
        record.update(support_true=int((truth > 0).sum()), support_mean=float(inclusion.sum()),
                      support_found=int(((truth > 0) & (inclusion > 0.5)).sum()),
                      support_false=int(((truth == 0) & (inclusion > 0.5)).sum()))
        records.append(record)
        print(json.dumps(record), flush=True)
        if args.save:
            prefix = ROOT / 'work' / f'{args.save}_{family}_{shape[0]}x{shape[1]}'
            Path(str(prefix) + '.json').write_text(json.dumps(dict(rows=policy.rows, predictions=episode.predictions, targets=episode.targets)))
            np.savez(str(prefix) + '.npz', samples=policy.samples, state=policy.state,
                     truth=np.r_[episode.idle, episode.base, truth], features=policy.features(episode.targets))
if records:
    family_scores = []
    for family in FAMILIES:
        errors = [record['normalized_mse'] for record in records if record['family'] == family]
        if errors:
            family_scores.append(1 / (1 + np.mean(errors)))
    print(json.dumps(dict(mean=float(np.mean(family_scores)), worst=float(np.min(family_scores)), scores=family_scores)))
