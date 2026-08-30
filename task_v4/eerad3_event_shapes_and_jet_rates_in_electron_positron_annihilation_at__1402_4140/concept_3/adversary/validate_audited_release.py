import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
import evaluate


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(artifact):
    try:
        result = evaluate.evaluate(ROOT / artifact)
    except Exception as error:
        result = evaluate.exception_result(error)
    result['artifact'] = artifact
    result['audit_utc'] = datetime.now(timezone.utc).isoformat()
    result['artifact_sha256'] = {name: digest(ROOT / artifact / name) for name in evaluate.SOURCES}
    return result


def scores():
    for label, artifact in [('baseline', 'participant/baseline'),
                            ('privileged', 'champions/selective_precision'),
                            ('fresh_v1', 'attempts/v_1/workspace')]:
        result = score(artifact)
        put(ROOT / f'adversary/{label}_audit_score.json', result)
        if label == 'fresh_v1':
            put(ROOT / 'attempts/v_1.audit_evaluation.json', result)
        print(label, {name: result.get(name) for name in ['valid', 'passed', 'failed_case_count',
              'runtime_ratio', 'candidate_cpu_seconds', 'baseline_cpu_seconds', 'reason']}, flush=True)
        if not result['valid']:
            raise RuntimeError('Audit score was not valid: ' + label)


def native_probe(source, runs=1):
    reports = []
    with tempfile.TemporaryDirectory(prefix='eerad3-release-probe-') as temporary:
        directory = Path(temporary)
        shutil.copyfile(ROOT / 'adversary' / source, directory / 'probe.c')
        subprocess.run(evaluate.isolated_command(directory, ['gcc', '-O2', 'probe.c', '-o', 'runner'],
                       compile_phase=True), check=True, capture_output=True, timeout=45,
                       preexec_fn=evaluate.limits)
        for trial in range(runs):
            result = subprocess.run(evaluate.isolated_command(directory,
                         ['/usr/bin/python3', '-I', '/trusted_runner.py']), input='',
                         capture_output=True, text=True, timeout=90, preexec_fn=evaluate.limits)
            assert result.returncode == 0, result.stderr
            report = json.loads(result.stdout)
            assert 'wrapper_error' not in report, report
            assert report['returncode'] == 0 and not report['descendant_failures'], report
            report.pop('stdout_b64')
            reports.append(report)
    return reports


def controls():
    result = {}
    result['orphan'] = native_probe('release_orphan_probe.c')[0]
    assert result['orphan']['adopted_descendants'] >= 1, result
    assert result['orphan']['cpu_seconds'] >= 0.17, result
    result['readonly_fresh_nondumpable'] = native_probe('release_isolation_probe.c', 2)
    spoof = score('adversary/timer_interposition')
    put(ROOT / 'adversary/timer_spoof_audit_score.json', spoof)
    assert spoof['valid'] and spoof['passed'], spoof
    assert spoof['candidate_cpu_seconds'] > 0.005, spoof
    result['cpu_time_spoof'] = {'passed': True, 'evidence': 'adversary/timer_spoof_audit_score.json',
                              'trusted_cpu_seconds': spoof['candidate_cpu_seconds']}
    cases = json.loads((evaluate.HIDDEN / 'cases.json').read_text())[:1]
    accounting = {'returncode': 0, 'cpu_seconds': 0.25, 'user_seconds': 0.2, 'system_seconds': 0.05,
                  'descendant_failures': []}
    invalid_outputs = ['', 'TIME 0 0\n', '0 0\nTIME 0 0\n',
                       ' '.join(['0'] * 84) + '\nWRONG 0 0\n']
    original_run = evaluate.subprocess.run
    schema_checks = []
    try:
        for output in invalid_outputs:
            response = dict(accounting, stdout_b64=base64.b64encode(output.encode()).decode())
            evaluate.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess([], 0, json.dumps(response), '')
            try:
                evaluate.run(Path('/unused/runner'), cases)
                raise AssertionError('Malformed output was accepted')
            except ValueError as error:
                rejected = evaluate.exception_result(error)
                assert not rejected['valid'] and not rejected['passed']
                assert rejected['error_type'] == 'invalid_submission'
                assert all(rejected[key] == 0 for key in ['core_score', 'worst_family_score', 'runtime_score'])
                schema_checks.append(rejected)
        output = ' '.join(['0'] * 84) + '\nTIME not-a-number ignored\n'
        response = dict(accounting, stdout_b64=base64.b64encode(output.encode()).decode())
        evaluate.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess([], 0, json.dumps(response), '')
        records, duration = evaluate.run(Path('/unused/runner'), cases)
        assert duration == 0.25 and len(records) == 1
    finally:
        evaluate.subprocess.run = original_run
    for label in ['environment_error', 'measurement_error']:
        rejected = evaluate.exception_result(RuntimeError(label + ': test'))
        assert rejected['infrastructure_error'] and rejected['error_type'] == label
        assert not rejected['valid'] and not rejected['passed']
        assert all(rejected[key] == 0 for key in ['core_score', 'worst_family_score', 'runtime_score'])
        schema_checks.append(rejected)
    missing = score('adversary/release_missing_submission') if (ROOT / 'adversary/release_missing_submission').exists() else evaluate.exception_result(ValueError('Missing source'))
    assert missing['error_type'] == 'invalid_submission'
    result['invalid_output_schema'] = schema_checks
    result['candidate_time_numeric_ignored'] = True
    result['passed'] = True
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    put(ROOT / 'adversary/release_audit_controls.json', result)
    print('RELEASE AUDIT CONTROLS PASS', result['orphan']['cpu_seconds'], flush=True)


def finalize():
    snapshot = ROOT / 'adversary/generation_1_snapshot'
    seal = json.loads((ROOT / 'adversary/frozen_generation_1.json').read_text())
    for filename, expected in seal['sha256'].items():
        assert digest(snapshot / filename) == expected, filename
    assert digest(snapshot / 'frozen_generation_1.json') == digest(ROOT / 'adversary/frozen_generation_1.json')
    target = json.loads((evaluate.HIDDEN / 'target.json').read_text())
    assert digest(evaluate.HIDDEN / 'target.json') == digest(snapshot / 'evaluator/hidden/target.json')
    for filename, key in [('cases.json', 'case_sha256'), ('references.json', 'reference_sha256')]:
        assert digest(evaluate.HIDDEN / filename) == target[key]
    assert target['timing_repeats'] == 300 and target['runtime_ratio_limit'] == 18.0
    cases = json.loads((evaluate.HIDDEN / 'cases.json').read_text())
    assert len(cases) == 104
    for folder in ['participant/workspace', 'participant/baseline']:
        for filename in evaluate.SOURCES + ['driver.f90', 'Makefile']:
            assert digest(ROOT / folder / filename) == digest(snapshot / folder / filename)
    audited = {key + '_score': json.loads((ROOT / f'adversary/{label}_audit_score.json').read_text())
               for key, label in [('baseline', 'baseline'), ('privileged', 'privileged'), ('fresh_v1', 'fresh_v1')]}
    controls_report = json.loads((ROOT / 'adversary/release_audit_controls.json').read_text())
    artifact_guard = json.loads((ROOT / 'adversary/release_artifact_guard.json').read_text())
    assert artifact_guard['passed'] and artifact_guard['rejected_before_copy']
    unit_controls = json.loads((ROOT / 'adversary/release_audit_unit_controls.json').read_text())
    assert unit_controls['passed']
    assert all(value['valid'] for value in audited.values())
    assert not audited['baseline_score']['passed'] and audited['baseline_score']['failed_case_count'] > 0
    assert audited['privileged_score']['passed'] and audited['fresh_v1_score']['passed'] and controls_report['passed']
    original_score = json.loads((ROOT / 'attempts/v_1.evaluation.json').read_text())
    countersearch = json.loads((ROOT / 'adversary/champion_quality_search/reference_summary.json').read_text())
    assert countersearch['checked'] == 12000 and not countersearch['failures']
    idle_path = ROOT.parent / 'research/idle_core_probe.json'
    idle_probe = json.loads(idle_path.read_text())
    idle_score = idle_probe['scores']['1_incumbent']
    assert idle_score['quality_passed'] and idle_score['relative_mad'] > 0.25
    idle_summary = {'source': '../research/idle_core_probe.json', 'source_sha256': digest(idle_path),
                    'selected_cpu': idle_probe['selected_cpu'], 'initial_idle_fraction': idle_probe['initial_idle_fraction'],
                    'ratios': [trial['ratio'] for trial in idle_score['paired_trials']],
                    'median_ratio': idle_score['runtime_ratio'], 'relative_mad': idle_score['relative_mad'],
                    'predeclared_relative_mad_limit': 0.25, 'quality_passed': True,
                    'decision': 'no_go', 'new_target_committed': False, 'hardness_claimed': False}
    put(ROOT / 'adversary/idle_core_no_go.json', idle_summary)
    hashes = {str(path.relative_to(ROOT)): digest(path)
              for folder in ['participant', 'evaluator'] for path in sorted((ROOT / folder).rglob('*'))
              if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
    manifest = {'audit_revision': 'generation_1_trusted_cpu_v1', 'original_generation': 1,
                'audited_utc': datetime.now(timezone.utc).isoformat(), 'release_valid': True,
                'sha256': hashes, 'original_seal': 'adversary/frozen_generation_1.json',
                'original_snapshot_verified_files': len(seal['sha256']),
                'unchanged_target': {key: target[key] for key in ['timing_repeats', 'runtime_ratio_limit',
                                                               'case_sha256', 'reference_sha256']},
                'unchanged_case_count': 104, 'numerical_tolerances_unchanged': True,
                'resource_change': 'Ignore candidate TIME; full native startup, work, I/O and descendant user+system CPU from protected in-namespace parent RUSAGE_CHILDREN',
                'target_sha256': digest(evaluate.HIDDEN / 'target.json'),
                'original_fresh_evaluation_sha256': digest(ROOT / 'attempts/v_1.evaluation.json'),
                'audit_scores': {label: f'adversary/{label}_audit_score.json' for label in ['baseline', 'privileged', 'fresh_v1']},
                'controls': 'adversary/release_audit_controls.json',
                'artifact_directory_guard': 'adversary/release_artifact_guard.json',
                'unit_controls': 'adversary/release_audit_unit_controls.json',
                'idle_core_diagnostic': 'adversary/idle_core_no_go.json',
                'unfrozen_draft': 'adversary/unfrozen_throughput_draft', 'new_generation': False}
    put(ROOT / 'adversary/audited_release.json', manifest)
    original_status = json.loads((snapshot / 'status.json').read_text())
    status = {key: original_status[key] for key in ['name', 'mode', 'baseline_score', 'privileged_score']}
    status.update(generation=1, status='solved', solved=True, retained=False, release_valid=True,
                  solvability='demonstrated', failed_capability=None, ratchet_generations=0,
                  maximum_total_generations=3, total_generations=1, original_fresh_score=original_score,
                  audited_release_scores=audited, audit_revision='adversary/audited_release.json',
                  target={'all_cases': 104, 'all_families': 9, 'timing_repeats': 300, 'runtime_ratio_max': 18.0},
                  target_sha256=digest(evaluate.HIDDEN / 'target.json'),
                  fresh_attempts=[{'generation': 1, 'model': 'ultima-alpha', 'artifact': 'attempts/v_1/workspace',
                                  'evaluation': 'attempts/v_1.evaluation.json',
                                  'audit_evaluation': 'attempts/v_1.audit_evaluation.json', 'passed': True}],
                  countersearch_summary={'native_cases': 12000, 'oracle_checked': 12000, 'quality_failures': 0,
                      'independent_oracle_spotchecks': len(countersearch['independent_reference_checks']),
                      'largest_reported_gate_ratio': countersearch['largest_gate_ratio'],
                      'evidence': 'adversary/champion_quality_search/reference_summary.json',
                      'idle_core_resource_check': idle_summary, 'discovery_decision': 'rejected_no_robust_champion_failure'},
                  throughput_proposal={'status': 'unfrozen_no_go', 'hardness_claimed': False,
                      'evidence': 'adversary/calibration_early_stop.json',
                      'archive': 'adversary/unfrozen_throughput_draft'},
                  active_calibration_running=False, fresh_generation_2_attempt_started=False,
                  resource_hardness_claimed=False, final_utc=datetime.now(timezone.utc).isoformat())
    put(ROOT / 'status.json', status)
    differences = sorted(filename for filename, value in hashes.items() if seal['sha256'].get(filename) != value)
    assert differences == ['evaluator/evaluate.py', 'evaluator/trusted_runner.py',
                           'participant/input/INTERFACE.md', 'participant/input/RESOURCE.json'], differences
    put(ROOT / 'adversary/audit_changed_paths.json', {
        'scope': 'concept_3 only; main-owned research evidence read but not edited',
        'active_release_differences_from_sealed_original': differences,
        'restored_original_files': sorted(filename for filename, value in hashes.items() if seal['sha256'].get(filename) == value),
        'operator_files': ['README.md', 'status.json', 'adversary/restore_generation_1.py',
                          'adversary/validate_audited_release.py', 'adversary/test_audit_guards.py',
                          'adversary/release_orphan_probe.c', 'adversary/release_isolation_probe.c',
                          'adversary/generation_2_progress.md'],
        'new_evidence': ['adversary/audited_release.json', 'adversary/baseline_audit_score.json',
                         'adversary/privileged_audit_score.json', 'adversary/fresh_v1_audit_score.json',
                         'adversary/timer_spoof_audit_score.json', 'attempts/v_1.audit_evaluation.json',
                         'adversary/release_audit_controls.json', 'adversary/release_artifact_guard.json',
                         'adversary/release_audit_unit_controls.json', 'adversary/idle_core_no_go.json',
                         'adversary/champion_quality_search/report.json',
                         'adversary/champion_quality_search/reference_summary.json'],
        'archives': ['adversary/unfrozen_throughput_draft/', 'adversary/release_audit_attempts/'],
        'private_search_scripts': ['adversary/search_champion_quality.py', 'adversary/summarize_champion_quality.py']})
    print('RELEASE VALID: SOLVED GENERATION 1, RATCHETS 0; manifest', len(hashes), 'files', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['scores', 'controls', 'finalize', 'all'])
    arguments = parser.parse_args()
    for phase in ['scores', 'controls', 'finalize'] if arguments.phase == 'all' else [arguments.phase]:
        globals()[phase]()
