import copy
import csv
import hashlib
import json
import multiprocessing
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import psutil

from .diagnostics import diagnostics, distance
from .engine import solve
from .figures import plot_rows
from .io import load_case


def write_table(filename, rows):
    if not rows:
        Path(filename).write_text('row_id\n')
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(filename).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_case(case, destination, options, configuration):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    peak = [process.memory_info().rss]
    finished = threading.Event()

    def sample_memory():
        while not finished.wait(0.002):
            peak[0] = max(peak[0], process.memory_info().rss)

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    start = time.perf_counter()
    result = solve(case, options)
    elapsed = time.perf_counter() - start
    result = {key: np.asarray(value) for key, value in result.items()}
    np.savez_compressed(destination / 'result.npz', **result)
    metrics = diagnostics(result)
    metrics.update({'case': case['id'], 'family': case['family'], 'configuration': configuration,
                    'wall_seconds': elapsed,
                    'dimension': len(case['H0']), 'samples': len(case['times']),
                    'config_digest': hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()})
    arrays = {key: value for key, value in case.items() if isinstance(value, np.ndarray)}
    manifest = {key: value for key, value in case.items() if key not in arrays}
    manifest['arrays'] = 'input.npz'
    np.savez_compressed(destination / 'input.npz', **arrays)
    (destination / 'input.json').write_text(json.dumps(manifest, indent=2))
    (destination / 'options.json').write_text(json.dumps(options, indent=2))
    peak[0] = max(peak[0], process.memory_info().rss)
    finished.set()
    sampler.join()
    metrics['peak_mib'] = peak[0] / 1024 ** 2
    metrics['memory_measurement'] = 'process_RSS_sampled_2ms'
    (destination / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    return result, metrics


def isolated_run(case, destination, options, configuration):
    process = multiprocessing.get_context('spawn').Process(target=run_case,
                                                           args=(case, destination, options, configuration))
    process.start()
    process.join(60)
    if process.is_alive():
        process.terminate()
        process.join()
        raise RuntimeError('Run exceeded 60 seconds: ' + case['id'] + '/' + configuration)
    if process.exitcode:
        raise RuntimeError('Run failed: ' + case['id'] + '/' + configuration)
    with np.load(Path(destination) / 'result.npz', allow_pickle=False) as archive:
        raw = {key: archive[key] for key in archive.files}
    metrics = json.loads((Path(destination) / 'metrics.json').read_text())
    return raw, metrics


def campaign(input_directory, output_directory, configurations):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    rows = []
    scaling = []
    for filename in sorted(Path(input_directory).glob('*.json')):
        case = load_case(filename)
        records = {}
        for configuration in ['production', 'ablation', 'refined']:
            raw, metrics = isolated_run(case, output_directory / 'runs' / case['id'] / configuration,
                                    configurations[configuration], configuration)
            records[configuration] = (raw, metrics)
        for configuration, (raw, metrics) in records.items():
            row = {'row_id': case['id'] + '/' + configuration, **metrics,
                   'distance_to_refined': distance(raw, records['refined'][0]),
                   'state_distance_to_refined': float(np.max(np.linalg.norm(raw['states'] - records['refined'][0]['states'], axis=(1, 2)))),
                   'channel_distance_to_refined': float(np.linalg.norm(raw['channel'] - records['refined'][0]['channel'])) if 'channel' in raw else 0.0}
            rows.append(row)
        for dimension in case.get('scaling_sizes', []):
            smaller = copy.deepcopy(case)
            for name in ['H0', 'rho0']:
                smaller[name] = case[name][:dimension, :dimension].copy()
            for name in ['h_ops', 'c_ops', 'a_ops', 'e_ops']:
                smaller[name] = case[name][:, :dimension, :dimension].copy()
            smaller['rho0'] /= np.trace(smaller['rho0'])
            smaller['id'] = case['id'] + '_size_' + str(dimension)
            raw, metrics = isolated_run(smaller, output_directory / 'runs' / smaller['id'] / 'production',
                                    configurations['production'], 'production')
            embedded = np.zeros_like(records['production'][0]['states'])
            embedded[:, :dimension, :dimension] = raw['states']
            scaling.append({'row_id': smaller['id'], **metrics,
                            'study': 'supplied_cutoff', 'implementation': 'structured',
                            'boundary_population': float(raw['states'][:, -1, -1].real.max()),
                            'distance_to_comparator': float(np.max(np.linalg.norm(embedded - records['production'][0]['states'], axis=(1, 2))))})
    from .studies import controlled_studies, resource_study
    scaling.extend(resource_study(output_directory, configurations))
    controlled_studies(input_directory, output_directory, configurations)
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
              'distance_to_refined', 'Trajectory/channel discrepancy: production versus physical/numerical ablation')
    plot_rows(scaling, output_directory / 'figures' / 'robustness_or_scaling.png',
              'wall_seconds', 'Resonator cutoff versus measured solver time')
    (output_directory / 'figures' / 'sources.json').write_text(json.dumps({
        'primary_result.png': {'table': 'ablation.csv', 'metric': 'distance_to_refined', 'rows': [row['row_id'] for row in ablations]},
        'robustness_or_scaling.png': {'table': 'scaling.csv', 'metric': 'wall_seconds', 'rows': [row['row_id'] for row in scaling]}
    }, indent=2))
    subprocess.run([sys.executable, str(Path(__file__).parents[1] / 'validate.py'), str(output_directory)], check=True)
    from .reporting import write_report
    write_report(output_directory)
