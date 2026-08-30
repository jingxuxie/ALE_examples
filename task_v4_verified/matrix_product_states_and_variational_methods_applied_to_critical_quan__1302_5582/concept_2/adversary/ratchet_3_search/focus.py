import csv
import hashlib
import itertools
import json
import math
import time

from manybody import CONCEPT, ROOT, ExactTargets, SixContractions, TensorContractions, high_precision_six, np, trusted_physics, write_json
from check_six import check_six
from fourpoint import high_precision_target


def main():
    started = time.monotonic()
    lengths = tuple(trusted_physics.COMPOSITE_INTERVALS)
    gaps = tuple(trusted_physics.COMPOSITE_GAPS)
    sextuples = []
    for left, first_gap, middle, second_gap, right in itertools.product(lengths, gaps, lengths, gaps, lengths):
        if left + first_gap + middle + second_gap + right <= 256:
            sextuples.append(list(map(int, np.r_[0, np.cumsum((left, first_gap, middle, second_gap, right))])))
    specification = {'private_proposal_not_frozen': True, 'observable': 'third joint cumulant of three disjoint XX interval composites',
                     'definition': '<(Q1-<Q1>)(Q2-<Q2>)(Q3-<Q3>)>; every submitted subtraction uses submitted means',
                     'interval_lengths': lengths, 'inter_interval_gaps': gaps, 'maximum_span': 256,
                     'relative_tolerance': .1, 'exact_target_floor': 1e-6, 'count': len(sextuples), 'sextuples': sextuples,
                     'rationale': 'Reuse exactly the existing length and gap alphabets and span bound, but test a new connected three-composite observable. Retain all v3 criteria unchanged.',
                     'new_target_feasibility': 'unknown; no passing witness has been sought or found for this proposal'}
    write_json(ROOT / 'proposed_six_targets.json', specification)
    summary = {'proposed_count': len(sextuples), 'versions': {}}
    targets = ExactTargets(1024)
    focused_quartets = [(0, 5, 101, 106), (0, 4, 196, 201), (0, 384, 640, 1024)]
    for version in ('v_6', 'v_5'):
        state = CONCEPT / 'attempts' / version / 'state.npz'
        tensor = trusted_physics.load_tensor(state)
        report = check_six(state, sextuples)
        write_json(ROOT / f'{version}_proposed_six_score.json', report)
        contractions = SixContractions(tensor, lengths, gaps)
        certificates = []
        for record in sorted(report['records'], key=lambda record: record['relative_error'], reverse=True)[:8]:
            positions = tuple(record['positions'])
            direct = contractions.direct_six(positions)
            precision = high_precision_six(positions)
            intervals = list(zip(positions[::2], positions[1::2]))
            four_errors = []
            for index, (first, second) in enumerate(((0, 1), (0, 2), (1, 2))):
                quartet = intervals[first] + intervals[second]
                observed_covariance = direct['four_moments_12_13_23'][index] - direct['pair_means'][first] * direct['pair_means'][second]
                exact = targets.evaluate(quartet)
                four_errors.append({'positions': quartet, 'relative_error': abs(observed_covariance / exact['covariance'] - 1)})
            batch_error = abs(direct['third_composite_cumulant'] - record['observed_cumulant'])
            precision_error = abs(float(precision['third_composite_cumulant']) / record['exact_cumulant'] - 1)
            certificates.append({'record': record, 'sequential': direct, 'high_precision': precision, 'three_four_covariance_errors': four_errors,
                                 'batch_sequential_absolute_error': batch_error, 'exact_high_precision_relative_error': precision_error})
            if batch_error > 2e-11 or precision_error > 2e-8:
                raise RuntimeError('Focused six-spin certificate failed')
        write_json(ROOT / f'{version}_focused_six_certificates.json', certificates)
        four_contractions = TensorContractions(tensor)
        quartet_records = []
        for positions in focused_quartets:
            exact = targets.evaluate(positions)
            direct = four_contractions.evaluate(positions)
            precise = high_precision_target(positions)
            pair_errors = []
            for first, second in itertools.combinations(positions, 2):
                distance = second - first
                four_contractions.prepare(distance)
                pair_errors.append(abs(four_contractions.pairs[distance] / targets.pair(distance) - 1))
            quartet_records.append({'positions': positions, 'exact': exact, 'sequential': direct, 'high_precision': precise,
                                    'covariance_relative_error': abs(direct['covariance'] / exact['covariance'] - 1),
                                    'raw_relative_error': abs(direct['raw'] / exact['raw'] - 1),
                                    'all_six_pair_max_relative_error': max(pair_errors),
                                    'exact_high_precision_relative_error': abs(float(precise['covariance']) / exact['covariance'] - 1)})
        write_json(ROOT / f'{version}_focused_four_certificates.json', quartet_records)
        audit = json.loads((ROOT / f'{version}_four' / 'archived_audit.json').read_text())
        evaluation = json.loads((ROOT / f'{version}_four' / 'archived_evaluation.json').read_text())
        summary['versions'][version] = {'source_sha256': hashlib.sha256(state.read_bytes()).hexdigest(),
            'archived_audit': {key: audit.get(key) for key in ('state', 'elapsed_seconds', 'return_code', 'timed_out', 'participant_unchanged', 'empty_output_at_launch')},
            'archived_evaluation_passed': evaluation.get('passed'),
            'current_v3_passed': report['current_v3']['passed'],
            'proposed_six': {key: value for key, value in report.items() if key not in ('records', 'current_v3')},
            'worst_certificate': certificates[0], 'focused_four': quartet_records}
    manifest = json.loads((CONCEPT / 'adversary' / 'ratchet_2' / 'freeze_manifest.json').read_text())
    frozen = []
    for record in manifest['frozen_files']:
        actual = hashlib.sha256((CONCEPT / record['path']).read_bytes()).hexdigest()
        frozen.append({'path': record['path'], 'sha256': actual, 'matches_frozen': actual == record['sha256']})
    summary['frozen_files_unchanged'] = all(record['matches_frozen'] for record in frozen)
    summary['elapsed_seconds'] = time.monotonic() - started
    write_json(ROOT / 'frozen_integrity.json', {'all_unchanged': summary['frozen_files_unchanged'], 'files': frozen})
    write_json(ROOT / 'focused_summary.json', summary)
    print(json.dumps({'count': len(sextuples), 'frozen_files_unchanged': summary['frozen_files_unchanged'], 'results': {version: {'six': data['proposed_six'], 'worst_lower_four_errors': data['worst_certificate']['three_four_covariance_errors']} for version, data in summary['versions'].items()}}, indent=2), flush=True)


if __name__ == '__main__':
    main()
