import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    reports = []
    for path in ROOT.glob('*/*.score.json'):
        report = json.loads(path.read_text())
        if report.get('valid') and (ROOT / report['artifact']).is_file():
            reports.append(report)
    if not reports:
        raise RuntimeError('No valid private checkpoint exists')
    if (ROOT / 'PASS_FOUND.json').exists():
        selection = json.loads((ROOT / 'PASS_FOUND.json').read_text())['artifact']
    else:
        selected = max(reports, key=lambda report: (report.get('passed', False), report['worst_family_score'], report['core_score']))
        selection = selected['artifact']
    shutil.copyfile(ROOT / selection, ROOT / 'state.npz')
    near_misses = [report for report in reports if not report.get('passed')]
    if near_misses:
        near_miss = max(near_misses, key=lambda report: (report['worst_family_score'], report['core_score']))
        shutil.copyfile(ROOT / near_miss['artifact'], ROOT / 'near_miss.npz')
        write_json(ROOT / 'near_miss.score.json', near_miss)
    command = [sys.executable, str(CONCEPT / 'evaluator' / 'evaluate.py'), '--submission', str(ROOT), '--output', str(ROOT / 'exact_checker_score.json')]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    (ROOT / 'exact_checker_stdout.json').write_text(completed.stdout)
    (ROOT / 'exact_checker_stderr.log').write_text(completed.stderr)
    if completed.returncode:
        raise RuntimeError('Official evaluator process failed')
    official = json.loads((ROOT / 'exact_checker_score.json').read_text())
    manifest = json.loads((CONCEPT / 'adversary' / 'ratchet_3' / 'freeze_manifest.json').read_text())
    integrity = []
    for record in manifest['frozen_files']:
        actual = hashlib.sha256((CONCEPT / record['path']).read_bytes()).hexdigest()
        integrity.append({'path': record['path'], 'expected_sha256': record['sha256'], 'actual_sha256': actual, 'unchanged': actual == record['sha256']})
    write_json(ROOT / 'frozen_integrity.json', {'all_unchanged': all(record['unchanged'] for record in integrity), 'files': integrity})
    assert all(record['unchanged'] for record in integrity)
    from fit import CompositePhysics, np, raw_from_tensor, torch
    tensor = np.load(ROOT / 'state.npz', allow_pickle=False)['A']
    with torch.no_grad():
        fast = CompositePhysics(tensor.shape[1] // 2).observables(raw_from_tensor(tensor))
    metrics = official.get('metrics', {})
    differences = {'energy': abs(fast[0].item() - metrics['energy_excess'])}
    for index, name in enumerate(('order_correlations', 'density_connected_correlations', 'y_correlations', 'composite_order_covariances', 'three_interval_cumulants'), start=1):
        differences[name] = float(np.max(np.abs(fast[index].numpy() - metrics[name])))
    write_json(ROOT / 'selected_normalized_physics_audit.json', {'fast_vs_frozen_actual_LR_absolute_differences': differences,
        'canonical_defect': metrics['canonical_defect'], 'parity_defect': metrics['parity_defect'],
        'observable_eigenvalue': metrics['observable_transfer_eigenvalue'], 'observable_right_residual': metrics['observable_right_fixed_point_residual']})
    result = {'completed_utc': datetime.now(timezone.utc).isoformat(), 'contract_version': 'critical-vacuum-v4',
              'selected_checkpoint': selection, 'state_sha256': hashlib.sha256((ROOT / 'state.npz').read_bytes()).hexdigest(),
              'official_evaluator': official, 'frozen_surface_unchanged': True, 'fresh_v7_v8_attempts_or_audits_read': False,
              'generation_privileged_source_reuse': True, 'independent_fresh_participant_attempt': False,
              'passing_v4_witness_demonstrated': bool(official.get('passed')), 'normalized_physics_differences': differences,
              'worker_summaries': {path.parent.name: json.loads(path.read_text()) for path in ROOT.glob('*/summary.json')}}
    write_json(ROOT / 'portfolio_results.json', result)
    print(json.dumps({'selected': selection, 'sha256': result['state_sha256'], 'valid': official.get('valid'), 'passed': official.get('passed'),
                      'core_score': official.get('core_score'), 'worst_family_score': official.get('worst_family_score'),
                      'metrics': {name: metrics.get(name) for name in ('energy_excess', 'order_max_relative_error', 'density_max_relative_error', 'y_max_relative_error', 'composite_order_max_relative_error', 'three_interval_max_relative_error')},
                      'frozen_surface_unchanged': True}, indent=2), flush=True)


if __name__ == '__main__':
    main()
