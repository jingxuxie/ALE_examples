import argparse
import json
import time

import numpy as np

from optimize import OUT, PROTOCOL, PUBLIC, fc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', default=str(OUT / 'control.json'))
    parser.add_argument('--cases')
    parser.add_argument('--name', default='audit')
    args = parser.parse_args()
    cases = fc.read_json(args.cases) if args.cases else PUBLIC
    splines, control_info = fc.validate_artifact(fc.read_json(args.artifact), PROTOCOL)
    started = time.monotonic()
    reports = []
    for first in range(0, len(cases), 4):
        batch = cases[first:first + 4]
        states = []
        scores = []
        diagnostics = []
        residuals = []
        for shape, dt in (((80, 40), 0.01), ((112, 56), 0.01), ((112, 56), 0.005)):
            initial, target, residual = fc.references(batch, shape, OUT / 'cache')
            state, diagnostic = fc.evolve(splines, batch, shape, dt, initial)
            states.append(state)
            scores.append(fc.fidelities(state, target, shape))
            diagnostics.append(diagnostic)
            residuals.append(residual)
            print('batch', first, 'grid', shape, 'dt', dt, 'scores', scores[-1].tolist(), 'seconds', round(time.monotonic() - started, 1), flush=True)
        allowances = 2 * (np.abs(scores[0] - scores[1]) + np.abs(scores[1] - scores[2])) + 2e-6
        spatial_distances = fc.state_distance(fc.prolong(states[0], (112, 56)), states[1], (112, 56))
        temporal_distances = fc.state_distance(states[1], states[2], (112, 56))
        for index, case in enumerate(batch):
            report = {'case': case, 'scores': [float(value[index]) for value in scores], 'allowance': float(allowances[index]), 'Q': float(scores[-1][index] - allowances[index]), 'spatial_distance': float(spatial_distances[index]), 'temporal_distance': float(temporal_distances[index]), 'reference_residual': max(residuals)}
            report.update({key: max(float(diagnostic[key][index]) for diagnostic in diagnostics) for key in diagnostics[0]})
            reports.append(report)
        (OUT / (args.name + '.json')).write_text(json.dumps({'controls': control_info, 'reports': reports}, indent=2) + '\n')
    print('mean Q', np.mean([report['Q'] for report in reports]), 'worst Q', min(report['Q'] for report in reports), flush=True)


if __name__ == '__main__':
    main()
