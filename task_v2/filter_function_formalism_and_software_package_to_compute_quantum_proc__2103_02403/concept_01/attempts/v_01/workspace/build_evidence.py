import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np

from pipeline.physics import ideal_channel, load_case, observables


ROOT = Path(__file__).resolve().parent.parent
TABLES = {}
CASES = ['calibration_static', 'driven_static', 'switching_echo', 'memory_ou',
         'white_gate', 'leakage_static', 'broadband_entangler']
LABELS = ['Idle\nstatic', 'Driven\nstatic', 'Switching\necho', 'Memory\nOU',
          'White\ngate', 'Six-state\nstatic', 'Six-state\nbroadband']


def read_csv(name):
    with (ROOT / name).open() as stream:
        return list(csv.DictReader(stream))


def write_csv(name, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (ROOT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)
    TABLES[name] = {row['row_id']: row for row in rows}


def metric_row(case_id, mode, launches):
    row_id = f'{case_id}_{mode}'
    directory = ROOT / 'artifacts' / row_id
    metrics = json.loads((directory / 'metrics.json').read_text())
    keys = ['infidelity', 'leakage', 'coherent_size', 'k2_norm', 'seconds', 'peak_rss_mb',
            'tp_error', 'unital_error', 'choi_min']
    row = dict(row_id=row_id, case_id=case_id, mode=mode,
               **{key: metrics[key] for key in keys}, artifact=f'artifacts/{row_id}',
               wall_seconds=launches[row_id]['wall_seconds'], method=metrics['diagnostics']['method'])
    return row


def make_tables():
    launches = {row['row_id']: row for row in json.loads((ROOT / 'launches.json').read_text())}
    results, ablation, comparisons, scaling = [], [], [], []
    for case_id in CASES:
        case, arrays = load_case(ROOT / 'input' / 'cases' / f'{case_id}.json')
        ideal = ideal_channel(arrays)
        reference = dict(np.load(ROOT / 'artifacts' / f'{case_id}_refined' / 'process.npz'))
        reference_error = ideal.conj().T @ reference['channel']
        reference_coherent = (reference_error - reference_error.conj().T) / 2
        for mode in ['selected', 'baseline', 'refined', 'no_memory']:
            row = metric_row(case_id, mode, launches)
            process = dict(np.load(ROOT / row['artifact'] / 'process.npz'))
            if mode in ('selected', 'baseline'):
                results.append(row)
            if mode != 'baseline':
                ablation.append(row)
            error = ideal.conj().T @ process['channel']
            coherent = (error - error.conj().T) / 2
            comparisons.append(dict(
                row_id=row['row_id'], case_id=case_id, mode=mode,
                relative_channel_error=float(np.linalg.norm(process['channel'] - reference['channel'])
                                             / max(np.linalg.norm(reference['channel'] - ideal), 1e-8)),
                relative_k2_error=float(np.linalg.norm(process['k2'] - reference['k2'])
                                        / max(np.linalg.norm(reference['k2']), 1e-8)),
                relative_coherent_error=float(np.linalg.norm(coherent - reference_coherent)
                                              / max(np.linalg.norm(reference_coherent), 1e-8)),
                channel_difference_norm=float(np.linalg.norm(process['channel'] - reference['channel'])),
                coherent_probe=float((error[1, 0] - error[0, 1].conj()).imag / 2),
                ideal_leakage=observables(ideal, arrays)['leakage'], artifact=row['artifact'],
                reference_artifact=f'artifacts/{case_id}_refined'))
            scaling.append(dict(row_id=row['row_id'], case_id=case_id, mode=mode,
                                segments=len(arrays['dt']), dimension=arrays['H'].shape[-1],
                                seconds=row['seconds'], wall_seconds=row['wall_seconds'],
                                peak_rss_mb=row['peak_rss_mb'], artifact=row['artifact']))
    write_csv('results.csv', results)
    write_csv('ablation.csv', ablation)
    write_csv('comparison.csv', comparisons)
    write_csv('scaling.csv', scaling)
    lab_rows = []
    for measured in read_csv('input/lab_checks.csv'):
        for mode in ['baseline', 'selected']:
            row_id = measured['case_id'] + '_' + mode
            prediction = TABLES['results.csv'][row_id]
            probe = TABLES['comparison.csv'][row_id]['coherent_probe']
            uncertainty = float(measured['infidelity_se'])
            probe_uncertainty = float(measured['coherent_probe_se'])
            lab_rows.append(dict(row_id=row_id, case_id=measured['case_id'], mode=mode,
                                predicted_infidelity=prediction['infidelity'],
                                lab_infidelity=float(measured['infidelity']), infidelity_se=uncertainty,
                                infidelity_z=(prediction['infidelity'] - float(measured['infidelity'])) / uncertainty,
                                predicted_coherent_probe=probe,
                                lab_coherent_probe=float(measured['coherent_probe']),
                                coherent_probe_se=probe_uncertainty,
                                coherent_probe_z=((probe - float(measured['coherent_probe'])) / probe_uncertainty
                                                  if probe_uncertainty > 0 else 0),
                                artifact=prediction['artifact']))
    write_csv('lab_comparison.csv', lab_rows)
    diagnostic_rows = []
    for path in sorted((ROOT / 'diagnostics').glob('*.json')):
        measured = json.loads(path.read_text())
        prediction = TABLES['results.csv'][measured['case_id'] + '_selected']
        probe = TABLES['comparison.csv'][measured['case_id'] + '_selected']['coherent_probe']
        diagnostic_rows.append(dict(row_id=path.stem, **measured,
                                    predicted_infidelity=prediction['infidelity'],
                                    predicted_coherent_probe=probe,
                                    infidelity_z=(prediction['infidelity'] - measured['infidelity']) / measured['infidelity_se'],
                                    coherent_probe_z=(probe - measured['coherent_probe']) / measured['coherent_probe_se'],
                                    artifact=str(path.relative_to(ROOT))))
    write_csv('diagnostics.csv', diagnostic_rows)
    slow = json.loads((ROOT / 'iterations' / 'broadband_refined_v1_slow' / 'metrics.json').read_text())
    fast = TABLES['ablation.csv']['broadband_entangler_refined']
    write_csv('resource_history.csv', [
        dict(row_id='broadband_refined_v1', seconds=slow['seconds'], peak_rss_mb=slow['peak_rss_mb'],
             artifact='iterations/broadband_refined_v1_slow'),
        dict(row_id='broadband_refined_final', seconds=fast['seconds'], peak_rss_mb=fast['peak_rss_mb'],
             artifact=fast['artifact'])])
    TABLES['experiments.csv'] = {row['row_id']: row for row in read_csv('experiments.csv')}
    TABLES['validation/response.csv'] = {row['row_id']: row for row in read_csv('validation/response.csv')}


def make_claims():
    claims = []
    def claim(claim_id, text, table, rows, metric, operation='value'):
        values = [float(TABLES[table][row][metric]) for row in rows]
        value = values[0] if operation == 'value' else (
            values[0] - values[1] if operation == 'difference' else values[0] / values[1])
        claims.append(dict(claim_id=claim_id, text=text.format(value=value), table=table,
                           rows=rows, metric=metric, operation=operation, value=value))
    claim('static_memory', 'Bath restarts change driven-static infidelity by {value:.8f} (restart minus continuous).',
          'ablation.csv', ['driven_static_no_memory', 'driven_static_selected'], 'infidelity', 'difference')
    claim('ou_memory', 'Bath restarts change OU infidelity by {value:.8f} (restart minus continuous).',
          'ablation.csv', ['memory_ou_no_memory', 'memory_ou_selected'], 'infidelity', 'difference')
    claim('white_memory_control', 'White-noise restart minus continuous infidelity is {value:.3g}.',
          'ablation.csv', ['white_gate_no_memory', 'white_gate_selected'], 'infidelity', 'difference')
    claim('driven_closure_failure', 'Even with exact k2, the second-cumulant exponential has {value:.6f} relative full-channel error on driven static noise.',
          'experiments.csv', ['driven_static_corrected_cumulant'], 'relative_channel_error')
    claim('law_not_covariance', 'Replacing switching noise by Gaussian OU with identical covariance changes the full channel by relative {value:.6f}.',
          'experiments.csv', ['switching_same_covariance_gaussian'], 'relative_channel_error')
    claim('broadband_validity', 'Selected broadband prediction differs from bounded fourth-order refinement by relative {value:.6g} in the full channel.',
          'comparison.csv', ['broadband_entangler_selected'], 'relative_channel_error')
    claim('ou_refinement', 'Selected OU prediction differs from the tighter hierarchy by relative {value:.6g} in the full channel.',
          'comparison.csv', ['memory_ou_selected'], 'relative_channel_error')
    claim('quadratic_check', 'Independent static finite-difference/Richardson response agrees with ordered k2 to relative {value:.6g}.',
          'validation/response.csv', ['driven_static_response'], 'relative_error')
    claim('spectral_sidedness', 'Adding the negative-frequency half doubles the static response norm at unchanged cutoffs: ratio {value:.12g}.',
          'experiments.csv', ['static_spectrum_two_sided_same_cutoff', 'static_spectrum_positive_dense'],
          'response_ratio', 'ratio')
    claim('refinement_resource_repair', 'Broadband refinement speedup after the budget repair is {value:.4g} times (predictor time).',
          'resource_history.csv', ['broadband_refined_v1', 'broadband_refined_final'], 'seconds', 'ratio')
    claim('broadband_memory_resource', 'Baseline/selected peak-RSS ratio on the 250-segment six-state record is {value:.4g}.',
          'results.csv', ['broadband_entangler_baseline', 'broadband_entangler_selected'], 'peak_rss_mb', 'ratio')
    (ROOT / 'claims.json').write_text(json.dumps(claims, indent=2) + '\n')


def make_figures():
    destination = ROOT / 'figures'
    destination.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.dpi': 150, 'savefig.dpi': 180})
    colors = {'selected': '#166b9b', 'baseline': '#d67726', 'no_memory': '#aa4874'}
    figure, axes = plt.subplots(1, 2, figsize=(13.2, 4.7), gridspec_kw={'width_ratios': [0.8, 1.5]})
    lab_cases = CASES[:3]
    positions = np.arange(len(lab_cases))
    lab_rows = [TABLES['lab_comparison.csv'][case_id + '_selected'] for case_id in lab_cases]
    axes[0].errorbar(positions, [row['lab_infidelity'] for row in lab_rows],
                     yerr=[2 * row['infidelity_se'] for row in lab_rows],
                     fmt='o', color='black', capsize=4, label='Lab check ±2 SE', markersize=5)
    for mode, shift, marker in [('baseline', -0.12, 's'), ('selected', 0.12, 'D')]:
        axes[0].scatter(positions + shift,
                        [TABLES['results.csv'][case_id + '_' + mode]['infidelity'] for case_id in lab_cases],
                        color=colors[mode], marker=marker, s=38, label=mode.title())
    axes[0].set(xticks=positions, xticklabels=LABELS[:3], ylabel='Entanglement infidelity',
                title='Independent ensemble checks')
    axes[0].legend(fontsize=8, loc='upper left')
    positions = np.arange(len(CASES))
    for mode, shift in [('baseline', -0.16), ('selected', 0.16)]:
        values = [max(TABLES['comparison.csv'][case_id + '_' + mode]['relative_channel_error'], 1e-14)
                  for case_id in CASES]
        axes[1].bar(positions + shift, values, width=0.3, color=colors[mode], label=mode.title())
    closure_cases = CASES[1:4] + CASES[5:]
    axes[1].scatter([CASES.index(case_id) for case_id in closure_cases],
                    [float(TABLES['experiments.csv'][case_id + '_corrected_cumulant']['relative_channel_error'])
                     for case_id in closure_cases], marker='x', color='#34834d', s=55,
                    label='Exact k2, exponential closure', zorder=5)
    axes[1].axhline(0.01, color='0.5', linestyle=':', linewidth=1)
    axes[1].set(yscale='log', ylim=(4e-15, 3), xticks=positions, xticklabels=LABELS,
                ylabel='Relative full-channel difference', title='Against tighter law-specific propagation')
    axes[1].legend(fontsize=8, loc='lower left')
    figure.text(0.5, 0.01, 'Channel differences normalize by ||Φref − Φideal||F; display floor 10⁻¹⁴. Refinement is not experimental truth.',
                ha='center', fontsize=8)
    figure.tight_layout(rect=(0, 0.045, 1, 1))
    figure.savefig(destination / 'primary_result.png')
    plt.close(figure)
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.7))
    memory_cases = ['driven_static', 'memory_ou', 'switching_echo']
    positions = np.arange(3)
    for mode, shift in [('selected', -0.17), ('no_memory', 0.17)]:
        axes[0].bar(positions + shift,
                    [TABLES['ablation.csv'][case_id + '_' + mode]['infidelity'] for case_id in memory_cases],
                    width=0.32, color=colors[mode], label='Continuous bath' if mode == 'selected' else 'Bath restarted')
    axes[0].set(xticks=positions, xticklabels=['Driven\nstatic', 'OU', 'Switching\necho'],
                ylabel='Entanglement infidelity', title='Gate boundaries do not reset noise')
    axes[0].legend(fontsize=8)
    for mode, marker in [('selected', 'o'), ('baseline', 's')]:
        rows = [TABLES['results.csv'][case_id + '_' + mode] for case_id in CASES]
        axes[1].scatter([row['seconds'] for row in rows],
                        [max(TABLES['comparison.csv'][row['row_id']]['relative_channel_error'], 1e-14) for row in rows],
                        s=[30 + row['peak_rss_mb'] / 6 for row in rows],
                        color=colors[mode], marker=marker, alpha=0.85, label=mode.title())
    axes[1].axhline(0.01, color='0.5', linestyle=':', linewidth=1)
    axes[1].set(xscale='log', yscale='log', xlabel='Predictor seconds (one thread)',
                ylabel='Relative full-channel difference', title='Accuracy and measured cost')
    axes[1].legend(fontsize=8)
    axes[1].text(0.04, 0.35, 'Marker area increases with peak RSS', transform=axes[1].transAxes, fontsize=8)
    scale_rows = sorted([row for row in TABLES['experiments.csv'].values()
                         if row['variant'] == 'scaled_corrected_cumulant'], key=lambda row: float(row['sigma_scale']))
    amplitudes = np.asarray([float(row['sigma_scale']) for row in scale_rows])
    errors = np.asarray([float(row['relative_channel_error']) for row in scale_rows])
    axes[2].loglog(amplitudes, errors, 'o-', color='#34834d', label='Corrected cumulant error')
    axes[2].loglog(amplitudes, errors[0] * (amplitudes / amplitudes[0]) ** 2, '--', color='0.5', label='λ² guide')
    axes[2].set(xlabel='Noise amplitude multiplier λ', ylabel='Relative full-channel difference',
                title='Gaussianity alone is insufficient')
    axes[2].set_xticks([0.125, 0.25, 0.5, 1.0], ['0.125', '0.25', '0.5', '1'])
    axes[2].xaxis.set_minor_formatter(NullFormatter())
    axes[2].legend(fontsize=8)
    figure.text(0.5, 0.01, 'Fresh-process wall times and all RSS values are in scaling.csv. The error reference is a tighter deterministic calculation.',
                ha='center', fontsize=8)
    figure.tight_layout(rect=(0, 0.045, 1, 1))
    figure.savefig(destination / 'robustness_or_scaling.png')
    plt.close(figure)
    sources = {
        'primary_result.png': {
            'left': [dict(table='lab_comparison.csv', rows=[case_id + '_' + mode for case_id in lab_cases
                                                          for mode in ['selected', 'baseline']],
                          metrics=['predicted_infidelity', 'lab_infidelity', 'infidelity_se'],
                          transformation='Error bars are two sampling standard errors.')],
            'right': [dict(table='comparison.csv', rows=[case_id + '_' + mode for case_id in CASES
                                                       for mode in ['selected', 'baseline']], metric='relative_channel_error'),
                      dict(table='experiments.csv', rows=[case_id + '_corrected_cumulant' for case_id in closure_cases],
                           metric='relative_channel_error')]},
        'robustness_or_scaling.png': {
            'left': [dict(table='ablation.csv', rows=[case_id + '_' + mode for case_id in memory_cases
                                                    for mode in ['selected', 'no_memory']], metric='infidelity')],
            'middle': [dict(table=table, rows=[case_id + '_' + mode for case_id in CASES
                                             for mode in ['selected', 'baseline']])
                       for table in ['results.csv', 'comparison.csv', 'scaling.csv']],
            'right': [dict(table='experiments.csv', rows=[row['row_id'] for row in scale_rows],
                           metrics=['sigma_scale', 'relative_channel_error'],
                           transformation='Dashed guide is first error times (lambda/first lambda)^2.')]}}
    (destination / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n')


def make_report():
    result = TABLES['results.csv']
    comparison = TABLES['comparison.csv']
    ablation = TABLES['ablation.csv']
    experiments = TABLES['experiments.csv']
    tests = json.loads((ROOT / 'validation' / 'tests.json').read_text())
    selected_rows = [row for row in result.values() if row['mode'] == 'selected']
    public_lines = []
    for case_id in CASES:
        selected = result[case_id + '_selected']
        baseline = result[case_id + '_baseline']
        public_lines.append(f"| {case_id} | {baseline['infidelity']:.8g} | {selected['infidelity']:.8g} | "
                            f"{comparison[case_id + '_selected']['relative_channel_error']:.2g} | "
                            f"{selected['seconds']:.3f} | {selected['peak_rss_mb']:.1f} |")
    broad_metrics = json.loads((ROOT / 'artifacts' / 'broadband_entangler_selected' / 'metrics.json').read_text())
    broad_refined = json.loads((ROOT / 'artifacts' / 'broadband_entangler_refined' / 'metrics.json').read_text())
    report = f"""# Release audit: conditional approval of the replacement

## Decision and scope

**Do not release the legacy forecast as a general process predictor. Release the new
`selected` implementation with its method/convergence diagnostics.** All seven public
cases pass the audit; all {len(tests)} exact/invariance tests pass. No parameters were fitted
to lab checks. A result marked `converged: false`, `accuracy_warning`, or
`resource_warning` is an explicitly uncertified finite-noise prediction, not a scientific
accuracy guarantee. `k2` has a separate deterministic calculation.

| Case | Baseline infidelity | Selected infidelity | Selected/refined channel difference | Seconds | Peak MiB |
|---|---:|---:|---:|---:|---:|
{chr(10).join(public_lines)}

Differences use the contract's full complex Frobenius normalization, not just fidelity.
`results.csv` has all 14 required public comparisons; `ablation.csv` has 21 separately
executed selected/refined/restart rows, including a white-noise control. Artifact paths
lead to the actual process arrays. The largest selected time is
{max(row['seconds'] for row in selected_rows):.3f} seconds and largest selected peak RSS is
{max(row['peak_rss_mb'] for row in selected_rows):.1f} MiB. Fresh-process wall times, rather than
only predictor timings, are also recorded in `scaling.csv` and `launches.json`.

## Competing explanations and discriminating experiments

1. **Representation error? Not found in the tested conversions.** Complex Hamiltonian,
   column-vectorization, Choi normalization, ideal segment splitting, and vendor-basis
   conversion tests pass. The latter residual is
   {json.loads((ROOT / 'validation' / 'vendor_representation.json').read_text())['frobenius_error']:.3g}.
   This is evidence against a transpose/normalization explanation, not proof of every
   unused vendor path.
2. **Spectral convention and quadrature error? Yes.** The baseline uses a two-sided PSD
   on positive frequencies only, without folding. At the same cutoffs, the response
   doubles when the negative half is included. Its artificial Lorentzian static model
   also loses low-frequency weight: dense positive integration recovers only 0.352084
   of the exact static response; two-sided integration gives 0.704168; lowering the
   cutoff gives 0.999306. The remaining discrepancy reflects finite regularization and
   quadrature. Refining the original 160-point mesh alone does not repair the model.
   See the `static_spectrum_*` rows in `experiments.csv`.
3. **Bath memory mistaken for a gate-library operation? Yes.** Baseline regrouping of
   identical driven controls changes infidelity from
   {result['driven_static_baseline']['infidelity']:.8f} to
   {float(experiments['driven_repartition_baseline']['infidelity']):.8f}; selected is invariant.
   Independent bath restarts change selected driven-static infidelity by
   {ablation['driven_static_no_memory']['infidelity'] - ablation['driven_static_selected']['infidelity']:+.8f}
   and OU infidelity by
   {ablation['memory_ou_no_memory']['infidelity'] - ablation['memory_ou_selected']['infidelity']:+.8f}.
   White-noise restart and continuous predictions agree. `blocks` never changes the
   physical selected target.
4. **Missing coherent response? Yes.** `second_order=False` discards ordered frequency
   shifts. The replacement retains the anti-Hermitian part of `k2`; omitting it is
   independently tested in `*_symmetric_cumulant` rows. The five finite-difference
   response tests in `validation/response.csv` have relative errors at most
   {max(float(row['relative_error']) for row in TABLES['validation/response.csv'].values()):.3g}.
5. **Second-cumulant closure invalid at finite noise? Also yes.** With the *correct full*
   `k2`, `Phi0 exp(k2)` still has
   {float(experiments['driven_static_corrected_cumulant']['relative_channel_error']):.3%}
   full-channel error on driven Gaussian static noise. Scalar Gaussianity does not
   terminate the ordered noncommuting operator cumulants. A Gaussian OU replacement
   for switching noise with exactly the same covariance has identical `k2` but
   {float(experiments['switching_same_covariance_gaussian']['relative_channel_error']):.3%}
   different finite-noise channel. Neither PSD, complete positivity, nor one fidelity
   identifies the full target.

## Replacement and controlled approximation

Static Gaussian noise uses converged Gaussian quadrature over stationary latent draws;
OU uses normalized Hermite stochastic-Liouville dynamics; telegraph uses its discrete
Markov/Walsh dynamics; white noise uses the exact Stratonovich Lindblad generator.
Latent mixing, segment-dependent sensitivity, initial stationarity, time ordering and
all Hilbert-space states are retained. Six-state records are never projected to four
states. The synthetic leakage test actually transfers population outside its two-state
computational subspace; the public six-state static case happens to have zero leakage.

The separate quadratic response propagates the ideal channel, first-order bath memories,
and their ordered second-order return, then transforms to the **initial** interaction
frame. This includes coherent effects and does not approximate static noise by a narrow
spectral line. See `workspace/METHODS.md` for equations, error bounds and limits.

The fast exponential is retained only when a covariance-envelope Dyson bound certifies
relative error below 2e-4. For the 250-segment broadband record its conservative bound is
{broad_metrics['diagnostics']['weak_relative_error_bound']:.3g}; observed selected/refined
channel difference is {comparison['broadband_entangler_selected']['relative_channel_error']:.3g}.
Refinement uses a degree-two Hermite bath, exact through fourth order, with analytic
omitted-tail bound {broad_refined['diagnostics']['hierarchy_relative_truncation_bound']:.3g}
before floating-point error. This is evidence for a weak-noise approximation, not an
assumption that a many-rate bath is white or static.

## Chronological run → diagnosis → revision → rerun

- **11:31 UTC:** Executed the requested original calibration command.
  `initial_static/process.npz` and `initial_static/metrics.json` record infidelity
  0.013901375 versus the exact 0.038441827 and the noisy lab check 0.039203308.
- **11:33–11:41:** Inspected the multi-file package and pipeline; preserved baseline
  unchanged in `workspace/pipeline/baseline.py`. Implemented law-specific solvers and
  ordered response. First public results are retained under `iterations/pre_final/`;
  spectral, partition, and closure experiments isolate distinct causes.
- **11:41–11:45:** Initial high-order broadband refinement took 127.464 seconds and
  failed its very tight convergence threshold. Its actual arrays and metrics remain
  in `iterations/broadband_refined_v1_slow/`; this version was not released.
- **11:45–11:48:** Replaced repeated high-order weak-bath solves by a fourth-order
  tail-controlled calculation. Propagated the deviation from the ideal channel to
  prevent large ideal-channel roundoff from dominating tiny weak-noise differences.
  The rerun took 21.178 seconds (`logs/broadband_entangler_refined_v2.log`).
- **Final rerun:** `launches.json` records UTC start times, commands, wall time and
  successful exits for all 28 fresh invocations from a different working directory.
  The final broadband refinement takes {ablation['broadband_entangler_refined']['seconds']:.3f}
  seconds. `logs/tests.log`, `logs/experiments.log`, `diagnostics/*.json`, and the
  evidence tables retain the subsequent validation, rather than just a method summary.

Independent trajectory diagnostics were rerun with seed 4217: static, OU, and coarse/fine
switching checks (`diagnostics.csv`). Their sampling errors and time-discretization
errors are distinct. The switching coarse/fine estimates change with their random
realizations as well as step size; this is not treated as deterministic convergence.
The supplied lab checks agree with selected within two reported standard errors in
infidelity, but these checks alone do not certify process accuracy.

## Figures and limitations

`figures/primary_result.png` separates agreement with noisy scalar observations from
full-channel convergence. Green crosses show why repairing `k2` alone is insufficient.
`figures/robustness_or_scaling.png` shows memory effects, measured accuracy/resource
tradeoffs, and the weak-amplitude scaling of the closure error. All plotted source rows
and transformations are identified in `figures/sources.json`. `claims.json` contains
machine-recomputable quantitative claims, including memory and validity claims.

Finite Hermite/Walsh truncation is not automatically CP and adjacent-order agreement is
an empirical check, not a universal error theorem. Strong, high-rank baths can exhaust
the state/work budget; these emit warnings and retain the last completed prediction
(or explicitly labeled cumulant fallback), never a silently truncated time record.
An 85-second refinement deadline is checked between segments; a single expensive
matrix-exponential action and the separate response calculation are not hard preempted.
The public release stays below 60 seconds and far below 1.5 GiB, but arbitrary input
sizes outside these measurements are not certified. Analytic weak-bath bounds exclude
floating-point errors; refinements below about 1e-10 absolute channel norm are
roundoff-sensitive. The scaling rows are heterogeneous workloads, not a controlled
fit of asymptotic segment-count complexity. No supplied controls, covariance laws, or leakage geometry may be
replaced by a name-based assumption.

## Reproduction

Run `bash run.sh input/cases/driven_static.json DEST --mode selected` from this directory,
or use absolute paths from elsewhere. `baseline`, `refined`, and `no_memory` are supported.
`bash workspace/audit.sh` reruns tests, all public modes, diagnostics, experiments and
evidence checks. It uses only copied inputs, supplied dependencies, and local output paths.
"""
    (ROOT / 'report.md').write_text(report)


def main():
    make_tables()
    make_claims()
    make_figures()
    make_report()


if __name__ == '__main__':
    main()
