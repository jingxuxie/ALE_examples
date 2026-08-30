import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

from sparse_fit import sparse_fit
from synthesize import load_instances, projector, rotate, schedule


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--branch', type=int, required=True)
    parser.add_argument('--seed', type=int, required=True)
    arguments = parser.parse_args()
    instance = load_instances()[2]
    matrix = projector(instance)
    first, second = 7, 10
    cross = matrix[first, second]
    difference = float((matrix[first, first] - matrix[second, second]).real)
    angle = 0.5 * math.atan2(-2 * abs(cross), difference)
    phase = float(-np.angle(cross))
    angle += arguments.branch * math.pi / 2
    residual = rotate(matrix, first, second, angle, phase)
    pure = min((first, second), key=lambda mode: abs(residual[mode, mode]))
    reduced = copy.deepcopy(instance)
    reduced['id'] += f'_core{arguments.branch}'
    reduced['target_projector'] = dict(real=residual.real.tolist(), imag=residual.imag.tolist())
    reduced['edges'] = [edge for edge in instance['edges'] if pure not in edge and abs(residual[tuple(edge)]) > 1e-12]
    reduced['budgets']['max_gates'] -= 1
    print('CORE', arguments.branch, 'pure', pure, 'edges', reduced['edges'], flush=True)
    sparse_fit(reduced, arguments.seed, 4, 400, compact=False)
    for variant in ('sparse', 'approx'):
        path = Path(f"{reduced['id']}_{variant}_{arguments.seed}.json")
        if not path.exists():
            continue
        core = json.loads(path.read_text())
        gates = [gate for layer in core['layers'] for gate in layer]
        gates.append(dict(u=first, v=second, theta=-angle, phi=phase))
        circuit = dict(id=instance['id'], layers=schedule(gates, instance['n_modes']))
        Path(f"{instance['id']}_reduced_{arguments.branch}_{arguments.seed}_{variant}.json").write_text(json.dumps(circuit))


if __name__ == '__main__':
    main()
