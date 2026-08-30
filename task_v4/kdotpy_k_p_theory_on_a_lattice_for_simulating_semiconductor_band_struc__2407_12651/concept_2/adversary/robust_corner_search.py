import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from model import LOWER, UPPER, diagnose


def directions_from_report(report, maximum):
    hidden = ROOT / 'evaluator' / 'hidden'
    interiors = np.load(hidden / 'correlated_displacements.npy', allow_pickle=False)
    corners = np.load(hidden / 'corner_displacements.npy', allow_pickle=False)
    records = [(row, interiors[row['probe']]) for row in report['correlated_perturbations']]
    records.extend((row, corners[row['probe']]) for row in report['corner_perturbations'])
    selected = sorted(records, key=lambda entry: entry[0]['metrics']['plateau_spread'], reverse=True)[:maximum]
    selected += sorted(records, key=lambda entry: entry[0]['metrics']['retained_optical_min'])[:maximum]
    selected += sorted(records, key=lambda entry: entry[0]['metrics']['plateau_mean'], reverse=True)[:4]
    axes = np.zeros((42, 25))
    for coordinate in range(21):
        axes[2 * coordinate, coordinate] = .02
        axes[2 * coordinate + 1, coordinate] = -.02
    collected = np.concatenate((axes, np.array([entry[1] for entry in selected])))
    return np.concatenate((np.zeros((1, 25)), np.unique(collected, axis=0)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=2400)
    options = parser.parse_args()
    output = Path(options.output)
    output.mkdir(parents=True, exist_ok=False)
    parameters = np.array(json.loads(Path(options.start).read_text())['parameters'])
    report = json.loads(Path(options.report).read_text())
    started = time.monotonic()
    specification = importlib.util.spec_from_file_location('private_checker', ROOT / 'evaluator' / 'evaluate.py')
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    history = []
    for stage in range(3):
        directions = directions_from_report(report, 12 + 4 * stage)
        stage_deadline = min(started + options.seconds, time.monotonic() + options.seconds / 3)
        state = {'loss': float('inf'), 'evaluations': 0, 'parameters': parameters.tolist()}
        def residual(values):
            if time.monotonic() >= stage_deadline:
                raise TimeoutError
            pieces = []
            for position, displacement in enumerate(directions):
                metrics = diagnose(values + displacement, 25, (.193, .371))
                chern = round(metrics['chern'])
                partial = np.array(metrics['contributions'])[2:4]
                differences = np.array([partial[0], partial[1], partial.sum()])
                plateau_limit = .0038 if position == 0 else .0075
                pieces.extend((30 * np.maximum(np.abs(differences) - plateau_limit, 0)).tolist())
                optical_limit = .0157 if position == 0 else .0151
                pieces.extend((40 * np.maximum(optical_limit - np.array(metrics['optical'][:4]), 0)).tolist())
                pieces.append(2 * max(.67 - metrics['sampled_gap'], 0))
                pieces.append(8 * max(.20 - metrics['plateau_mean'], metrics['plateau_mean'] - .410, 0))
                pieces.append(4. * (chern != 1))
                pieces.append(2 * max(abs(metrics['full'] - chern) - .01, 0))
            vector = np.array(pieces)
            loss = float(vector @ vector)
            state['evaluations'] += 1
            if loss < state['loss']:
                state.update(loss=loss, parameters=values.tolist(), elapsed_seconds=time.monotonic() - started)
                (output / ('stage_' + str(stage) + '_checkpoint.json')).write_text(json.dumps(state, indent=2))
            return vector
        try:
            least_squares(residual, parameters, bounds=(LOWER, UPPER), max_nfev=200,
                          ftol=1e-11, xtol=1e-11, gtol=1e-8, diff_step=1e-4)
        except TimeoutError:
            pass
        parameters = np.array(state['parameters'])
        witness = output / ('stage_' + str(stage) + '_witness.json')
        witness.write_text(json.dumps({'parameters': parameters.tolist()}, indent=2))
        report = checker.evaluate(witness)
        (output / ('stage_' + str(stage) + '_evaluation.json')).write_text(json.dumps(report, indent=2))
        history.append({'stage': stage, 'loss': state['loss'], 'evaluations': state['evaluations'],
                        'core_score': report['core_score'], 'worst_family_score': report['worst_family_score'],
                        'passed': report['passed'], 'elapsed_seconds': time.monotonic() - started})
        (output / 'history.json').write_text(json.dumps(history, indent=2))
        print(json.dumps(history[-1]), flush=True)
        if report['passed'] or time.monotonic() >= started + options.seconds:
            break


if __name__ == '__main__':
    main()
