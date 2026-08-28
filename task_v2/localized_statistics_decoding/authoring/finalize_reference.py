import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    results = json.loads((ROOT / 'authoring/reference_output.json').read_text())
    by_id = {case['id']: case for case in results['cases']}
    public = ROOT / 'participant/v_01/input'
    independent = json.loads((public / 'micro_expected.json').read_text())
    errors = []
    for truth in independent['cases']:
        predicted = by_id[truth['id']]
        errors.append(abs(predicted['log_evidence'] - truth['log_evidence']))
        errors.extend(abs(left - right) for left, right in zip(predicted['mode_posterior'], truth['mode_posterior']))
        for actual, expected in zip(predicted['shots'], truth['shots']):
            errors.extend(abs(left - right) for left, right in zip(actual['logical_posterior'], expected['logical_posterior']))
            errors.extend(abs(actual['query_probability'][key] - value) for key, value in expected['query_probability'].items())
    if max(errors) > 1e-9:
        raise AssertionError(f'Independent exhaustive oracle discrepancy: {max(errors)}')
    public_ids = [case['id'] for case in json.loads((public / 'validation.json').read_text())['cases']]
    public_output = {'cases': [by_id[identifier] for identifier in public_ids]}
    save(public / 'validation_expected.json', public_output)
    save(ROOT / 'evaluator/v_01/hidden/public_expected.json', public_output)
    save(ROOT / 'solution/v_01/validation_predictions.json', public_output)
    for path in sorted((ROOT / 'evaluator/v_01/hidden').glob('case_*.json')):
        if path.name.endswith('_expected.json'):
            continue
        identifier = json.loads(path.read_text())['cases'][0]['id']
        save(path.with_name(path.stem + '_expected.json'), {'cases': [by_id[identifier]]})
    save(ROOT / 'authoring/oracle_check.json', {'independent_micro_max_error': max(errors),
                                              'checked_cases': len(independent['cases'])})
    print(json.dumps({'independent_micro_max_error': max(errors), 'reference_cases': len(by_id)}))


if __name__ == '__main__':
    main()
