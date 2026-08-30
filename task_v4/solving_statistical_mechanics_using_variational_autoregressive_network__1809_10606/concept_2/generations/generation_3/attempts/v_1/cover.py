import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

from exact import evaluate
from fit import fit_target, make_target
from minimax import minimax
from sectors import best_sector
from survey import components


def run(source, prefix):
    original = json.loads(Path(source).read_text())
    report, (energy, proposal, target, logq, gradient) = evaluate(original, True)
    ground = np.flatnonzero(energy[32768:] == energy.min())
    clusters = components(ground)
    cluster = max(clusters, key=lambda current: proposal[current + 32768].sum())
    candidate = dict(original, cluster=(cluster + 32768).tolist())
    teacher = make_target(candidate, original['beta'], softness=10)
    best_score = report['core_score']
    start = time.time()
    for index, fraction in enumerate([.2, .4, .6, .8, 1.0]):
        log_target = (1 - fraction) * logq + fraction * np.log(teacher)
        probability = np.exp(log_target - logsumexp(log_target))
        weights = fit_target(probability, original['order'])
        current = dict(original, weights=weights.tolist())
        print('initial',fraction,round(time.time()-start,1),evaluate(current),flush=True)
        current = minimax(current, 160, verbose=False)
        current, _, _ = best_sector(current, strict=False)
        report = evaluate(current)
        Path(f'{prefix}_{index}.json').write_text(json.dumps(current))
        print('refined',fraction,round(time.time()-start,1),report,flush=True)
        if report['core_score'] > best_score:
            best_score = report['core_score']
            Path(prefix + '_best.json').write_text(json.dumps(current))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--prefix', default='cover')
    arguments = parser.parse_args()
    run(arguments.source, arguments.prefix)
