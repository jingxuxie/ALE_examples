import argparse
import itertools
import json
import multiprocessing
import time
from pathlib import Path

import numpy as np
from scipy.stats import qmc

from optimize import PROTOCOL, PUBLIC, fc


def ensemble():
    names = list(PROTOCOL['uncertainty'])
    cases = list(PUBLIC)
    rows = list(itertools.product([-1., 1.], repeat=8))
    rows.extend((2 * qmc.Sobol(8, scramble=True, seed=1951).random_base2(5) - 1).tolist())
    for index, row in enumerate(rows):
        values = dict(PROTOCOL['nominal'])
        for name, coordinate in zip(names, row):
            lower, upper = PROTOCOL['uncertainty'][name]
            values[name] = (lower + upper) / 2 + coordinate * (upper - lower) / 2
        cases.append(dict(id='stress_%03d' % index, family='joint', **values))
    for family, selected in [('interaction', ['g', 'self_ratio', 'cross_ratio']), ('calibration', ['rf_gain', 'bias', 'gradient']), ('trap', ['trap_x', 'trap_y', 'gradient'])]:
        for index, row in enumerate(itertools.product([-1., 1.], repeat=3)):
            values = dict(PROTOCOL['nominal'])
            for name, coordinate in zip(selected, row):
                lower, upper = PROTOCOL['uncertainty'][name]
                values[name] = (lower + upper) / 2 + coordinate * (upper - lower) / 2
            cases.append(dict(id=family + '_stress_%d' % index, family=family, **values))
    return cases


def run_group(task):
    cases, artifact, shape, dt, full = task
    splines, controls = fc.validate_artifact(artifact, PROTOCOL)
    if not full:
        initial, target, residual = fc.references(cases, shape, Path('cache'))
        state, diagnostics = fc.evolve(splines, cases, shape, dt, initial)
        return fc.fidelities(state, target, shape), diagnostics, None
    levels = [((80, 40), .01), ((112, 56), .01), ((112, 56), .005)]
    states, scores, audits = [], [], []
    for grid, step in levels:
        initial, target, residual = fc.references(cases, grid, Path('cache'))
        state, diagnostics = fc.evolve(splines, cases, grid, step, initial)
        states.append(state)
        scores.append(fc.fidelities(state, target, grid))
        audits.append(diagnostics)
        print('completed', cases[0]['id'], grid, step, flush=True)
    allowance = 2 * (np.abs(scores[0] - scores[1]) + np.abs(scores[1] - scores[2])) + 2e-6
    distances = np.maximum(fc.state_distance(fc.prolong(states[0], (112,56)), states[1], (112,56)), fc.state_distance(states[1], states[2], (112,56)))
    diagnostics = {name: np.max([audit[name] for audit in audits], axis=0) for name in audits[0]}
    return np.maximum(0, scores[-1] - allowance), diagnostics, {'allowance': allowance, 'distance': distances, 'fidelity': scores[-1]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', default='best.json')
    parser.add_argument('--output', default='stress.json')
    parser.add_argument('--nx', type=int, default=64)
    parser.add_argument('--ny', type=int, default=32)
    parser.add_argument('--dt', type=float, default=.04)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--cases', default='')
    args = parser.parse_args()
    started = time.time()
    cases = fc.read_json(args.cases) if args.cases else ensemble()
    artifact = fc.read_json(args.artifact)
    tasks = [(cases[index::4], artifact, (args.nx, args.ny), args.dt, args.full) for index in range(4)]
    with multiprocessing.Pool(4) as pool:
        results = pool.map(run_group, tasks)
    scores = np.zeros(len(cases))
    diagnostics = {name: np.zeros(len(cases)) for name in ['norm_error', 'boundary_mass', 'spectral_tail']}
    refinement = {name: np.zeros(len(cases)) for name in ['allowance', 'distance', 'fidelity']} if args.full else None
    for index, (score, diagnostic, refined) in enumerate(results):
        scores[index::4] = score
        for name in diagnostics:
            diagnostics[name][index::4] = diagnostic[name]
        if args.full:
            for name in refinement:
                refinement[name][index::4] = refined[name]
    report = fc.summarize(scores, cases, PROTOCOL)
    report.update(cases=cases, fidelities=scores.tolist(), diagnostics={name: value.tolist() for name, value in diagnostics.items()}, runtime=time.time() - started)
    if args.full:
        report['refinement'] = {name: value.tolist() for name, value in refinement.items()}
        report['numerical_audits_passed'] = bool(np.max(refinement['allowance']) <= 2e-4 and np.max(refinement['distance']) <= .002 and all(np.max(diagnostics[name]) <= limit for name, limit in [('norm_error', 1e-10), ('boundary_mass', 1e-8), ('spectral_tail', 1e-8)]))
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    print('Summary', {name: report[name] for name in ['core_score', 'family_scores', 'worst_case_score', 'runtime']}, flush=True)
    print('Diagnostics', {name: value.max() for name, value in diagnostics.items()}, flush=True)
    print('Worst', [(cases[index]['id'], scores[index]) for index in np.argsort(scores)[:16]], flush=True)


if __name__ == '__main__':
    main()
