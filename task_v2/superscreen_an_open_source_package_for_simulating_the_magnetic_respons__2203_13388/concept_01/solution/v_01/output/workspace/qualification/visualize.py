import csv
from pathlib import Path

import matplotlib.pyplot as plt


def figures(directory):
    directory = Path(directory)
    target = directory / 'figures'
    target.mkdir(exist_ok=True)
    rows = list(csv.DictReader((directory / 'ablation.csv').open()))
    configurations = sorted({row['configuration'] for row in rows})
    figure, axes = plt.subplots(figsize=(8, 4))
    for configuration in configurations:
        subset = [row for row in rows if row['configuration'] == configuration and row['drive'] == '2']
        axes.plot([row['case'] for row in subset], [float(row['field_norm']) for row in subset], 'o-', label=configuration)
    axes.set_ylabel('Response-field norm (mT)')
    axes.legend()
    figure.tight_layout()
    figure.savefig(target / 'primary_result.png', dpi=140)
    plt.close(figure)
    rows = list(csv.DictReader((directory / 'scaling.csv').open()))
    figure, axes = plt.subplots(figsize=(7, 4))
    for configuration in configurations:
        subset = [row for row in rows if row['configuration'] == configuration]
        axes.scatter([int(row['vertices']) for row in subset], [float(row['seconds']) for row in subset], label=configuration)
    axes.set_xlabel('Total mesh vertices')
    axes.set_ylabel('Solve time (seconds)')
    axes.legend()
    figure.tight_layout()
    figure.savefig(target / 'robustness_or_scaling.png', dpi=140)
    plt.close(figure)
