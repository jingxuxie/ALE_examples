import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.special import expit

from binary import solve_binary


def decode_case(case, model):
    initial = np.asarray(model['initial'])
    offsets = np.asarray(model['offsets'])
    slopes = np.asarray(model['slopes'])
    output = []
    log_evidence = 0.0
    for shot in case['shots']:
        rates = [float(initial @ expit(offsets[:, fault['rate_group']] + slopes[fault['rate_group']] * shot['dose'] + fault['bias']))
                 for fault in case['faults']]
        matrix = np.asarray([[int(row in fault['detectors']) for fault in case['faults']]
                             for row in range(case['num_detectors'])], dtype=np.uint8)
        syndrome = [0 if value is None else value for value in shot['syndrome']]
        correction = solve_binary(matrix, syndrome, np.argsort(-np.asarray(rates)))
        label = 0
        log_probability = 0.0
        for index, fault in enumerate(case['faults']):
            if correction[index]:
                label ^= fault['logical_mask']
            log_probability += math.log(rates[index] if correction[index] else 1 - rates[index])
        posterior = [float(index == label) for index in range(1 << case['num_observables'])]
        log_evidence += log_probability
        output.append({'id': shot['id'], 'logical_posterior': posterior, 'logical_decision': label,
                       'query_probability': {query['id']: float(correction[query['faults']].sum() % 2)
                                             for query in shot['queries']}})
    return {'id': case['id'], 'log_evidence': log_evidence, 'switch_probability': [0.0] * (len(output) - 1), 'shots': output}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    model = json.loads(Path(__file__).with_name('baseline_model.json').read_text())
    dataset = json.loads(Path(arguments.input).read_text())
    Path(arguments.output).write_text(json.dumps({'cases': [decode_case(case, model) for case in dataset['cases']]}, indent=2) + '\n')
