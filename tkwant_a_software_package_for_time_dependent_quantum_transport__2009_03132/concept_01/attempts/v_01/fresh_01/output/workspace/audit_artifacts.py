import argparse
import csv
import hashlib
import json
import runpy
import shutil
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from driver import summarize
from transport.model import load_suite


def rows(path):
    with open(path) as handle:
        return list(csv.DictReader(handle))


def audit(output, replay=False):
    output = Path(output).resolve()
    tables = {name: {row['row_id']: row for row in rows(output / name)} for name in
              ['results.csv', 'ablation.csv', 'scaling.csv', 'comparisons.csv', 'history.csv', 'qualification.csv', 'checks.csv']}
    count = 0
    for input_name, directory, configuration, table_name in [
            ('development', 'production', 'production', 'results.csv'),
            ('development', 'conservative', 'conservative', 'ablation.csv'),
            ('development', 'ablation', 'ablation', 'ablation.csv'),
            ('controls', 'scaling', 'production', 'scaling.csv')]:
        for case in load_suite(output / 'inputs' / (input_name + '.json')):
            path = output / 'runs' / directory / (case['id'] + '.npz')
            result = dict(np.load(path))
            assert set(result) == {'times', 'density', 'current'}
            assert np.array_equal(result['times'], case['times'])
            assert result['density'].shape == (len(case['times']), len(case['hamiltonian']['real']))
            assert result['current'].shape == (len(case['times']), len(case['current_bonds']))
            assert all(np.all(np.isfinite(value)) for value in result.values())
            assert result['density'].min() >= -1e-7 and result['density'].max() <= 1 + 1e-5
            metadata = json.loads(path.with_suffix('.json').read_text())
            calculated = summarize(case, result, metadata, configuration)
            retained = tables[table_name][calculated['row_id']]
            for key, value in calculated.items():
                if isinstance(value, str):
                    assert value == retained[key]
                else:
                    assert abs(value - float(retained[key])) <= 1e-12 * max(1., abs(value))
            count += 1
    assert len(tables['results.csv']) == 6 and len(tables['ablation.csv']) == 12 and len(tables['scaling.csv']) == 3
    qualification_count = 0
    for row in tables['qualification.csv'].values():
        path = output / 'runs' / 'qualification' / row['config'] / (row['case'] + '.npz')
        trace = dict(np.load(path))
        metadata = json.loads(path.with_suffix('.json').read_text())
        assert all(np.all(np.isfinite(value)) for value in trace.values())
        calculated = summarize(dict(id=row['case'], family=row['family']), trace, metadata, row['config'])
        for key, value in calculated.items():
            if not isinstance(value, str):
                assert abs(value - float(row[key])) <= 1e-12 * max(1., abs(value))
        reference_path = None
        if row['config'] in ['energy_only', 'time_only', 'boundary_only', 'finite_reference']:
            reference_path = output / 'runs' / 'production' / (row['case'] + '.npz')
        elif row['config'] in ['legacy_half_step', 'legacy_no_absorber']:
            reference_path = output / 'runs' / 'baseline' / 'controls' / (row['case'] + '.npz')
        elif row['config'] in ['hard_wall_check', 'conservative', 'ablation']:
            reference_path = output / 'runs' / 'qualification' / 'production' / (row['case'] + '.npz')
        elif row['case'] == 'sidebranch_empty_dark':
            reference_path = output / 'runs' / 'production' / 'sidebranch_development.npz'
        if reference_path is not None:
            reference = np.load(reference_path)
            for key in ['density', 'current']:
                error = float(np.max(abs(trace[key] - reference[key]))) if trace[key].size else 0.
                assert abs(error - float(row[key + '_error'])) < 1e-12
        if 'independent_landauer_current' in metadata:
            error = abs(np.sum(trace['current'][0, :2]) - metadata['independent_landauer_current'])
            assert abs(error - float(row['landauer_current_error'])) < 1e-12
        if 'late_current_peak' in metadata:
            peak = np.max(abs(trace['current'][trace['times'] >= 50, 1]))
            assert abs(peak - float(row['late_current_peak'])) < 1e-12
        qualification_count += 1
    claims = json.loads((output / 'claims.json').read_text())['claims']
    assert len(claims) >= 3

    def lookup(reference):
        return float(tables[reference['table']][reference['row_id']][reference['column']])

    for claim in claims:
        left = lookup(claim['left'])
        right = lookup(claim['right']) if 'right' in claim else claim['value']
        comparison = claim['comparison']
        if comparison == 'le':
            valid = left <= right
        elif comparison == 'ge':
            valid = left >= right
        elif comparison == 'abs_difference_le':
            valid = abs(left - right) <= claim['tolerance']
        elif comparison == 'relative_difference_le':
            valid = abs(left - right) / max(abs(left), abs(right), 1e-12) <= claim['tolerance']
        else:
            raise AssertionError(comparison)
        assert valid, (claim['id'], left, right)
    primary_rows = rows(output / 'figures' / 'primary_result.csv')
    assert len(primary_rows) == sum(len(case['times']) for case in load_suite(output / 'inputs' / 'development.json'))
    assert len({(row['case'], row['time']) for row in primary_rows}) == len(primary_rows)
    for record in primary_rows:
        trace = np.load(output / 'runs' / record['config'] / (record['case'] + '.npz'))
        index = int(np.argmin(abs(trace['times'] - float(record['time']))))
        assert abs(trace['times'][index] - float(record['time'])) < 1e-12
        assert abs(np.sum(trace['density'][index]) - float(record['density_sum'])) < 1e-12
        assert abs(trace['current'][index, 0] - float(record['current_0'])) < 1e-12
    for record in rows(output / 'figures' / 'robustness_or_scaling.csv'):
        for key in ['runtime_s', 'peak_rss_mb']:
            assert float(record[key]) == float(tables['scaling.csv'][record['row_id']][key])
    for name in ['primary_result', 'robustness_or_scaling']:
        with Image.open(output / 'figures' / (name + '.png')) as image:
            image.verify()
    tests = [json.loads(line) for line in (output / 'runs' / 'tests.jsonl').read_text().splitlines()]
    assert all(test['passed'] for test in tests)
    result = dict(passed=True, required_traces_checked=count, claims_checked=len(claims),
                  qualification_traces_checked=qualification_count,
                  assertion_tests_passed=len(tests), figure_sources_verified=True)
    if (output / 'replay.json').exists():
        differences = []
        for record in json.loads((output / 'replay.json').read_text())['comparisons']:
            original = np.load(output / 'runs' / record['config'] / (record['case'] + '.npz'))
            repeated = np.load(output / 'runs' / 'replay' / record['config'] / (record['case'] + '.npz'))
            for key in ['density', 'current']:
                difference = float(np.max(abs(original[key] - repeated[key])))
                assert difference == record[key + '_difference']
                differences.append(difference)
        assert max(differences) < 1e-9
        result['full_production_ablation_replay_max_difference'] = max(differences)
    if replay:
        directory = output / 'runs' / 'portability'
        submission = directory / 'submission'
        caller = directory / 'caller'
        caller.mkdir(parents=True, exist_ok=True)
        (submission / 'workspace').mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / 'run.sh', submission / 'run.sh')
        shutil.copy2(output / 'workspace' / 'driver.py', submission / 'workspace' / 'driver.py')
        shutil.copytree(output / 'workspace' / 'transport', submission / 'workspace' / 'transport',
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        case = runpy.run_path(str(output / 'workspace' / 'tests' / 'test_accuracy.py'))['uniform_case']()
        case['id'] = 'portable_unknown_identifier'
        case['family'] = 'unrecognized_family'
        case['times'] = [0., .3, 1.9, 4.3]
        case['drives'] = [dict(kind='add', profile='pulse', amplitude=.4, duration=1.5, entries=[[0, 0, 1., 0.]])]
        (directory / 'cases.json').write_text(json.dumps(dict(cases=[case])))
        for configuration in ['production', 'ablation']:
            subprocess.run(['bash', str(submission / 'run.sh'), '--cases', '../cases.json',
                            '--output', '../' + configuration, '--config', configuration], cwd=caller, check=True)
        production = np.load(directory / 'production' / (case['id'] + '.npz'))
        ablation = np.load(directory / 'ablation' / (case['id'] + '.npz'))
        assert abs(production['current'][0, 0] - 1 / (2 * np.pi)) < 2e-6
        assert abs(ablation['current'][0, 0]) < 2e-6
        result['minimal_copied_submission_replayed'] = True
        result['portable_ablation_initial_current_difference'] = float(abs(production['current'][0, 0] - ablation['current'][0, 0]))
    (output / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    artifact_paths = [path for path in output.glob('*') if path.suffix in ['.csv', '.md', '.json', '.sh'] and path.name != 'manifest.json']
    artifact_paths.extend((output / 'figures').glob('*'))
    artifact_paths.extend((output / 'workspace').glob('*.py'))
    artifact_paths.extend((output / 'workspace' / 'transport').glob('*.py'))
    for directory in ['production', 'conservative', 'ablation', 'scaling']:
        artifact_paths.extend((output / 'runs' / directory).glob('*.npz'))
        artifact_paths.extend((output / 'runs' / directory).glob('*.json'))
    manifest = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(artifact_paths)}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--replay', action='store_true')
    arguments = parser.parse_args()
    audit(arguments.output, arguments.replay)
