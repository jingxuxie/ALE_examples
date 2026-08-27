import argparse
import json
from pathlib import Path

import numpy as np


def compare(expected, actual, inputs):
    candidates = {case['id']: case for case in actual['cases']}
    cases = {case['id']: case for case in inputs['cases']}
    output = []
    for truth in expected['cases']:
        predicted = candidates[truth['id']]
        shots = {shot['id']: shot for shot in predicted['shots']}
        logical_errors = []
        query_errors = []
        for shot in truth['shots']:
            candidate = shots[shot['id']]
            logical_errors.append(np.abs(np.asarray(candidate['logical_posterior']) - shot['logical_posterior']).sum() / 2)
            query_errors.extend(abs(candidate['query_probability'][query] - value)
                                for query, value in shot['query_probability'].items())
        switches = np.abs(np.asarray(predicted['switch_probability']) - truth['switch_probability'])
        observed = sum(value is not None for shot in cases[truth['id']]['shots'] for value in shot['syndrome'])
        output.append({'id': truth['id'], 'logical_tv_mean': float(np.mean(logical_errors)),
                       'logical_tv_max': float(max(logical_errors)), 'query_abs_mean': float(np.mean(query_errors)),
                       'query_abs_max': float(max(query_errors)), 'switch_abs_mean': float(np.mean(switches)),
                       'switch_abs_max': float(max(switches)),
                       'log_evidence_per_observed_bit_abs': abs(predicted['log_evidence'] - truth['log_evidence']) / observed})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected', required=True)
    parser.add_argument('--actual', required=True)
    parser.add_argument('--input', required=True)
    arguments = parser.parse_args()
    print(json.dumps(compare(json.loads(Path(arguments.expected).read_text()),
                             json.loads(Path(arguments.actual).read_text()),
                             json.loads(Path(arguments.input).read_text())), indent=2))
