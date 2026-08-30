import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import json
import warnings
from pathlib import Path
import numpy as np
from optimize import Grid, optimize, certificate_margins, pack, unpack

warnings.filterwarnings('ignore')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('initial')
    parser.add_argument('--output', default='fine8.json')
    parser.add_argument('--gap', type=float, default=3.000005)
    parser.add_argument('--rounds', type=int, default=12)
    args = parser.parse_args()
    coefficients = pack(json.loads(Path(args.initial).read_text()))
    support = np.flatnonzero(coefficients)
    errors = [(mass, anisotropy) for mass in np.linspace(-.05, .05, 5) for anisotropy in [0., .03, .06]]
    dense = Grid(161, errors=errors)
    base = Grid(17)
    points = set(zip(base.horizontal, base.vertical))
    for step in range(args.rounds):
        energies = dense.evaluate(coefficients, False)
        stats = dense.stats(coefficients, energies)
        margins = certificate_margins(coefficients, stats['direct'], np.min(energies[:, :, 2]-energies[:, :, 1]))
        stats['wc'] += margins[0]-.006
        stats['gc'] += .009-margins[1]
        print('ROUND', step, stats, 'points', len(points), flush=True)
        Path(args.output).write_text(json.dumps(unpack(coefficients), indent=2)+'\n')
        Path(args.output+'.stats').write_text(json.dumps(stats, indent=2)+'\n')
        for device in range(len(errors)):
            for indices in [np.argsort(energies[device, :, 0])[:4], np.argsort(-energies[device, :, 0])[:4], np.argsort(energies[device, :, 1])[:4], np.argsort(energies[device, :, 1]-energies[device, :, 0])[:4]]:
                points.update((dense.horizontal[index], dense.vertical[index]) for index in indices)
        grid = Grid(points=sorted(points), errors=errors)
        candidate, _ = optimize(coefficients, support=support, gap=args.gap, iterations=90, certified=True, grid_override=grid, verbose=False)
        change = np.max(np.abs(candidate-coefficients))
        coefficients = candidate
        if change < 1e-9:
            break
    Path(args.output).write_text(json.dumps(unpack(coefficients), indent=2)+'\n')
