import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

workspace = Path(__file__).resolve().parents[1] / 'participant' / 'workspace'
if workspace.is_dir():
    sys.path.insert(0, str(workspace))

from atlas import Atlas, single_descent


def optimize(atlas, initial, seconds=35.0):
    deadline = time.monotonic() + seconds
    seed = int.from_bytes(hashlib.sha256(atlas.metadata['case_id'].encode()).digest()[:4], 'little')
    random = np.random.default_rng(seed)
    best = np.array(initial, dtype=np.int64).copy()
    current = best.copy()
    best_value = atlas.score(best)['objective']
    current_value = best_value
    mutable = np.array([vertex for vertex in range(atlas.vertices) if vertex not in atlas.anchors])
    iteration = 0
    while time.monotonic() < deadline:
        batch_size = 256
        neighbors = np.tile(current, (batch_size, 1))
        move_count = 2 if iteration % 5 else int(random.integers(3, 8))
        for mutation in range(move_count):
            vertices = random.choice(mutable, size=batch_size)
            candidates = random.integers(0, atlas.candidates, size=batch_size)
            neighbors[np.arange(batch_size), vertices] = candidates
        values = atlas.evaluate_many(neighbors)
        feasible_values = np.where(values['feasible'], values['objective'], np.inf)
        selected = int(np.argmin(feasible_values))
        if feasible_values[selected] < best_value - 1e-12:
            best = neighbors[selected].copy()
            best_value = float(feasible_values[selected])
        progress = (iteration % 160) / 160
        temperature = 0.016 * (1 - progress) + 0.0004
        if np.isfinite(feasible_values[selected]):
            difference = feasible_values[selected] - current_value
            if difference < 0 or random.random() < np.exp(-difference / temperature):
                current = neighbors[selected].copy()
                current_value = float(feasible_values[selected])
        iteration += 1
        if iteration % 160 == 0:
            current = best.copy()
            current_value = best_value
    final = single_descent(atlas, best)
    return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=35.0)
    arguments = parser.parse_args()
    atlas = Atlas.load(arguments.input)
    with np.load(Path(arguments.input) / 'arrays.npz', allow_pickle=False) as archive:
        initial = archive['baseline_choices']
    choices = optimize(atlas, initial, arguments.seconds)
    Path(arguments.output).write_text(json.dumps({'choices': choices.tolist()}) + '\n')


if __name__ == '__main__':
    main()
