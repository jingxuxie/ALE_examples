import argparse
import csv
from pathlib import Path
import numpy as np
from driver import run_suite
from plotting import plot_lines


def write_csv(path, rows):
    with open(path, 'w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def experiment(input_directory, output_directory):
    inputs = Path(input_directory).resolve()
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    comparisons = []
    for configuration in ['production', 'conservative', 'ablation']:
        rows = run_suite(inputs / 'development.json', output / 'runs' / configuration, configuration)
        if configuration == 'production':
            write_csv(output / 'results.csv', rows)
        else:
            comparisons.extend(rows)
    write_csv(output / 'ablation.csv', comparisons)
    scaling = run_suite(inputs / 'controls.json', output / 'runs' / 'scaling', 'production')
    write_csv(output / 'scaling.csv', scaling)
    figures = output / 'figures'
    figures.mkdir(exist_ok=True)
    sources = []
    series = []
    for path in sorted((output / 'runs' / 'production').glob('*.npz')):
        data = np.load(path)
        series.append((path.stem, data['times'], data['current'][:, 0]))
        for index, time in enumerate(data['times']):
            sources.append(dict(case=path.stem, config='production', time=float(time), density_sum=float(np.sum(data['density'][index])), current_0=float(data['current'][index, 0])))
    write_csv(figures / 'primary_result.csv', sources)
    plot_lines(series, figures / 'primary_result.png', 'Pulse response: first monitored bond', 'time', 'particle current')
    resources = [dict(row_id=row['row_id'], runtime_s=row['runtime_s'], peak_rss_mb=row['peak_rss_mb']) for row in scaling]
    write_csv(figures / 'robustness_or_scaling.csv', resources)
    plot_lines([('runtime', list(range(len(scaling))), [row['runtime_s'] for row in scaling])], figures / 'robustness_or_scaling.png', 'Stationary, short, long controls', 'control index', 'runtime [s]')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    experiment(arguments.input, arguments.output)
