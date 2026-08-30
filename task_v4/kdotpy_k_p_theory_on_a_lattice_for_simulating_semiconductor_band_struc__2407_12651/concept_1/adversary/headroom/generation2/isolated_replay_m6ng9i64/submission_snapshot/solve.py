import time

STARTED = time.monotonic()

import argparse
import hashlib
import json
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


def penalized(atlas, result):
    excess = np.maximum(result['cost'] - atlas.budget, 0)
    invalid_link = np.maximum(atlas.minimum_link - result['minimum_link'], 0)
    invalid_branch = np.maximum(atlas.branch_margin - result['branch_margin'], 0)
    return result['objective'] + 0.15 * excess + 4 * result['topology_error'] + 100 * (invalid_link + invalid_branch)


def descend(atlas, initial, deadline, steps=60):
    current = np.array(initial, dtype=int).copy()
    vertices = np.array([vertex for vertex in range(atlas.vertices) if vertex not in atlas.anchors])
    moving = np.repeat(vertices, atlas.candidates)
    alternatives = np.tile(np.arange(atlas.candidates), len(vertices))
    for vertex, candidate in atlas.anchors.items():
        current[vertex] = candidate
    current_score = atlas.evaluate_many(current[None])
    value = float(penalized(atlas, current_score)[0])
    best = current.copy() if current_score['feasible'][0] else None
    for step in range(steps):
        if time.monotonic() >= deadline:
            break
        neighbors = np.tile(current, (len(moving), 1))
        neighbors[np.arange(len(moving)), moving] = alternatives
        result = atlas.evaluate_many(neighbors)
        objectives = penalized(atlas, result)
        selected = int(np.argmin(objectives))
        if objectives[selected] >= value - 1e-12:
            break
        current = neighbors[selected].copy()
        value = float(objectives[selected])
        if result['feasible'][selected]:
            best = current.copy()
    return best


def search(atlas, baseline, probabilities, deadline):
    seed = int.from_bytes(hashlib.sha256(atlas.metadata['case_id'].encode()).digest()[:4], 'little')
    random = np.random.default_rng(seed)
    best = baseline.copy()
    best_value = atlas.score(best)['objective']
    mutable = np.array([vertex for vertex in range(atlas.vertices) if vertex not in atlas.anchors])
    starts = []
    artifacts = {'lp_round_safe': baseline.copy(), 'lp_repair': baseline.copy()}
    phase_seconds = {}
    if probabilities is not None:
        probabilities = np.maximum(probabilities, 0)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        rounded = probabilities.argmax(axis=1)
        artifacts['lp_round'] = rounded.copy()
        rounded_score = atlas.score(rounded)
        if rounded_score['feasible'] and rounded_score['objective'] < best_value:
            best, best_value = rounded.copy(), rounded_score['objective']
            artifacts['lp_round_safe'] = rounded.copy()
        phase_seconds['lp_round'] = time.monotonic() - STARTED
        repaired = descend(atlas, rounded, min(deadline - 3, time.monotonic() + 3.0))
        if repaired is not None:
            value = atlas.score(repaired)['objective']
            if value < best_value:
                best, best_value = repaired, value
        artifacts['lp_repair'] = best.copy()
        phase_seconds['lp_repair'] = time.monotonic() - STARTED
        for trial in range(10):
            uniforms = random.random(atlas.vertices)
            starts.append((probabilities.cumsum(axis=1) < uniforms[:, None]).sum(axis=1).clip(0, atlas.candidates - 1))
    for initial in starts:
        if time.monotonic() >= deadline - 3:
            break
        candidate = descend(atlas, initial, min(deadline - 3, time.monotonic() + 2.5))
        if candidate is not None:
            value = atlas.score(candidate)['objective']
            if value < best_value:
                best, best_value = candidate, value
    current, current_value = best.copy(), best_value
    iteration = 0
    while time.monotonic() < deadline:
        batch_size = 192
        selections = np.tile(current, (batch_size, 1))
        mutations = 2 if iteration % 6 else int(random.integers(3, 8))
        for mutation in range(mutations):
            vertices = random.choice(mutable, size=batch_size)
            alternatives = random.integers(0, atlas.candidates, size=batch_size)
            if probabilities is not None and mutation == 0:
                alternatives = (probabilities[vertices].cumsum(axis=1) < random.random((batch_size, 1))).sum(axis=1).clip(0, atlas.candidates - 1)
            selections[np.arange(batch_size), vertices] = alternatives
        result = atlas.evaluate_many(selections)
        values = np.where(result['feasible'], result['objective'], np.inf)
        selected = int(np.argmin(values))
        if values[selected] < best_value:
            best, best_value = selections[selected].copy(), float(values[selected])
        temperature = 0.003 + 0.008 * (1 - (iteration % 120) / 120)
        if np.isfinite(values[selected]) and (values[selected] < current_value or random.random() < np.exp(min(0, (current_value - values[selected]) / temperature))):
            current, current_value = selections[selected].copy(), float(values[selected])
        iteration += 1
        if iteration % 120 == 0:
            current, current_value = best.copy(), best_value
    return best, {'search_batches': iteration, 'objective': best_value, 'phase_seconds': phase_seconds}, artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=65)
    parser.add_argument('--lp-seconds', type=float, default=20)
    arguments = parser.parse_args()
    atlas = Atlas.load(arguments.input)
    with np.load(Path(arguments.input) / 'arrays.npz', allow_pickle=False) as archive:
        baseline = archive['baseline_choices']
    probabilities, bound = relaxation(atlas, min(arguments.lp_seconds, max(1, arguments.seconds - 5)))
    choices, statistics, artifacts = search(atlas, baseline, probabilities, STARTED + arguments.seconds)
    destination = Path(arguments.output)
    destination.write_text(json.dumps({'choices': choices.tolist()}) + '\n')
    for name, selection in artifacts.items():
        destination.with_name(name + '.json').write_text(json.dumps({'choices': selection.tolist()}) + '\n')
    record = {'case_id': atlas.metadata['case_id'], 'family': atlas.metadata['family'], 'bound': bound,
              'search': statistics, 'score': atlas.score(choices), 'elapsed_solver_seconds': time.monotonic() - STARTED,
              'baseline_objective': atlas.metadata['baseline_objective']}
    destination.with_name('bound.json').write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
