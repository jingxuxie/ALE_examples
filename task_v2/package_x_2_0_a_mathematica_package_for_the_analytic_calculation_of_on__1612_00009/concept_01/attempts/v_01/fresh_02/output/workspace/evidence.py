import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

from experiments import flatten, save_csv
from plotting import plot_rows


ROOT = Path(__file__).resolve().parent.parent
CHANNEL_COLUMNS = [channel + component for channel in ('uv', 'ir2', 'ir1', 'finite')
                   for component in ('_re', '_im')]
PUBLIC_PROFILES = ['production', 'fixed', 'direct', 'order_8', 'order_12', 'order_20', 'order_32', 'order_52', 'order_80']


def relative(row, reference):
    return max(abs(float(row[column]) - float(reference[column])) for column in CHANNEL_COLUMNS) / max(
        max(abs(float(reference[column])) for column in CHANNEL_COLUMNS), 1e-300)


def key(row):
    return row['case_id'], row['integral_id'], row['order']


def validation():
    sys.path.insert(0, str(ROOT / 'workspace/tests'))
    import test_science
    test_science.CHECKS.clear()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'workspace/tests'))
    with (ROOT / 'validation.log').open('w') as stream:
        outcome = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    save_csv(ROOT / 'independent_checks.csv', test_science.CHECKS)
    if not outcome.wasSuccessful():
        raise RuntimeError('Scientific validation failed; see validation.log')
    print(f'{outcome.testsRun} tests passed; {len(test_science.CHECKS)} quantitative comparisons', flush=True)


def baseline_comparison():
    current = list(csv.DictReader((ROOT / 'ablation.csv').open()))
    references = {key(row): row for row in current if row['profile'] == 'direct'}
    configurations = json.loads((ROOT / 'baseline/workspace/profiles.json').read_text())
    rows = []
    for profile in ['production', 'fixed', 'direct']:
        digest = hashlib.sha256(json.dumps(configurations[profile], sort_keys=True).encode()).hexdigest()
        inherited = json.loads((ROOT / 'baseline/runs' / (profile + '.json')).read_text())
        for row in flatten(inherited, 'inherited_' + profile, digest):
            row['relative_to_direct'] = relative(row, references[key(row)])
            rows.append(row)
    rows.extend(row for row in current if row['profile'] in ['production', 'fixed', 'direct'])
    save_csv(ROOT / 'baseline_comparison.csv', rows)
    plot_rows(rows, ROOT / 'figures/primary_result.png', 'work', 'relative_to_direct')


def stress_study():
    configurations = json.loads((ROOT / 'workspace/profiles.json').read_text())
    predictions = {}
    rows = []
    scaling = []
    for profile in ['production', 'direct', 'tensor_only', 'adaptive_cyclic']:
        destination = ROOT / 'runs' / ('stress_' + profile + '.json')
        started = time.perf_counter()
        subprocess.run(['bash', str(ROOT / 'run.sh'), '--requests', str(ROOT / 'workspace/stress_requests.json'),
                        '--output', str(destination), '--profile', profile], check=True)
        elapsed = time.perf_counter() - started
        predictions[profile] = json.loads(destination.read_text())
        digest = hashlib.sha256(json.dumps(configurations[profile], sort_keys=True).encode()).hexdigest()
        rows.extend(flatten(predictions[profile], profile, digest))
        for case in predictions[profile]['cases']:
            entries = list(case['integrals'].values())
            scaling.append(dict(case_id=case['id'], family=case['family'], profile=profile, config_hash=digest,
                                seconds=case['seconds'], campaign_seconds=elapsed, work=sum(entry['work'] for entry in entries),
                                max_internal_error=max(entry['estimated_error'] for entry in entries), trace_residual=0,
                                converged=all(entry['converged'] for entry in entries)))
        print('stress', profile, 'wall seconds', round(elapsed, 3), flush=True)
    references = {key(row): row for row in rows if row['profile'] == 'direct'}
    for row in rows:
        row['relative_to_direct'] = relative(row, references[key(row)])
    for row in scaling:
        row['max_relative_to_direct'] = max(entry['relative_to_direct'] for entry in rows
                                             if entry['case_id'] == row['case_id'] and entry['profile'] == row['profile'])
    save_csv(ROOT / 'stress_ablation.csv', rows)
    save_csv(ROOT / 'stress_scaling.csv', scaling)
    plot_rows(scaling, ROOT / 'figures/adaptive_stress.png', 'work', 'max_relative_to_direct')


def summarize():
    rows = list(csv.DictReader((ROOT / 'scaling.csv').open()))
    summary = {}
    for profile in PUBLIC_PROFILES:
        selected = [row for row in rows if row['profile'] == profile]
        summary[profile] = dict(seconds=sum(float(row['seconds']) for row in selected),
                                work=sum(int(row['work']) for row in selected),
                                wall_seconds=float(selected[0]['campaign_seconds']),
                                max_relative_to_direct=max(float(row['max_relative_to_direct']) for row in selected))
    (ROOT / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-stress', action='store_true')
    arguments = parser.parse_args()
    os.chdir(ROOT)
    subprocess.run([sys.executable, str(ROOT / 'workspace/experiments.py'), '--submission', str(ROOT),
                    '--requests', str(ROOT / 'workspace/release.json'), '--profiles'] + PUBLIC_PROFILES, check=True)
    validation()
    baseline_comparison()
    if not arguments.skip_stress:
        stress_study()
    summarize()


if __name__ == '__main__':
    main()
