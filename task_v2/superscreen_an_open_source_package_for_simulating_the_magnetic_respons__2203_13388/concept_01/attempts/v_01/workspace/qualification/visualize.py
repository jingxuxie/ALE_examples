import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def figures(directory):
    directory = Path(directory)
    target = directory / 'figures'
    target.mkdir(exist_ok=True)
    rows = list(csv.DictReader((directory / 'ablation.csv').open()))
    configurations = ['legacy', 'legacy_exact_readout', 'smoothed_material', 'no_coupling', 'coarse', 'qualified']
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    for configuration in configurations:
        subset = [row for row in rows if row['configuration'] == configuration and row['drive'] == '2']
        for axis, metric in zip(axes, ['current_relative_error', 'near_field_relative_error']):
            axis.semilogy([row['case'] for row in subset], [max(float(row[metric]), 1e-10) for row in subset], 'o-', label=configuration)
            axis.tick_params(axis='x', rotation=20)
            axis.grid(alpha=0.2)
    axes[0].set_ylabel('Relative current difference from order 40')
    axes[1].set_ylabel('Relative near-field difference from order 40')
    axes[1].legend(fontsize=7)
    figure.tight_layout()
    figure.savefig(target / 'primary_result.png', dpi=140)
    plt.close(figure)
    rows = list(csv.DictReader((directory / 'scaling.csv').open()))
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    for configuration in ['qualified', 'fixed12', 'refined', 'reference', 'legacy']:
        subset = [row for row in rows if row['configuration'] == configuration]
        axes[0].scatter([int(row['triangles']) for row in subset], [float(row['seconds']) for row in subset], label=configuration)
        axes[1].scatter([int(row['triangles']) for row in subset], [float(row['max_rss_mib']) for row in subset], label=configuration)
    for axis in axes:
        axis.set_xlabel('Total mesh triangles')
        axis.grid(alpha=0.2)
    axes[0].set_ylabel('In-process solve time, including warm-up (s)')
    axes[1].set_ylabel('Fresh-process peak RSS (MiB)')
    axes[0].legend(fontsize=8)
    for row in rows:
        if row.get('run_kind') == 'relocated_cold':
            axes[0].annotate('cold JIT', (int(row['triangles']), float(row['seconds'])), xytext=(4, -10), textcoords='offset points', fontsize=8)
            axes[1].annotate('cold JIT', (int(row['triangles']), float(row['max_rss_mib'])), xytext=(4, -10), textcoords='offset points', fontsize=8)
    figure.tight_layout()
    figure.savefig(target / 'robustness_or_scaling.png', dpi=140)
    plt.close(figure)
