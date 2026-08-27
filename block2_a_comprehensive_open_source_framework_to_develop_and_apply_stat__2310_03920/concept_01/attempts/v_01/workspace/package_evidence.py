import csv
import json
import math
import os
from pathlib import Path
import shlex

import numpy as np
from scipy.integrate import cumulative_trapezoid


ROOT = Path(__file__).resolve().parents[1]
OBSERVABLES = ['charge', 'current', 'source', 'number', 'spin', 'phonon']
REGIMES = ['impurity', 'ladder', 'spin_orbit', 'paired', 'vibronic']


def write_csv(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def diagnostics(rows):
    values = {key: np.array([float(row[key]) for row in rows]) for key in rows[0]}
    residual = values['charge'] - values['charge'][0] - cumulative_trapezoid(
        values['current'] + values['source'], values['time'], initial=0)
    without_source = values['charge'] - values['charge'][0] - cumulative_trapezoid(
        values['current'], values['time'], initial=0)
    return dict(norm_drift=float(np.ptp(values['norm'])), energy_drift=float(np.ptp(values['energy'])),
                continuity_quadrature_residual=float(np.max(np.abs(residual))),
                continuity_without_source=float(np.max(np.abs(without_source))),
                number_change=float(np.ptp(values['number'])), spin_change=float(np.ptp(values['spin'])))


def collect():
    results, scaling, runs, failures = [], [], {}, []
    for directory in sorted((ROOT / 'runs').iterdir()):
        if not (directory / 'trajectory.csv').exists() or not (directory / 'stats.json').exists():
            if (directory / 'failure.json').exists():
                failures.append(dict(row_id=directory.name, **json.loads((directory / 'failure.json').read_text())))
            continue
        case = json.loads((directory / 'case.json').read_text())
        stats = json.loads((directory / 'stats.json').read_text())
        profile = (directory / 'profile.txt').read_text().strip()
        rows = list(csv.DictReader((directory / 'trajectory.csv').open()))
        runs[directory.name] = (case, stats, rows)
        for index, row in enumerate(rows):
            results.append(dict(row_id=f'{directory.name}_{index}', experiment=directory.name,
                                case=case['id'], profile=profile, abs_source=abs(float(row['source'])), **row))
        scaling.append(dict(row_id=directory.name, case=case['id'], profile=profile, n_sites=case['n_sites'],
                            local_dimension_product=4 ** case['n_sites'] * math.prod(
                                mode['levels'] for mode in case.get('phonons', [])),
                            seconds=stats['seconds'], peak_rss_mb=stats['peak_rss_mb'],
                            settings=json.dumps(stats['settings'], sort_keys=True),
                            sector_dimension=stats['settings'].get('sector_dimension', ''),
                            initial_energy=stats['initial_energy'],
                            initial_residual=stats.get('diagnostics', {}).get('initial_residual', ''),
                            preparation_seconds=stats.get('diagnostics', {}).get('preparation_seconds', ''),
                            initial_variance=stats.get('diagnostics', {}).get('initial_variance', ''),
                            calibration_energy_error=(abs(stats['initial_energy'] - (1 - math.sqrt(5)))
                                                      if case['id'] == 'dimer_calibration' else ''),
                            **diagnostics(rows)))
        if not profile.startswith('legacy'):
            configuration = dict(stats['settings'])
            configuration.setdefault('spin_orbitals', False)
            configuration.setdefault('number_as_sz', False)
            configuration.setdefault('one_site_after', None)
            configuration.setdefault('initial_bond', min(32, configuration['bond']))
            configuration.setdefault('bond_schedule', [min(32, configuration['bond'])] * 2 +
                                     [min(64, configuration['bond'])] * 2 + [configuration['bond']])
            configuration.setdefault('general_symmetry', configuration.get('symmetry_implementation') != 'specialized SZ')
            if 'tensor_layout' in configuration:
                configuration['mode_layout_override' if configuration.get('spin_orbitals') else 'layout_override'] = configuration['tensor_layout']
            if 'symmetry_implementation' not in configuration:
                configuration.update(davidson_tol=1e-12, krylov_tol=1e-14)
            invocation = '#!/usr/bin/env bash\nset -euo pipefail\n'
            invocation += 'HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)\n'
            invocation += 'export ALE_SETTINGS=' + shlex.quote(json.dumps(configuration)) + '\n'
            invocation += 'bash "$HERE/../../run.sh" "$HERE/case.json" "${1:?Provide an empty replay directory}" '
            invocation += shlex.quote(stats['profile']) + '\n'
            (directory / 'replay.sh').write_text(invocation)
            (directory / 'replay.sh').chmod(0o755)
        else:
            configuration = stats['settings']
            invocation = '#!/usr/bin/env bash\nset -euo pipefail\n'
            invocation += 'HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)\n'
            invocation += 'source "${ALE_ASSETS:?}/workspace/env.sh"\nexport PYTHONDONTWRITEBYTECODE=1\n'
            invocation += 'unset LEGACY_REPAIR_CLOCK LEGACY_REPAIR_U\n'
            if configuration.get('repair_clock'):
                invocation += 'export LEGACY_REPAIR_CLOCK=1\n'
            if configuration.get('repair_U'):
                invocation += 'export LEGACY_REPAIR_U=1\n'
            legacy_profile = {16: 'baseline', 24: 'production', 48: 'refined'}[configuration['bond']]
            invocation += 'python3 "$HERE/../../workspace/legacy/run.py" "$HERE/case.json" "${1:?Provide an empty replay directory}" '
            invocation += legacy_profile + '\n'
            (directory / 'replay.sh').write_text(invocation)
            (directory / 'replay.sh').chmod(0o755)
    comparisons = []
    def compare(left, right, label, purpose):
        if left not in runs or right not in runs:
            return
        left_case, left_stats, left_rows = runs[left]
        right_case, right_stats, right_rows = runs[right]
        right_by_time = {round(float(row['time']), 10): row for row in right_rows}
        matched = [(row, right_by_time[round(float(row['time']), 10)]) for row in left_rows
                   if round(float(row['time']), 10) in right_by_time]
        if not matched:
            return
        differences = np.array([[float(first[column]) - float(second[column]) for column in OBSERVABLES]
                                for first, second in matched])
        row = dict(row_id=label, case=left_case['id'], left_run=left, right_run=right,
                   observable_rms_difference=float(np.sqrt(np.mean(differences ** 2))),
                   initial_energy_difference=abs(left_stats['initial_energy'] - right_stats['initial_energy']),
                   observable_max_difference=float(np.max(abs(differences))), purpose=purpose,
                   matched_times=len(matched), left_seconds=left_stats['seconds'], right_seconds=right_stats['seconds'])
        for index, column in enumerate(OBSERVABLES):
            row[column + '_max_difference'] = float(np.max(abs(differences[:, index])))
        comparisons.append(row)
    for regime in REGIMES:
        case = regime + '_dev'
        for profile in ['legacy', 'legacy_clock', 'legacy_clock_U', 'baseline', 'tensor160', 'bond48',
                        'smallstep16', 'more_sweeps16', 'specialized', 'refined', 'final_tensor', 'modes96', 'redundant']:
            compare(case + '_' + profile, case + '_production', case + '_' + profile + '_vs_exact',
                    'legacy physics/clock' if profile.startswith('legacy') else 'finite resources / independent representation')
        compare(case + '_baseline', case + '_smallstep16', case + '_step_ablation', 'timestep only')
        compare(case + '_baseline', case + '_more_sweeps16', case + '_sweep_ablation', 'sweep count and convergence threshold')
        compare(case + '_baseline', case + '_bond48', case + '_bond_layout_ablation', 'bond dimension and oscillator layout')
    compare('mixed_nonlocal_odd_tensor160', 'mixed_nonlocal_odd_production', 'nonlocal_odd_layout',
            'independent fermion signs, odd parity, spin mixing and nonlocal pairs')
    compare('renamed_mixed_contact_tensor160', 'renamed_mixed_contact_production', 'mixed_boson_parity_layout',
            'arbitrary identifier, oscillator layout, all Hamiltonian term classes, odd parity')
    for regime, variant in [('spin_orbit', 'real_hopping'), ('vibronic', 'zero_coupling'),
                            ('ladder', 'zero_density'), ('paired', 'zero_pairing')]:
        compare(regime + '_' + variant + '_production', regime + '_dev_production', regime + '_physics_' + variant,
                'deliberately changed physical Hamiltonian: ' + variant)
    scale_cases = sorted({case['id'] for case, stats, rows in runs.values() if '_scale_' in case['id']})
    for case in scale_cases:
        candidates = ['baseline', 'refined', 'fast96', 'fast64', 'exact', 'pilot160', 'pilot', 'candidate128',
                      'modes96', 'rcm_modes128', 'rcm_modes192', 'spatial192_hybrid', 'redundant128',
                      'modes96_hybrid', 'final_policy', 'final_tensor', 'variance', 'wide_start', 'general', 'warmup',
                      'refined_warmup', 'tensor128']
        for profile in candidates:
            compare(case + '_' + profile, case + '_production', case + '_' + profile + '_vs_production',
                    'size/resource scaling')
        for profile in ['production'] + candidates:
            if profile == 'exact':
                continue
            compare(case + '_' + profile, case + '_exact', case + '_' + profile + '_vs_exact',
                    'independent sparse check at increased size')
        compare(case + '_fast64', case + '_fast96', case + '_64_vs_96', 'bond-only scaling')
    by_identifier = {row['row_id']: row for row in comparisons}
    for regime in REGIMES:
        base = by_identifier.get(regime + '_dev_baseline_vs_exact')
        fine = by_identifier.get(regime + '_dev_bond48_vs_exact')
        if base and fine:
            base['refinement_error_ratio'] = base['observable_rms_difference'] / max(fine['observable_rms_difference'], 1e-300)
    write_csv(ROOT / 'results.csv', results)
    write_csv(ROOT / 'scaling.csv', scaling)
    write_csv(ROOT / 'ablation.csv', comparisons)
    write_csv(ROOT / 'failed_runs.csv', failures)
    return results, scaling, comparisons


def plots(results, scaling, comparisons):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures = ROOT / 'figures'
    figures.mkdir(exist_ok=True)
    primary = [row for row in results if row['experiment'] in [regime + '_dev_' + profile
               for regime in REGIMES for profile in ['production', 'baseline', 'legacy']]]
    write_csv(figures / 'primary_result.csv', primary)
    figure, axes = plt.subplots(2, 3, figsize=(12, 7))
    for axis, regime in zip(axes.ravel(), REGIMES):
        for profile, style in [('legacy', ':'), ('baseline', '--'), ('production', '-')]:
            selected = [row for row in primary if row['experiment'] == regime + '_dev_' + profile]
            axis.plot([float(row['time']) for row in selected], [float(row['current']) for row in selected],
                      style, label=profile)
        axis.set(title=regime, xlabel='time', ylabel='inward hopping current')
    axis = axes.ravel()[-1]
    selected = [row for row in primary if row['experiment'] == 'paired_dev_production']
    for observable in ['current', 'source']:
        axis.plot([float(row['time']) for row in selected], [float(row[observable]) for row in selected], label=observable)
    axis.set(title='paired: distinct transport and source', xlabel='time', ylabel='regional electron rate')
    axis.legend()
    axes[0, 0].legend()
    figure.tight_layout()
    figure.savefig(figures / 'primary_result.png', dpi=160)
    plt.close(figure)
    source = []
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for regime in REGIMES:
        selected = [row for row in comparisons if row['case'] == regime + '_dev'
                    and row['right_run'] == regime + '_dev_production'
                    and any(row['left_run'] == regime + '_dev_' + profile
                            for profile in ['baseline', 'smallstep16', 'bond48', 'final_tensor'])]
        for row in selected:
            axes[0].scatter(row['left_seconds'], max(row['observable_rms_difference'], 1e-14))
            axes[0].annotate(row['left_run'].replace('_dev_', ':'),
                             (row['left_seconds'], max(row['observable_rms_difference'], 1e-14)), fontsize=6)
            source.append(dict(panel='accuracy_cost', **row))
    axes[0].set(xscale='log', yscale='log', xlabel='solver seconds', ylabel='RMS observable error versus sparse',
                title='Development accuracy, not just conservation')
    for profile, marker in [('production', 'o'), ('baseline', 'x'), ('refined', '^')]:
        selected = [row for row in scaling if '_scale_' in row['case'] and row['row_id'] == row['case'] + '_' + profile]
        axes[1].scatter([row['n_sites'] for row in selected], [row['seconds'] for row in selected], label=profile, marker=marker)
        source.extend(dict(panel='size_scaling', **row) for row in selected)
    axes[1].axhline(180, color='gray', linestyle=':', label='held-out safety timeout')
    axes[1].set(yscale='log', xlabel='electronic sites', ylabel='solver seconds', title='Finite-resource size study')
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(figures / 'robustness_or_scaling.png', dpi=160)
    plt.close(figure)
    write_csv(figures / 'robustness_or_scaling.csv', source)


if __name__ == '__main__':
    tables = collect()
    plots(*tables)
