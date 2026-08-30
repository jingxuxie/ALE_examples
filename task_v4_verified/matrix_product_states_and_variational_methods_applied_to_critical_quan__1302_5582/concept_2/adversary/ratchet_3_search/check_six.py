import argparse
import json
import math
from pathlib import Path

from manybody import ExactTargets, SixContractions, np, stable_six, trusted_physics, write_json


def check_six(state, sextuples, relative_limit=.1, target_floor=1e-6):
    tensor = trusted_physics.load_tensor(state)
    current = trusted_physics.check(state)
    if not current.get('valid'):
        return {'current_v3': current, 'proposed_addition_passed': False, 'reason': 'invalid tensor'}
    lengths = sorted({positions[index + 1] - positions[index] for positions in sextuples for index in (0, 2, 4)})
    gaps = sorted({positions[index + 1] - positions[index] for positions in sextuples for index in (1, 3)})
    contractions = SixContractions(tensor, lengths, gaps)
    targets = ExactTargets(max(positions[-1] - positions[0] for positions in sextuples))
    left_indices = {label: index for index, label in enumerate(contractions.left_labels)}
    right_indices = {label: index for index, label in enumerate(contractions.right_labels)}
    batches = {length: contractions.batch(length) for length in lengths}
    records = []
    for positions in sextuples:
        spacings = [right - left for left, right in zip(positions, positions[1:])]
        left, first_gap, middle, second_gap, right = spacings
        raw_values, cumulants = batches[middle]
        left_index = left_indices[left, first_gap]
        right_index = right_indices[right, second_gap]
        exact = stable_six(positions, targets)
        if exact['third_composite_cumulant'] < target_floor:
            raise ValueError('Exact cumulant below the declared target floor')
        observed = float(cumulants[left_index, right_index])
        records.append({'positions': list(positions), 'exact_cumulant': exact['third_composite_cumulant'], 'observed_cumulant': observed,
                        'relative_error': abs(observed / exact['third_composite_cumulant'] - 1),
                        'raw_exact': exact['raw'], 'raw_observed': float(raw_values[left_index, right_index])})
    worst = max(records, key=lambda record: record['relative_error'])
    passed = worst['relative_error'] <= relative_limit
    return {'current_v3': current, 'private_proposal_not_frozen_evaluator': True, 'proposed_addition_passed': passed,
            'would_pass_all_v3_plus_proposed_addition': current['passed'] and passed,
            'relative_limit': relative_limit, 'target_floor': target_floor, 'sextuples_checked': len(records),
            'maximum_relative_error': worst['relative_error'], 'worst': worst,
            'minimum_exact_cumulant': min(record['exact_cumulant'] for record in records),
            'count_above_limit': sum(record['relative_error'] > relative_limit for record in records),
            'relative_error_quantiles': np.quantile([record['relative_error'] for record in records], [.5, .9, .99]).tolist(),
            'records': records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True)
    parser.add_argument('--targets', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    specification = json.loads(Path(arguments.targets).read_text())
    report = check_six(arguments.state, specification['sextuples'], specification['relative_tolerance'], specification['exact_target_floor'])
    write_json(arguments.output, report)
    print(json.dumps({key: value for key, value in report.items() if key not in ('records', 'current_v3')}, indent=2))


if __name__ == '__main__':
    main()
