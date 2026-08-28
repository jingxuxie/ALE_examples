import argparse
import json
from pathlib import Path

import numpy as np


def compare(expected, actual):
    actual_cases = {case['id']: case for case in actual['cases']}
    results = []
    for truth in expected['cases']:
        candidate = actual_cases[truth['id']]
        candidate_shots = {shot['id']: shot for shot in candidate['shots']}
        logical_errors = []
        query_errors = []
        for shot in truth['shots']:
            predicted = candidate_shots[shot['id']]
            logical_errors.append(float(np.abs(np.asarray(shot['logical_posterior'])
                                                - np.asarray(predicted['logical_posterior'])).sum() / 2))
            query_errors.extend(abs(probability - predicted['query_probability'][query])
                                for query, probability in shot['query_probability'].items())
        results.append({'id': truth['id'], 'logical_tv_mean': float(np.mean(logical_errors)),
                        'logical_tv_max': float(max(logical_errors)),
                        'query_abs_mean': float(np.mean(query_errors)),
                        'query_abs_max': float(max(query_errors)),
                        'log_evidence_abs': abs(truth['log_evidence'] - candidate['log_evidence']),
                        'mode_tv': float(np.abs(np.asarray(truth['mode_posterior'])
                                               - np.asarray(candidate['mode_posterior'])).sum() / 2)})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected', required=True)
    parser.add_argument('--actual', required=True)
    arguments = parser.parse_args()
    expected = json.loads(Path(arguments.expected).read_text())
    actual = json.loads(Path(arguments.actual).read_text())
    print(json.dumps(compare(expected, actual), indent=2))
