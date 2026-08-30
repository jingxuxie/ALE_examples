import itertools
import json

from manybody import CONCEPT, ROOT, ExactTargets, SixContractions, TensorContractions, high_precision_six, trusted_physics, write_json


def main():
    results = {}
    targets = ExactTargets(256)
    for version in ('v_6', 'v_5'):
        report = json.loads((ROOT / f'{version}_proposed_six_score.json').read_text())
        tensor = trusted_physics.load_tensor(CONCEPT / 'attempts' / version / 'state.npz')
        contractions = TensorContractions(tensor)
        cached = {}
        selected = []
        for record in report['records']:
            if record['relative_error'] <= .1:
                continue
            positions = record['positions']
            intervals = list(zip(positions[::2], positions[1::2]))
            errors = []
            for first, second in itertools.combinations(range(3), 2):
                quartet = intervals[first] + intervals[second]
                canonical = tuple(site - quartet[0] for site in quartet)
                if canonical not in cached:
                    direct = contractions.evaluate(canonical)
                    exact = targets.evaluate(canonical)
                    cached[canonical] = abs(direct['covariance'] / exact['covariance'] - 1)
                errors.append(cached[canonical])
            if max(errors) <= .01:
                selected.append({'six_record': record, 'three_four_covariance_relative_errors': errors})
        selected.sort(key=lambda record: record['six_record']['relative_error'], reverse=True)
        if selected:
            six = SixContractions(tensor, trusted_physics.COMPOSITE_INTERVALS, trusted_physics.COMPOSITE_GAPS)
            positions = selected[0]['six_record']['positions']
            selected[0]['sequential_certificate'] = six.direct_six(positions)
            selected[0]['high_precision_certificate'] = high_precision_six(positions)
        results[version] = {'count': len(selected), 'all_three_lower_covariance_tolerance': .01, 'six_tolerance': .1, 'cases': selected}
    write_json(ROOT / 'lower_four_pass_six_fail.json', results)
    print(json.dumps({version: {'count': data['count'], 'best': data['cases'][:1]} for version, data in results.items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
