import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    validation = read_json(ROOT / 'validation.json')
    baseline = read_json(ROOT / 'baseline_score.json')
    contract = read_json(CONCEPT / 'participant' / 'input' / 'contract.json')
    assert validation['passed'] and validation['bytecode_and_symlink_free']
    assert baseline['valid'] and not baseline['passed']
    assert baseline['contract_version'] == contract['version'] == 'critical-vacuum-v4'
    assert contract['three_interval_channel']['maximum_relative_error'] == .1
    assert contract['three_interval_channel']['sextuple_count'] == 252
    assert contract['construction_wall_seconds'] == 3600 and contract['checker_timeout_seconds'] == 120
    assert baseline['runtime_seconds'] < 120
    assert {path.name for path in (CONCEPT / 'participant' / 'baseline').iterdir()} == {'README.md', 'state.npz'}
    status = read_json(CONCEPT / 'status.json')
    if status.get('target_contract_version') != 'critical-vacuum-v4':
        status['generation_2_fresh_agent_scores'] = status.get('fresh_agent_scores', [])
    status.update({'status': 'ratchet_3_frozen_ready', 'evaluator_validated': True,
                   'validation_report': 'adversary/ratchet_3/validation.json', 'baseline_report': 'adversary/ratchet_3/baseline_score.json',
                   'baseline_passed': False, 'baseline_core_score': baseline['core_score'], 'baseline_worst_family_score': baseline['worst_family_score'],
                   'baseline_composite_order_max_relative_error': baseline['metrics']['composite_order_max_relative_error'],
                   'baseline_three_interval_max_relative_error': baseline['metrics']['three_interval_max_relative_error'],
                   'target_contract_version': 'critical-vacuum-v4', 'target_frozen_before_fresh_attempt': True,
                   'passing_solution_known': False, 'solvability': 'unknown_for_v4', 'ratchet_generations': 3,
                   'freeze_manifest': 'adversary/ratchet_3/freeze_manifest.json', 'fresh_agents_launched_by_ratchet_builder': False,
                   'fresh_agent_scores': [], 'selected_champion': 'champions/generation_3/state.npz',
                   'selected_champion_is_current_solution': False, 'baseline_champion_contract_version': 'critical-vacuum-v3',
                   'counterexample_search_report': 'adversary/ratchet_3_search/focused_summary.json',
                   'observable_normalization': 'actual left/right transfer fixed points and leading eigenvalue; original submitted-tensor admissibility gates',
                   'next_action': 'main may launch fresh isolated v7/v8 against the frozen v4 surface'})
    status['target'].update({'three_interval_max_relative_error': .1, 'three_interval_sextuple_count': 252, 'three_interval_span_max': 256})
    write_json(CONCEPT / 'status.json', status)
    files = []
    for folder in (CONCEPT / 'participant', CONCEPT / 'evaluator'):
        assert not list(folder.rglob('*.pyc')) and not list(folder.rglob('__pycache__'))
        for path in sorted(folder.rglob('*')):
            assert not path.is_symlink()
            if path.is_file():
                files.append({'path': str(path.relative_to(CONCEPT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                              'bytes': path.stat().st_size, 'mtime_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
    hashes = {record['path']: record['sha256'] for record in files}
    assert hashes['participant/workspace/physics.py'] == hashes['evaluator/hidden/trusted_physics.py'] == validation['public_trusted_source_sha256']
    assert hashes['participant/baseline/state.npz'] == validation['baseline_sha256']
    result = {'ratchet_generation': 3, 'contract_version': 'critical-vacuum-v4', 'ready_for_main_to_launch_fresh': True,
              'manifest_created_utc': datetime.now(timezone.utc).isoformat(), 'frozen_content_last_modified_utc': max(record['mtime_utc'] for record in files),
              'threshold_decision': 'User approved K3 relative error <=0.1 on all 252 sextuples before fresh v4 attempts; no target tightening after evaluation',
              'all_v3_physical_targets_and_admissibility_tolerances_retained': True,
              'three_interval_sextuple_count': 252, 'three_interval_span_max': 256, 'three_interval_relative_tolerance': .1,
              'submitted_subtraction': 'literal physical raw six-, four-, and two-point moments, all from the submitted state',
              'observable_normalization': 'actual left/right transfer fixed points and leading eigenvalue; no identity-boundary shortcut',
              'construction_wall_seconds': 3600, 'checker_timeout_seconds': 120, 'bond_dimension_max': 24,
              'baseline_source': 'champions/generation_3/state.npz', 'baseline_passed': False,
              'baseline_core_score': baseline['core_score'], 'baseline_worst_family_score': baseline['worst_family_score'],
              'baseline_three_interval_max_relative_error': baseline['metrics']['three_interval_max_relative_error'],
              'baseline_checker_seconds': baseline['runtime_seconds'], 'passing_v4_tensor_known_at_freeze': False,
              'solvability': 'unknown_for_v4', 'fresh_agents_launched_by_sidecar': False, 'old_generation_archives_modified': False,
              'public_bytecode_and_symlink_free': True, 'all_regular_public_files_hashed_without_exclusions': True,
              'validation_report': 'adversary/ratchet_3/validation.json', 'normalization_report': 'adversary/ratchet_3/normalization_gauge_certificates.json',
              'artifact_rejection_report': 'adversary/ratchet_3/artifact_rejection.json',
              'status_sha256': hashlib.sha256((CONCEPT / 'status.json').read_bytes()).hexdigest(), 'frozen_files': files}
    write_json(ROOT / 'freeze_manifest.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'frozen_files'}, indent=2))


if __name__ == '__main__':
    main()
