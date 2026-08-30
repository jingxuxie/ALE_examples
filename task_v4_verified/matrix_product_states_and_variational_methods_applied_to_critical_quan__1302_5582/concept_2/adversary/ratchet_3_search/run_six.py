import csv
import hashlib
import itertools
import json
import time

from manybody import CONCEPT, ROOT, ExactTargets, SixContractions, high_precision_six, np, stable_six, trusted_physics, validate_ed, write_json


def scan(version):
    started = time.monotonic()
    path = CONCEPT / 'attempts' / version / 'state.npz'
    tensor = trusted_physics.load_tensor(path)
    lengths = (2, 4, 8, 16, 24, 32, 48, 64, 96)
    gaps = (2, 4, 8, 16, 24, 32, 48, 64, 96)
    contractions = SixContractions(tensor, lengths, gaps)
    targets = ExactTargets(512)
    records = []
    for middle in lengths:
        raw_values, connected_values = contractions.batch(middle)
        for left_index, (left, first_gap) in enumerate(contractions.left_labels):
            for right_index, (right, second_gap) in enumerate(contractions.right_labels):
                spacings = (left, first_gap, middle, second_gap, right)
                positions = tuple(map(int, np.r_[0, np.cumsum(spacings)]))
                span = positions[-1]
                if span > 512:
                    continue
                exact = stable_six(positions, targets)
                observed_raw = float(raw_values[left_index, right_index])
                observed_connected = float(connected_values[left_index, right_index])
                records.append({'left': left, 'first_gap': first_gap, 'middle': middle, 'second_gap': second_gap, 'right': right,
                                'span': span, 'exact_raw': exact['raw'], 'observed_raw': observed_raw,
                                'exact_cumulant': exact['third_composite_cumulant'], 'observed_cumulant': observed_connected,
                                'raw_relative_error': abs(observed_raw / exact['raw'] - 1),
                                'cumulant_relative_error': abs(observed_connected / exact['third_composite_cumulant'] - 1)})
    with (ROOT / f'{version}_six_scan.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    strata = {}
    for maximum_span in (64, 128, 256, 512):
        for minimum_length in (2, 8, 16):
            for floor in (1e-8, 1e-6, 1e-4):
                eligible = [record for record in records if record['span'] <= maximum_span and min(record['left'], record['middle'], record['right']) >= minimum_length and record['exact_cumulant'] >= floor]
                if not eligible:
                    continue
                strata[f'span{maximum_span}_lengthmin{minimum_length}_floor{floor}'] = {'count': len(eligible), 'worst': max(eligible, key=lambda record: record['cumulant_relative_error']),
                    'error_quantiles': np.quantile([record['cumulant_relative_error'] for record in eligible], [.5, .9, .99]).tolist(),
                    'count_above_10_percent': sum(record['cumulant_relative_error'] > .1 for record in eligible),
                    'count_above_25_percent': sum(record['cumulant_relative_error'] > .25 for record in eligible)}
    selected = []
    ranked = sorted([record for record in records if record['span'] <= 256 and min(record['left'], record['middle'], record['right']) >= 8 and record['exact_cumulant'] >= 1e-6], key=lambda record: record['cumulant_relative_error'], reverse=True)
    signatures = set()
    for record in ranked:
        signature = tuple(record[key] for key in ('left', 'first_gap', 'middle', 'second_gap', 'right'))
        if signature[::-1] in signatures:
            continue
        signatures.add(signature)
        selected.append(record)
        if len(selected) == 12:
            break
    certificates = []
    for record in selected:
        spacings = [record[key] for key in ('left', 'first_gap', 'middle', 'second_gap', 'right')]
        positions = tuple(map(int, np.r_[0, np.cumsum(spacings)]))
        direct = contractions.direct_six(positions)
        exact = stable_six(positions, targets)
        precision = high_precision_six(positions)
        difference = abs(direct['third_composite_cumulant'] - record['observed_cumulant'])
        target_difference = abs(float(precision['third_composite_cumulant']) / record['exact_cumulant'] - 1)
        pairs = list(zip(positions[::2], positions[1::2]))
        four_errors = []
        for first, second in ((0, 1), (0, 2), (1, 2)):
            quartet = pairs[first] + pairs[second]
            observed = contractions.direct.evaluate(quartet)
            four_exact = targets.evaluate(quartet)
            four_errors.append(abs(observed['covariance'] / four_exact['covariance'] - 1))
        certificates.append({'positions': positions, 'batch_record': record, 'sequential': direct, 'exact': exact, 'high_precision': precision,
                             'batch_vs_sequential_absolute_difference': difference, 'target_relative_difference': target_difference,
                             'three_constituent_four_covariance_relative_errors': four_errors})
        if difference > 2e-11 or target_difference > 2e-8:
            raise RuntimeError('Independent candidate audit failed')
    proposal_mesh = [record for record in records if all(record[key] in (8, 16, 32, 64) for key in ('left', 'first_gap', 'middle', 'second_gap', 'right')) and record['span'] <= 256]
    result = {'version': version, 'tensor_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'sextuples_scanned': len(records),
              'lengths': lengths, 'gaps': gaps, 'strata': strata, 'selected': selected, 'independent_certificates': certificates,
              'regular_mesh_8_16_32_64_span256': {'count': len(proposal_mesh), 'maximum_relative_error': max(record['cumulant_relative_error'] for record in proposal_mesh),
                  'minimum_exact_cumulant': min(record['exact_cumulant'] for record in proposal_mesh),
                  'count_above_10_percent': sum(record['cumulant_relative_error'] > .1 for record in proposal_mesh),
                  'count_above_25_percent': sum(record['cumulant_relative_error'] > .25 for record in proposal_mesh),
                  'worst': max(proposal_mesh, key=lambda record: record['cumulant_relative_error'])},
              'elapsed_seconds': time.monotonic() - started}
    write_json(ROOT / f'{version}_six_results.json', result)
    print(json.dumps({'event': 'six_scan_complete', 'version': version, 'count': len(records), 'mesh': result['regular_mesh_8_16_32_64_span256'], 'selected': selected[:3], 'elapsed_seconds': result['elapsed_seconds']}, indent=2), flush=True)


def main():
    certificates = validate_ed()
    print(json.dumps({'event': 'six_ed_certified', 'sizes': [record['size'] for record in certificates['finite_spin_ed']], 'sextuples': sum(record['sextuples_checked'] for record in certificates['finite_spin_ed'])}), flush=True)
    scan('v_6')
    scan('v_5')


if __name__ == '__main__':
    main()
