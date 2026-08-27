import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from zipfile import BadZipFile

OUTPUT = Path(__file__).resolve().parent / 'output'
INPUT = OUTPUT.parent.parent / 'participant/v_01/input/cases'
sys.path.insert(0, str(OUTPUT / 'workspace/deps'))
os.environ.setdefault('MPLCONFIGDIR', '/tmp/quantum_process_matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

FIELDS = 'row_id case_id mode infidelity leakage coherent_size k2_norm seconds peak_rss_mb artifact'.split()
ABLATIONS = ('driven_static', 'memory_ou')


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def write_table(name, rows):
    with (OUTPUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_result(destination, case_id, mode, dimension):
    metrics = json.loads((destination / 'metrics.json').read_text())
    with np.load(destination / 'process.npz', allow_pickle=False) as process:
        matrices = [process[key] for key in ('channel', 'k2')]
    valid = metrics['case_id'] == case_id and metrics['mode'] == mode
    valid &= all(matrix.shape == (dimension ** 2, dimension ** 2) and np.isfinite(matrix).all() for matrix in matrices)
    valid &= all(np.isfinite(metrics[key]) for key in FIELDS[3:-1] + ['tp_error', 'unital_error', 'choi_min'])
    valid &= metrics['seconds'] >= 0 and metrics['peak_rss_mb'] > 0 and isinstance(metrics['diagnostics'], dict)
    valid &= np.isclose(np.linalg.norm(matrices[1]), metrics['k2_norm'], rtol=1e-8, atol=1e-12)
    if not valid:
        raise ValueError(f'Invalid experiment artifacts: {destination}')
    return {'row_id': f'{case_id}_{mode}', **{key: metrics[key] for key in FIELDS[1:-1]}, 'artifact': destination.relative_to(OUTPUT).as_posix()}


def experiment(path, case_id, mode, dimension, fingerprint, resume):
    destination = OUTPUT / 'experiments' / f'{case_id}_{mode}'
    provenance = destination / 'run.json'
    fingerprint = f'{fingerprint}:{mode}'
    if resume:
        try:
            if json.loads(provenance.read_text())['fingerprint'] == fingerprint:
                return read_result(destination, case_id, mode, dimension)
        except (OSError, ValueError, KeyError, TypeError, EOFError, BadZipFile):
            pass
    destination.mkdir(parents=True, exist_ok=True)
    provenance.unlink(missing_ok=True)
    command = ['bash', str(OUTPUT / 'run.sh'), str(path), str(destination), '--mode', mode]
    started = datetime.now(timezone.utc).isoformat()
    print(f'Running {case_id} {mode}', flush=True)
    with (destination / 'run.log').open('w') as stream:
        subprocess.run(command, cwd=OUTPUT, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=240)
    row = read_result(destination, case_id, mode, dimension)
    write_json(provenance, dict(fingerprint=fingerprint, command=command, started_utc=started, finished_utc=datetime.now(timezone.utc).isoformat()))
    return row


def main():
    parser = argparse.ArgumentParser(description='Produce evidence from the assembled output/run.sh.')
    parser.add_argument('--resume', action='store_true', help='Reuse complete, validated runs with matching input/source fingerprints.')
    arguments = parser.parse_args()
    sources = [OUTPUT / 'run.sh', OUTPUT / 'workspace/run.sh', *sorted((OUTPUT / 'workspace/pipeline').glob('*.py')), *sorted((OUTPUT / 'workspace/vendor/filter_functions').glob('*.py'))]
    source_hash = hashlib.sha256(b''.join(path.read_bytes() for path in sources)).digest()
    cases, sizes, fingerprints = {}, {}, {}
    for path in sorted(INPUT.glob('*.json')):
        case = json.loads(path.read_text())
        case_id, asset = case['case_id'], path.parent / case['asset']
        cases[case_id] = path
        with np.load(asset, allow_pickle=False) as arrays:
            sizes[case_id] = dict(segments=len(arrays['dt']), dimension=arrays['H'].shape[-1])
        fingerprints[case_id] = hashlib.sha256(source_hash + path.read_bytes() + asset.read_bytes()).hexdigest()
    if not cases or not set(ABLATIONS).issubset(cases):
        raise ValueError('Public cases, including both required ablations, must be present.')
    def run(case_id, mode):
        return experiment(cases[case_id], case_id, mode, sizes[case_id]['dimension'], fingerprints[case_id], arguments.resume)
    results = [run(case_id, mode) for mode in ('baseline', 'selected') for case_id in cases]
    selected = {row['case_id']: row for row in results if row['mode'] == 'selected'}
    ablation, claims, comparisons, histories = [], [], [], []
    for case_id in ABLATIONS:
        rows = [dict(selected[case_id]), run(case_id, 'refined'), run(case_id, 'no_memory')]
        with np.load(OUTPUT / rows[0]['artifact'] / 'process.npz', allow_pickle=False) as process:
            reference = {key: process[key] for key in ('channel', 'k2')}
        for row in rows:
            with np.load(OUTPUT / row['artifact'] / 'process.npz', allow_pickle=False) as process:
                row.update({f'{key}_delta_selected': float(np.linalg.norm(process[key] - reference[key])) for key in reference})
            if row['mode'] != 'no_memory':
                diagnostics = json.loads((OUTPUT / row['artifact'] / 'metrics.json').read_text())['diagnostics']
                histories.append(f"- `{row['artifact']}/metrics.json`: " + json.dumps({key: diagnostics[key] for key in ('method', 'tolerance', 'converged', 'order', 'error_estimate', 'history') if key in diagnostics}))
        for label, row in zip(('refinement', 'memory'), rows[1:]):
            difference = rows[0]['infidelity'] - row['infidelity']
            claims.append(dict(claim_id=f'{case_id}_{label}', text=f"{case_id}: selected minus {row['mode']} infidelity ({label} comparison, not an absolute error bound).", table='ablation.csv', rows=[rows[0]['row_id'], row['row_id']], metric='infidelity', operation='difference', value=difference))
            comparisons.append(f"- {case_id} {label}: selected minus {row['mode']} infidelity = {difference:.9g}; channel Frobenius change = {row['channel_delta_selected']:.9g}; k2 Frobenius change = {row['k2_delta_selected']:.9g} (`ablation.csv`, `{row['row_id']}`).")
        ablation.extend(rows)
    scaling = [{**row, **sizes[row['case_id']]} for row in selected.values()]
    for name, rows in (('results.csv', results), ('ablation.csv', ablation), ('scaling.csv', scaling)):
        write_table(name, rows)
    write_json(OUTPUT / 'claims.json', claims)
    figures = OUTPUT / 'figures'
    figures.mkdir(exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    for axis, metric in zip(axes, ('infidelity', 'coherent_size')):
        for mode in ('baseline', 'selected'):
            series = [row for row in results if row['mode'] == mode]
            axis.plot(range(len(series)), [row[metric] for row in series], 'o-', label=mode)
        axis.set_xticks(range(len(cases)), list(cases), rotation=70)
        axis.set_ylabel(metric)
        axis.legend()
    figure.tight_layout()
    figure.savefig(figures / 'primary_result.png')
    plt.close(figure)
    figure, axis = plt.subplots(figsize=(10, 5))
    for mode in ('selected', 'refined', 'no_memory'):
        series = [row for row in ablation if row['mode'] == mode]
        axis.scatter([row['seconds'] for row in series], [row['channel_delta_selected'] for row in series], label=mode)
        for row in series:
            axis.annotate(row['case_id'], (row['seconds'], row['channel_delta_selected']))
    axis.set(xlabel='Predictor seconds', ylabel='Channel Frobenius distance from selected')
    axis.set_yscale('symlog', linthresh=1e-10)
    axis.legend()
    figure.tight_layout()
    figure.savefig(figures / 'robustness_or_scaling.png')
    plt.close(figure)
    write_json(figures / 'sources.json', {filename: dict(table=table, rows=[row['row_id'] for row in rows]) for filename, table, rows in [('primary_result.png', 'results.csv', results), ('robustness_or_scaling.png', 'ablation.csv', ablation)]})
    diagnostic_paths = sorted(set((OUTPUT / 'diagnostics').rglob('*.json')) | set(OUTPUT.glob('*diagnos*.json')) | set(OUTPUT.glob('*validat*.json')) | set(OUTPUT.glob('*histor*.json')))
    logged = '\n'.join(f'- `{path.relative_to(OUTPUT)}`: {json.dumps(json.loads(path.read_text()))}' for path in diagnostic_paths)
    slowest, largest = max(scaling, key=lambda row: row['seconds']), max(scaling, key=lambda row: row['peak_rss_mb'])
    report = f"""# Release evidence
Conditional research release, not a blanket accuracy guarantee. Baseline/selected disagreement alone does not establish which channel is accurate. Retain the weak broadband approximation only where independent higher-hierarchy residuals justify it; missing validation or exhausted convergence limits remain release blockers for that regime.

## Run → diagnose → revise → rerun (audit replay)
The solver revisions were assembled before this automation; this is a reproducible replay, not a claim that the script performed those edits. First, run/reuse every preserved baseline, anchored by `experiments/calibration_static_baseline/process.npz`, its `metrics.json`, and all baseline rows of `results.csv`. Diagnose competing numerical, memory, and physical-approximation hypotheses against `workspace/pipeline/legacy.py` and `workspace/pipeline/physics.py`: the baseline uses a finite one-sided frequency quadrature, a Lorentzian static regularization, independent-bath gate composition, and omits coherent quadratic terms (`second_order=False`). A frequency-grid change cannot restore discarded interblock correlations or missing ordered coherent response.

The revision checkpoint is `workspace/pipeline/quadratic.py`, `workspace/pipeline/reference_dynamics.py`, and `workspace/pipeline/predictor.py`; source snapshot SHA256 is `{source_hash.hex()}`. Rerun/reuse all selected cases, followed by separate refined and no_memory invocations for driven_static and memory_ou. Each experiment retains `process.npz`, `metrics.json`, `run.log`, and UTC execution provenance in `run.json`. Resume skips only matching, structurally valid recorded runs; reused artifacts retain their original dates. The numerical refinement histories below record actual successive solves, not invented development timestamps.

## Physics and controlled comparisons
Auxiliary moment propagation computes the initial-interaction-frame quadratic response including ordered coherent terms. Static channels integrate the full stationary Gaussian distribution by adaptive Gaussian quadrature with recorded convergence checks, not a regularized static spectrum. OU channels use a truncated Hermite hierarchy with successive-order checks. RTN uses the exact finite-state representation of the specified switching law, with numerical propagation error still possible; its covariance decays at twice the switching rate. White noise uses the Stratonovich Liouvillian with one-half the squared noise Liouvillian. Full Hilbert dimensions and actual supplied control segments are retained, including leakage states.

For broadband the selected laboratory channel is Phi0 exp(k2), a weak-noise approximation, not a consequence of Gaussian scalar noise alone: noncommuting operators can retain higher ordered contributions. An independently propagated higher Hermite hierarchy must test its residual relative to the small noise-induced channel correction. That validation belongs to the main workflow; logged artifacts below are consumed, not recomputed here. Shared k2 agreement in selected/refined is not independent quadratic-response validation.

Bath restarts remove cross-block correlations and change the physical target; blocks do not reset the real bath. The signed contrasts and full complex-matrix distances are:
{chr(10).join(comparisons)}
Refinement changes indicate numerical stability, not certified absolute error. Inspect effective orders: tighter settings may select the same final order. A small fidelity change can conceal coherent or leakage discrepancies; channel and k2 distances are therefore reported in `ablation.csv` as well.

## Figures, resources, and remaining limitations
`figures/primary_result.png` compares infidelity and coherent size, not ground-truth error. `figures/robustness_or_scaling.png` places refinement changes and physical memory contrasts against measured predictor time; no_memory is not an alternative accuracy reference. `figures/sources.json` identifies every plotted CSV row. `scaling.csv` includes all selected cases with segments from len(dt) and dimension from H.shape[-1], not gate counts or computational-subspace size.
Largest selected predictor time is {slowest['seconds']:.6g} s (`{slowest['row_id']}`); largest reported process RSS is {largest['peak_rss_mb']:.6g} MiB (`{largest['row_id']}`). These are public measurements, not guarantees of the 60 s / 1.5 GiB target on unseen cases. Predictor timing excludes interpreter startup and file I/O. Quadrature/hierarchy caps, floating-point cancellation of tiny corrections, and weak-noise truncation remain limitations; convergence flags must be checked. Trace preservation, positivity, Gaussianity, and agreement in one scalar are not proofs of channel accuracy. Sampling error in trajectory diagnostics is distinct from discretization bias or model error.

## Recorded refinement histories
{chr(10).join(histories)}

## Existing diagnostic artifacts (not rerun)
{logged or 'No standalone diagnostic artifacts found. Independent broadband and quadratic-response validation remain unestablished by this automation.'}
"""
    (OUTPUT / 'report.md').write_text(report)


if __name__ == '__main__':
    main()
