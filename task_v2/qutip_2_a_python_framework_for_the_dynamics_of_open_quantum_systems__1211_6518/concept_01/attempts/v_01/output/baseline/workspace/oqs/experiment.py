import copy
import csv
import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np

from .diagnostics import diagnostics, distance
from .engine import solve
from .figures import plot_rows
from .io import load_case


def write_table(filename, rows):
    with Path(filename).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_case(case, destination, options, configuration):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    result = solve(case, options)
    elapsed = time.perf_counter() - start
    result = {key: np.asarray(value) for key, value in result.items()}
    np.savez_compressed(destination / 'result.npz', **result)
    metrics = diagnostics(result)
    metrics.update({'case': case['id'], 'family': case['family'], 'configuration': configuration,
                    'wall_seconds': elapsed, 'peak_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                    'dimension': len(case['H0']), 'samples': len(case['times']),
                    'config_digest': hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()})
    (destination / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    return result, metrics


def campaign(input_directory, output_directory, configurations):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    rows = []
    scaling = []
    for filename in sorted(Path(input_directory).glob('*.json')):
        case = load_case(filename)
        records = {}
        for configuration in ['production', 'ablation', 'refined']:
            raw, metrics = run_case(case, output_directory / 'runs' / case['id'] / configuration,
                                    configurations[configuration], configuration)
            records[configuration] = (raw, metrics)
        for configuration, (raw, metrics) in records.items():
            row = {'row_id': case['id'] + '/' + configuration, **metrics,
                   'distance_to_refined': distance(raw, records['refined'][0])}
            rows.append(row)
        for dimension in case.get('scaling_sizes', []):
            smaller = copy.deepcopy(case)
            for name in ['H0', 'rho0']:
                smaller[name] = case[name][:dimension, :dimension].copy()
            for name in ['h_ops', 'c_ops', 'a_ops', 'e_ops']:
                smaller[name] = case[name][:, :dimension, :dimension].copy()
            smaller['rho0'] /= np.trace(smaller['rho0'])
            smaller['id'] = case['id'] + '_size_' + str(dimension)
            raw, metrics = run_case(smaller, output_directory / 'runs' / smaller['id'] / 'production',
                                    configurations['production'], 'production')
            scaling.append({'row_id': smaller['id'], **metrics,
                            'boundary_population': float(raw['states'][:, -1, -1].real.max())})
    write_table(output_directory / 'results.csv', rows)
    ablations = [row for row in rows if row['configuration'] != 'refined']
    write_table(output_directory / 'ablation.csv', ablations)
    write_table(output_directory / 'scaling.csv', scaling)
    claims = []
    for row in rows:
        if row['configuration'] == 'production':
            other = next(item for item in rows if item['case'] == row['case'] and item['configuration'] == 'ablation')
            relation = 'le' if row['distance_to_refined'] <= other['distance_to_refined'] else 'gt'
            claims.append({'id': row['case'] + '_refinement', 'table': 'results.csv',
                           'left': row['row_id'], 'right': other['row_id'],
                           'metric': 'distance_to_refined', 'relation': relation,
                           'interpretation': 'Internal refinement comparison; not an independent truth label.'})
    (output_directory / 'claims.json').write_text(json.dumps(claims, indent=2))
    plot_rows(ablations, output_directory / 'figures' / 'primary_result.png',
              'final_expectation', 'Model/implementation comparison: final first observable')
    plot_rows(scaling, output_directory / 'figures' / 'robustness_or_scaling.png',
              'wall_seconds', 'Resonator cutoff versus measured solver time')
    (output_directory / 'figures' / 'sources.json').write_text(json.dumps({
        'primary_result.png': {'table': 'ablation.csv', 'metric': 'final_expectation', 'rows': [row['row_id'] for row in ablations]},
        'robustness_or_scaling.png': {'table': 'scaling.csv', 'metric': 'wall_seconds', 'rows': [row['row_id'] for row in scaling]}
    }, indent=2))
