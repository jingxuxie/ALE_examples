import csv
import json
from pathlib import Path
import numpy as np
from metrics import read_output, error_metric
from sandbox_run import execute


def table(path):
    with Path(path).open() as handle:
        return list(csv.DictReader(handle))


def verify(submission, assets, output):
    checks, errors = {}, []
    try:
        results = table(submission / 'results.csv')
        scaling = table(submission / 'scaling.csv')
        ablations = table(submission / 'ablation.csv')
        tables = {'results.csv': results, 'scaling.csv': scaling, 'ablation.csv': ablations}
        assert all(len({row['row_id'] for row in rows}) == len(rows) for rows in tables.values())
        assert all(len(rows) for rows in tables.values())
        data = {}
        for experiment in sorted({row['experiment'] for row in results}):
            directory = submission / 'runs' / experiment
            observed = read_output(directory)
            case = json.loads((directory / 'case.json').read_text())
            profile = (directory / 'profile.txt').read_text().strip()
            submitted = [row for row in results if row['experiment'] == experiment]
            assert len(submitted) == len(observed['rows'])
            for row, actual in zip(submitted, observed['rows']):
                assert row['case'] == case['id'] and row['profile'] == profile
                assert all(abs(float(row[name]) - value) < 1e-8 for name, value in actual.items())
            scale = next(row for row in scaling if row['row_id'] == experiment)
            assert abs(float(scale['seconds']) - observed['stats']['seconds']) < 1e-6
            assert abs(float(scale['peak_rss_mb']) - observed['stats']['peak_rss_mb']) < 1e-6
            assert json.loads(scale['settings']) == observed['stats']['settings']
            data[experiment] = (case, profile, observed)
        checks['tables_match_runs'] = True
        distinct_cases = set()
        for row in ablations:
            case, profile, first = data[row['left_run']]
            other_case, other_profile, second = data[row['right_run']]
            assert case != other_case or first['stats']['settings'] != second['stats']['settings']
            matches = [(left, right) for left in first['rows'] for right in second['rows'] if abs(left['time'] - right['time']) < 1e-8]
            assert matches
            differences = [left[column] - right[column] for left, right in matches
                           for column in ['charge', 'current', 'source', 'number', 'spin', 'phonon']]
            rms = float(np.sqrt(np.mean(np.square(differences))))
            assert abs(rms - float(row['observable_rms_difference'])) < 1e-8
            assert abs(abs(first['initial_energy'] - second['initial_energy']) - float(row['initial_energy_difference'])) < 1e-8
            distinct_cases.add(case['family'])
        assert len(distinct_cases) >= 3
        checks['genuine_ablations'] = True
        claims = json.loads((submission / 'claims.json').read_text())['claims']
        assert len(claims) >= 3
        for claim in claims:
            if claim['table'] not in tables:
                supplemental = (submission / claim['table']).resolve()
                assert supplemental.is_relative_to(submission.resolve()) and supplemental.suffix == '.csv'
                tables[claim['table']] = table(supplemental)
            rows = {row['row_id']: row for row in tables[claim['table']]}
            left = float(rows[claim['lhs']['row_id']][claim['lhs']['column']])
            right_spec = claim['rhs']
            right = float(right_spec['value']) if 'value' in right_spec else float(rows[right_spec['row_id']][right_spec['column']])
            assert {'lt': left < right, 'le': left <= right, 'gt': left > right, 'ge': left >= right,
                    'eq': abs(left - right) <= 1e-8}[claim['op']]
        checks['claims_supported'] = True
        for name, candidates in [('primary_result', [results]), ('robustness_or_scaling', [scaling, ablations])]:
            assert (submission / 'figures' / (name + '.png')).stat().st_size > 100
            source = table(submission / 'figures' / (name + '.csv'))
            assert source
            indexed_candidates = [{row['row_id']: row for row in candidate} for candidate in candidates]
            for row in source:
                assert any(row.get('row_id') in indexed and all(str(value) == str(indexed[row['row_id']][column])
                           for column, value in row.items() if column in indexed[row['row_id']]) for indexed in indexed_candidates)
        assert (submission / 'report.md').stat().st_size > 200
        checks['figures_and_report'] = True
        reruns = []
        production_runs = [(name, value) for name, value in data.items() if value[1] == 'production']
        alternative_runs = [(name, value) for name, value in data.items() if value[1] in ['baseline', 'refined']]
        assert production_runs and alternative_runs
        production_runs.sort(key=lambda item: (item[0] != item[1][0]['id'] + '_' + item[1][1], item[1][0].get('family') != 'paired', item[1][0]['n_sites']))
        alternative_runs.sort(key=lambda item: (item[0] != item[1][0]['id'] + '_' + item[1][1], item[1][0].get('family') != 'vibronic', item[1][0]['n_sites']))
        for experiment, (case, profile, expected) in [production_runs[0], alternative_runs[0]]:
            case_path = submission / 'runs' / experiment / 'case.json'
            run_directory = output / experiment
            execution = execute(submission, assets, case_path, run_directory, profile)
            assert execution['status'] == 'ok'
            actual = read_output(run_directory)
            discrepancy, _ = error_metric(case, actual, expected)
            assert discrepancy < 2e-4
            reruns.append({'experiment': experiment, 'discrepancy': discrepancy, **execution})
        assert len(reruns) >= 2
        checks['fresh_reruns_match'] = True
        return {'score': 1.0, 'checks': checks, 'reruns': reruns, 'errors': []}
    except Exception as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    return {'score': len(checks) / 5, 'checks': checks, 'errors': errors}
