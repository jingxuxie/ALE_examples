import datetime
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
from evaluate import aggregate


def main():
    if (ROOT / 'frozen_manifest.json').exists():
        raise SystemExit('already frozen; no silent revision allowed')
    baseline_path = ROOT / 'attempts' / 'baseline_hidden.json'
    champion_path = ROOT / 'adversary' / 'champion_hidden.json'
    baseline = json.loads(baseline_path.read_text())
    champion = json.loads(champion_path.read_text())
    preflight = json.loads((ROOT / 'adversary' / 'replay_preflight.json').read_text())
    validation = json.loads((ROOT / 'adversary' / 'validation.json').read_text())
    if not baseline.get('completed') or not champion.get('completed') or not preflight['passed'] or not validation['passed']:
        raise SystemExit('complete baseline, privileged evaluation and passing replay preflight required')
    policy_path = ROOT / 'participant' / 'workspace' / 'policy.json'
    policy = json.loads(policy_path.read_text())
    baseline_summary = aggregate(baseline['cases'], policy)
    champion_summary = aggregate(champion['cases'], policy)
    if not baseline_summary['valid'] or abs(baseline_summary['family_balanced_gain']) > 1e-9:
        raise SystemExit('baseline reproduction failed')
    if not champion_summary['valid']:
        raise SystemExit('privileged numerical control is invalid')
    if policy['mean_gain_min'] != 0.12 or policy['worst_family_gain_min'] != 0.08:
        raise SystemExit('retain the original 12 percent / 8 percent targets')
    policy['frozen'] = True
    policy_path.write_text(json.dumps(policy, indent=2) + '\n')
    for report, path in [(baseline, baseline_path), (champion, champion_path)]:
        if not path.with_suffix('.before_freeze.json').exists():
            path.with_suffix('.before_freeze.json').write_text(json.dumps(report, indent=2) + '\n')
        report['policy'] = policy
        report.update(aggregate(report['cases'], policy))
        report['targets_selected_before_any_fresh_agent'] = True
        for row in report['cases']:
            row['runtime_seconds'] = row.get('runtime', {}).get('wall_seconds', 0.0)
            row['core_score'] = row.get('gain')
            row['reason'] = row.get('error', 'feasible artifact scored' if row.get('feasible') else 'feasibility checks failed')
        path.write_text(json.dumps(report, indent=2) + '\n')
    prior = ROOT.parents[2] / 'tasks' / ROOT.parent.name / 'solution' / 'v_01' / 'solve.py'
    source = ROOT.parent / 'authoring' / 'sources' / 'kdotpy-1.4.1' / 'src' / 'kdotpy' / 'berry.py'
    provenance = {'paper': 'arXiv:2407.12651', 'lattice_chern_method': 'arXiv:cond-mat/0503172',
                  'scope': 'Synthetic downstream atlas acquisition; not a full Kane-model material simulation.',
                  'prior_reference_sha256': hashlib.sha256(prior.read_bytes()).hexdigest(),
                  'shared_kdotpy_berry_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                  'prior_use': 'Scoring definitions and search approach inspected; new vectorized scorer and independent tests written. No prior agent conversation or outputs copied to participant.',
                  'numpy': np.__version__, 'scipy': scipy.__version__}
    (ROOT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    files = []
    for directory in ['participant', 'evaluator', 'champions']:
        files.extend(path for path in (ROOT / directory).rglob('*') if path.is_file() and '__pycache__' not in path.parts)
    files.extend((ROOT / 'adversary').glob('*.py'))
    files.extend([ROOT / 'README.md', ROOT / 'provenance.json'])
    manifest = {'frozen_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'policy': policy, 'sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(files))}}
    manifest_path = ROOT / 'frozen_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    status = {'concept': 1, 'verification_mode': 'A', 'name': 'Robust topology-constrained band atlas improvement',
              'status': 'ready_for_fresh_screen', 'hardness_claim': False, 'frozen': True,
              'reason': 'Public package, hidden cases, baseline and targets frozen after private calibration; no fresh agent evidence exists.',
              'solvability': 'demonstrated by privileged control' if champion_summary['passed'] else 'unknown',
              'known_passing_solution': champion_summary['passed'],
              'headroom_status': 'Measured control passes targets' if champion_summary['passed'] else 'Original 12 percent overall and 8 percent worst-family targets retained; passing-solution headroom not established.',
              'policy': policy, 'baseline': baseline_summary, 'privileged_control': champion_summary,
              'baseline_report': 'attempts/baseline_hidden.json', 'privileged_report': 'adversary/champion_hidden.json',
              'validation_log': 'adversary/validation.log', 'validation_json': 'adversary/validation.json',
              'replay_preflight': 'adversary/replay_preflight.json',
              'replay_preflight_passed': True, 'solver_generation_isolation_preflight': 'Not performed: controller must test its exact fresh-agent tool configuration separately.',
              'fresh_attempts': [], 'confirmation_attempts': [], 'human_validation_status': 'not_performed',
              'frozen_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              'scientific_cautions': ['Synthetic lattice-Dirac acquisition proxy, not material-specific Kane data.',
                                      'Determinant-bundle Chern class, not a global smooth frame or individual-band invariant.',
                                      'Privileged heuristic provides feasible upper bounds, not an exact optimum.',
                                      'Replay wall time is hardware-sensitive and includes isolated startup.']}
    (ROOT / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'status': status['status'], 'policy': policy, 'baseline': baseline_summary, 'privileged': champion_summary}, indent=2))


if __name__ == '__main__':
    main()
