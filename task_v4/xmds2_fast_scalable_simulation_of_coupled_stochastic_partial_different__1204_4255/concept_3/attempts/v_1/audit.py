import argparse
import json
import time
from pathlib import Path

import numpy as np

from optimize import PROTOCOL, PUBLIC, ROOT, fc, make_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', default='best.json')
    parser.add_argument('--output', default='audit.json')
    parser.add_argument('--cases', default='public')
    parser.add_argument('--coarse', action='store_true')
    args = parser.parse_args()
    started = time.time()
    splines, controls = fc.validate_artifact(fc.read_json(args.artifact), PROTOCOL)
    cases = make_cases(args.cases)
    levels = [((64, 32), .02)] if args.coarse else [((80, 40), .01), ((112, 56), .01), ((112, 56), .005)]
    states, scores, diagnostics = [], [], []
    for shape, dt in levels:
        initial, target, residual = fc.references(cases, shape, Path('cache'))
        state, diagnostic = fc.evolve(splines, cases, shape, dt, initial)
        fidelity = fc.fidelities(state, target, shape)
        states.append(state)
        scores.append(fidelity)
        diagnostics.append({name: value.tolist() for name, value in diagnostic.items()})
        print('level', shape, dt, 'time', time.time() - started, 'fidelities', fidelity.tolist(), 'diagnostics', {name: float(value.max()) for name, value in diagnostic.items()}, flush=True)
    if args.coarse:
        allowance = np.zeros(len(cases))
        distances = []
    else:
        allowance = 2 * (np.abs(scores[0] - scores[1]) + np.abs(scores[1] - scores[2])) + 2e-6
        distances = [fc.state_distance(fc.prolong(states[0], (112, 56)), states[1], (112, 56)), fc.state_distance(states[1], states[2], (112, 56))]
    result = fc.summarize(np.maximum(0, scores[-1] - allowance), cases, PROTOCOL)
    result.update(artifact=args.artifact, cases=[case['id'] for case in cases], fidelities=[score.tolist() for score in scores], allowance=allowance.tolist(), distances=[distance.tolist() for distance in distances], controls=controls, diagnostics=diagnostics, resource_score=fc.resource_score(splines, PROTOCOL), runtime=time.time() - started)
    result['numerical_audits_passed'] = bool(not args.coarse and max(allowance) <= 2e-4 and all(max(distance) <= .002 for distance in distances) and all(max(level[name]) <= bound for level in diagnostics for name, bound in [('norm_error', 1e-10), ('boundary_mass', 1e-8), ('spectral_tail', 1e-8)]))
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: result[name] for name in ['core_score', 'worst_case_score', 'numerical_audits_passed', 'resource_score', 'runtime']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
