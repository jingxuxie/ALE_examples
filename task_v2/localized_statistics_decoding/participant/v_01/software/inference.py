import math

import numpy as np

from regional import hypothesis


def decode_case(case):
    modes = len(case['mode_prior'])
    mode_weights = np.asarray(case['mode_prior'], dtype=float)
    output_shots = []
    log_evidence = 0.0
    for shot in case['shots']:
        logical = np.zeros(1 << case['num_observables'])
        queries = {query['id']: 0.0 for query in shot['queries']}
        shot_evidence = 0.0
        for mode in range(modes):
            correction = hypothesis(case, shot, mode)
            label = 0
            probability = 1.0
            for index, fault in enumerate(case['faults']):
                rate = fault['probabilities'][mode]
                probability *= rate if correction[index] else 1.0 - rate
                if correction[index]:
                    label ^= fault['logical_mask']
            logical[label] += mode_weights[mode]
            shot_evidence += mode_weights[mode] * probability
            for query in shot['queries']:
                queries[query['id']] += mode_weights[mode] * int(correction[query['faults']].sum() % 2)
        log_evidence += math.log(max(shot_evidence, 1e-300))
        output_shots.append({'id': shot['id'], 'logical_posterior': logical.tolist(),
                             'logical_decision': int(np.argmax(logical)), 'query_probability': queries})
    return {'id': case['id'], 'log_evidence': log_evidence,
            'mode_posterior': mode_weights.tolist(), 'shots': output_shots}
