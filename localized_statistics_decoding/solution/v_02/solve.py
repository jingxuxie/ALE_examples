import argparse
import copy
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logsumexp

from local_kernel import mode_shot, prepare_shot


def decode_case(case, model):
    offsets = np.asarray(model['offsets'])
    slopes = np.asarray(model['slopes'])
    initial = np.asarray(model['initial'])
    transition = np.asarray(model['transition'])
    mode_count = len(initial)
    groups = np.asarray([fault['rate_group'] for fault in case['faults']])
    biases = np.asarray([fault['bias'] for fault in case['faults']])
    results = []
    for shot in case['shots']:
        conditional = copy.deepcopy(case)
        rates = expit(offsets[:, groups] + slopes[groups] * shot['dose'] + biases)
        for fault_index, fault in enumerate(conditional['faults']):
            fault['probabilities'] = rates[:, fault_index].tolist()
        prepared = prepare_shot(conditional, shot)
        results.append([mode_shot(conditional, prepared, mode) for mode in range(mode_count)])
    emissions = np.asarray([[result[0] for result in shot] for shot in results])
    with np.errstate(divide='ignore'):
        log_transition = np.log(transition)
        forward = [np.log(initial) + emissions[0]]
    for shot_index in range(1, len(case['shots'])):
        forward.append(logsumexp(forward[-1][:, None] + log_transition, axis=0) + emissions[shot_index])
    forward = np.asarray(forward)
    backward = np.zeros_like(forward)
    for shot_index in range(len(case['shots']) - 2, -1, -1):
        backward[shot_index] = logsumexp(log_transition + emissions[shot_index + 1][None, :]
                                            + backward[shot_index + 1][None, :], axis=1)
    log_evidence = float(logsumexp(forward[-1]))
    posterior = np.exp(forward + backward - log_evidence)
    switches = []
    for shot_index in range(len(case['shots']) - 1):
        diagonal = forward[shot_index] + np.diag(log_transition) + emissions[shot_index + 1] + backward[shot_index + 1]
        switches.append(float(np.clip(1 - np.exp(diagonal - log_evidence).sum(), 0, 1)))
    output_shots = []
    for shot_index, shot in enumerate(case['shots']):
        logical = sum(posterior[shot_index, mode] * results[shot_index][mode][1] for mode in range(mode_count))
        logical /= logical.sum()
        queries = sum(posterior[shot_index, mode] * results[shot_index][mode][2] for mode in range(mode_count))
        output_shots.append({'id': shot['id'], 'logical_posterior': logical.tolist(),
                             'logical_decision': int(np.argmax(logical)),
                             'query_probability': {query['id']: float(queries[index])
                                                   for index, query in enumerate(shot['queries'])}})
    return {'id': case['id'], 'log_evidence': log_evidence, 'switch_probability': switches, 'shots': output_shots}


def solve_dataset(dataset, model):
    return {'cases': [decode_case(case, model) for case in dataset['cases']]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', default=str(Path(__file__).with_name('model.json')))
    arguments = parser.parse_args()
    model = json.loads(Path(arguments.model).read_text())
    dataset = json.loads(Path(arguments.input).read_text())
    Path(arguments.output).write_text(json.dumps(solve_dataset(dataset, model), indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
