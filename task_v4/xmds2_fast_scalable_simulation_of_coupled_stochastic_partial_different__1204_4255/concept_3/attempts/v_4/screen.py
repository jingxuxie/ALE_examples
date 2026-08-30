import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np

from optimize import OUT, PROTOCOL, PUBLIC, ROOT, fc


def full_cases():
    keys = list(PROTOCOL['uncertainty'])
    corners = []
    for index, choice in enumerate(itertools.product((0, 1), repeat=8)):
        corners.append(dict(id='corner_%03d' % index, family='joint', **{key: PROTOCOL['uncertainty'][key][side] for key, side in zip(keys, choice)}))
    return corners


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', default=str(OUT / 'control.json'))
    parser.add_argument('--nx', type=int, default=48)
    parser.add_argument('--ny', type=int, default=24)
    parser.add_argument('--dt', type=float, default=0.05)
    parser.add_argument('--name', default='screen')
    parser.add_argument('--cases')
    parser.add_argument('--select', type=int, default=24)
    args = parser.parse_args()
    cases = fc.read_json(args.cases) if args.cases else full_cases()
    splines, info = fc.validate_artifact(fc.read_json(args.artifact), PROTOCOL)
    shape = (args.nx, args.ny)
    scores = []
    reports = []
    started = time.monotonic()
    for first in range(0, len(cases), 16):
        batch = cases[first:first + 16]
        initial, target, residual = fc.references(batch, shape, OUT / 'cache')
        state, audit = fc.evolve(splines, batch, shape, args.dt, initial)
        fidelities = fc.fidelities(state, target, shape)
        scores.extend(fidelities.tolist())
        volume = fc.geometry(shape)[3]
        overlaps = 2 * volume * np.sum(target.conj() * state, axis=(-2, -1))
        for index, case in enumerate(batch):
            reports.append({'case': case, 'fidelity': float(fidelities[index]), 'phase_error': float(np.angle(overlaps[index, 1] / overlaps[index, 0])), 'port_overlap': np.abs(overlaps[index]).tolist(), 'audit': {key: float(value[index]) for key, value in audit.items()}})
        print('batch', first, 'seconds', round(time.monotonic() - started, 1), 'mean', np.mean(scores), 'worst', np.min(scores), flush=True)
    reports.sort(key=lambda item: item['fidelity'])
    (OUT / (args.name + '.json')).write_text(json.dumps(reports, indent=2) + '\n')
    selected = [item['case'] for item in reports[:args.select]]
    (OUT / (args.name + '_cases.json')).write_text(json.dumps(PUBLIC + selected, indent=2) + '\n')
    print('worst', json.dumps(reports[:8], indent=2), flush=True)


if __name__ == '__main__':
    main()
