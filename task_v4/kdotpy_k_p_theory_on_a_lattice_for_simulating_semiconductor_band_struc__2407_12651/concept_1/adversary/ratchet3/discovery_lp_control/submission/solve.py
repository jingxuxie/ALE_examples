import time

STARTED = time.monotonic()

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

for parent in Path(__file__).resolve().parents:
    workspace = parent / 'participant' / 'workspace'
    if workspace.is_dir():
        sys.path.insert(0, str(workspace))
        break

from atlas import Atlas
from relaxation import relaxation


def improve(atlas, probabilities, baseline, deadline):
    best = baseline.copy()
    best_value = atlas.score(best)['objective']
    if probabilities is None:
        return best, 0
    supports = [np.flatnonzero(row > 1e-7).tolist() for row in probabilities]
    if any(not values for values in supports) or math.prod(map(len, supports)) > 4096:
        return best, 0
    mutable = np.array([vertex for vertex in range(atlas.vertices) if vertex not in atlas.anchors])
    moving = np.repeat(mutable, atlas.candidates)
    alternatives = np.tile(np.arange(atlas.candidates), len(mutable))
    evaluated = 0
    for core in itertools.product(*supports):
        if time.monotonic() >= deadline - 3:
            break
        for first in range(0, len(moving), 128):
            vertices = moving[first:first + 128]
            candidates = alternatives[first:first + 128]
            neighbors = np.tile(core, (len(vertices), 1))
            neighbors[np.arange(len(vertices)), vertices] = candidates
            results = atlas.evaluate_many(neighbors)
            values = np.where(results['feasible'], results['objective'], np.inf)
            selected = int(np.argmin(values))
            if values[selected] < best_value:
                best, best_value = neighbors[selected].copy(), float(values[selected])
            evaluated += len(neighbors)
    while time.monotonic() < deadline:
        neighbors = np.tile(best, (len(moving), 1))
        neighbors[np.arange(len(moving)), moving] = alternatives
        results = atlas.evaluate_many(neighbors)
        values = np.where(results['feasible'], results['objective'], np.inf)
        selected = int(np.argmin(values))
        if values[selected] >= best_value - 1e-12:
            break
        best, best_value = neighbors[selected].copy(), float(values[selected])
    return best, evaluated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    atlas = Atlas.load(arguments.input)
    with np.load(Path(arguments.input) / 'arrays.npz', allow_pickle=False) as archive:
        baseline = archive['baseline_choices']
    probabilities, bound = relaxation(atlas, seconds=35)
    choices, evaluated = improve(atlas, probabilities, baseline, STARTED + 65)
    output = Path(arguments.output)
    output.write_text(json.dumps({'choices': choices.tolist()}) + '\n')
    diagnostics = {'lp': bound, 'enumerated_candidates': evaluated,
                   'elapsed_solver_seconds': time.monotonic() - STARTED,
                   'method': 'one LP; enumerate marginal support plus one arbitrary vertex change; feasible single-site descent',
                   'uses_cached_hidden_answers': False}
    output.with_name('diagnostics.json').write_text(json.dumps(diagnostics, indent=2) + '\n')


if __name__ == '__main__':
    main()
