import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]


def brute(case, model):
    count = len(case['faults'])
    states = np.asarray(list(itertools.product((0, 1), repeat=count)), dtype=np.uint8)
    detectors = np.zeros((len(states), case['num_detectors']), dtype=np.uint8)
    logical = np.zeros(len(states), dtype=np.int64)
    for index, fault in enumerate(case['faults']):
        detectors[:, fault['detectors']] ^= states[:, index, None]
        logical ^= states[:, index].astype(int) * fault['logical_mask']
    modes = len(model['initial'])
    conditional = []
    for shot in case['shots']:
        observed = [index for index, value in enumerate(shot['syndrome']) if value is not None]
        syndrome = [shot['syndrome'][index] for index in observed]
        feasible = (detectors[:, observed] == syndrome).all(axis=1)
        results = []
        for mode in range(modes):
            rates = np.asarray([expit(model['offsets'][mode][fault['rate_group']]
                                      + model['slopes'][fault['rate_group']] * shot['dose'] + fault['bias'])
                                for fault in case['faults']])
            weights = np.where(states, rates, 1 - rates).prod(axis=1) * feasible
            evidence = weights.sum()
            label_weights = np.bincount(logical, weights=weights, minlength=1 << case['num_observables']) / evidence
            query = np.asarray([weights @ (states[:, entry['faults']].sum(axis=1) % 2) / evidence for entry in shot['queries']])
            results.append((evidence, label_weights, query))
        conditional.append(results)
    total = 0.0
    logical_posteriors = [np.zeros(1 << case['num_observables']) for shot in case['shots']]
    query_posteriors = [np.zeros(len(shot['queries'])) for shot in case['shots']]
    switches = np.zeros(len(case['shots']) - 1)
    for path in itertools.product(range(modes), repeat=len(case['shots'])):
        weight = model['initial'][path[0]]
        for step, mode in enumerate(path):
            weight *= conditional[step][mode][0]
            if step:
                weight *= model['transition'][path[step - 1]][mode]
        total += weight
        for step, mode in enumerate(path):
            logical_posteriors[step] += weight * conditional[step][mode][1]
            query_posteriors[step] += weight * conditional[step][mode][2]
            if step:
                switches[step - 1] += weight * (path[step - 1] != mode)
    return {'log_evidence': math.log(total), 'switches': switches / total,
            'logical': [posterior / total for posterior in logical_posteriors],
            'queries': [posterior / total for posterior in query_posteriors]}


def main():
    model = json.loads((ROOT / 'authoring/true_model_v02.json').read_text())
    inputs = json.loads((ROOT / 'participant/v_02/input/micro.json').read_text())['cases']
    expected = json.loads((ROOT / 'participant/v_02/input/micro_expected.json').read_text())['cases']
    errors = []
    for case, truth in zip(inputs, expected):
        independent = brute(case, model)
        errors.append(abs(independent['log_evidence'] - truth['log_evidence']))
        errors.extend(abs(independent['switches'] - truth['switch_probability']))
        for step, shot in enumerate(truth['shots']):
            errors.extend(abs(independent['logical'][step] - shot['logical_posterior']))
            errors.extend(abs(independent['queries'][step] - list(shot['query_probability'].values())))
    if max(errors) > 1e-9:
        raise AssertionError(max(errors))
    specification = importlib.util.spec_from_file_location('train_reference', ROOT / 'solution/v_02/train.py')
    trainer = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(trainer)
    metadata = json.loads((ROOT / 'participant/v_02/input/calibration.json').read_text())
    records = np.load(ROOT / 'participant/v_02/input/calibration_records.npz')
    subset = {key: records[key][:48] for key in records.files}
    calibration = trainer.prepare_calibration(metadata, subset)
    rates = np.asarray(model['offsets'])
    initial = np.asarray(model['initial'])
    transition = np.asarray(model['transition'])
    parameters = np.r_[rates.ravel(), model['slopes'], np.log(initial[:-1] / initial[-1]),
                        np.log(transition[:, :-1] / transition[:, -1:]).ravel()]
    _, gradient = trainer.likelihood(parameters, 3, calibration)
    finite = []
    for index in range(len(parameters)):
        left, right = parameters.copy(), parameters.copy()
        left[index] -= 1e-5
        right[index] += 1e-5
        finite.append((trainer.likelihood(right, 3, calibration)[0] - trainer.likelihood(left, 3, calibration)[0]) / 2e-5)
    gradient_error = float(np.max(np.abs(gradient - finite)))
    if gradient_error > 1e-6:
        raise AssertionError(gradient_error)
    result = {'independent_micro_max_error': float(max(errors)), 'finite_difference_gradient_max_error': gradient_error}
    (ROOT / 'authoring/v02_independent_checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
