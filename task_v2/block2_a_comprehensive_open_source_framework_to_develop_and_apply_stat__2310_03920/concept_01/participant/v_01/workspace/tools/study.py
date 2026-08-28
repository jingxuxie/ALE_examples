import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np


def read_csv(path):
    with Path(path).open() as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with Path(path).open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def collect(output):
    results, scaling, ablations = [], [], []
    runs = {}
    for run in sorted((output / 'runs').iterdir()):
        if not (run / 'trajectory.csv').exists():
            continue
        case = json.loads((run / 'case.json').read_text())
        stats = json.loads((run / 'stats.json').read_text())
        rows = read_csv(run / 'trajectory.csv')
        profile = (run / 'profile.txt').read_text().strip()
        for index, row in enumerate(rows):
            results.append({'row_id': f'{run.name}_{index}', 'experiment': run.name, 'case': case['id'], 'profile': profile, **row})
        scaling.append({'row_id': run.name, 'case': case['id'], 'profile': profile, 'n_sites': case['n_sites'],
                        'local_dimension_product': 4 ** case['n_sites'] * int(np.prod([mode['levels'] for mode in case.get('phonons', [])])),
                        'seconds': stats['seconds'], 'peak_rss_mb': stats['peak_rss_mb'],
                        'settings': json.dumps(stats['settings'], sort_keys=True)})
        runs[(case['id'], profile)] = (run.name, rows, stats)
    for case_name in sorted({key[0] for key in runs}):
        for first, second in [('legacy', 'production'), ('baseline', 'production'), ('production', 'refined')]:
            if (case_name, first) not in runs or (case_name, second) not in runs:
                continue
            first_name, first_rows, first_stats = runs[(case_name, first)]
            second_name, second_rows, second_stats = runs[(case_name, second)]
            differences = [float(left[column]) - float(right[column]) for left, right in zip(first_rows, second_rows)
                           for column in ['charge', 'current', 'source', 'number', 'spin', 'phonon']]
            ablations.append({'row_id': case_name + '_' + first + '_' + second, 'case': case_name,
                              'left_run': first_name, 'right_run': second_name, 'observable_rms_difference': float(np.sqrt(np.mean(np.square(differences)))),
                              'initial_energy_difference': abs(first_stats['initial_energy'] - second_stats['initial_energy'])})
    write_csv(output / 'results.csv', results)
    write_csv(output / 'scaling.csv', scaling)
    write_csv(output / 'ablation.csv', ablations)
    return results, scaling, ablations


def plot(output, results, scaling):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder = output / 'figures'
    folder.mkdir(exist_ok=True)
    write_csv(folder / 'primary_result.csv', results)
    write_csv(folder / 'robustness_or_scaling.csv', scaling)
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    for experiment in sorted({row['experiment'] for row in results if row['profile'] == 'production'}):
        rows = [row for row in results if row['experiment'] == experiment]
        axes[0].plot([float(row['time']) for row in rows], [float(row['current']) for row in rows], label=experiment)
        axes[1].plot([float(row['time']) for row in rows], [float(row['charge']) for row in rows], label=experiment)
    axes[0].set(xlabel='time', ylabel='inward current')
    axes[1].set(xlabel='time', ylabel='regional charge')
    axes[0].legend(fontsize=6)
    figure.tight_layout()
    figure.savefig(folder / 'primary_result.png')
    plt.close(figure)
    figure, axis = plt.subplots(figsize=(7, 4))
    for profile in ['baseline', 'production', 'refined']:
        rows = [row for row in scaling if row['profile'] == profile]
        axis.scatter([float(row['local_dimension_product']) for row in rows], [float(row['seconds']) for row in rows], label=profile)
    axis.set(xscale='log', yscale='log', xlabel='full Hilbert-space dimension', ylabel='runtime / seconds')
    axis.legend()
    figure.tight_layout()
    figure.savefig(folder / 'robustness_or_scaling.png')
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--solver', required=True)
    parser.add_argument('--cases', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--profiles', nargs='+', default=['baseline', 'production', 'refined'])
    arguments = parser.parse_args()
    output = Path(arguments.out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(arguments.cases).glob('*.json')):
        case = json.loads(path.read_text())
        for profile in arguments.profiles:
            run = output / 'runs' / (case['id'] + '_' + profile)
            run.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, run / 'case.json')
            (run / 'profile.txt').write_text(profile)
            with (run / 'run.log').open('w') as handle:
                subprocess.run(['bash', str(Path(arguments.solver).resolve()), str(path.resolve()), str(run), profile],
                               stdout=handle, stderr=subprocess.STDOUT, check=True, timeout=180)
    results, scaling, ablations = collect(output)
    plot(output, results, scaling)
    template = {'schema': 'numeric-comparisons-v1', 'claims': [
        {'text': 'Replace with your supported quantitative interpretation.', 'table': 'ablation.csv',
         'lhs': {'row_id': ablations[0]['row_id'], 'column': 'observable_rms_difference'},
         'op': 'lt', 'rhs': {'value': 0.01}}
    ]}
    (output / 'claims.template.json').write_text(json.dumps(template, indent=2))


if __name__ == '__main__':
    main()
