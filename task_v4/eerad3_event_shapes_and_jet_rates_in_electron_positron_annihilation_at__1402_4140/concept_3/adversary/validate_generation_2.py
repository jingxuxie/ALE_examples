import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
sys.path.insert(0, str(ROOT / 'adversary'))
from evaluate import build, evaluate, isolated_command, limits, run
from prepare_generation_2 import digest, put, snapshot_generation_one


def audit_package():
    snapshot, seal = snapshot_generation_one()
    commitment = json.loads((ROOT / 'adversary/generation_2_preparation.json').read_text())
    for name, expected in commitment['sha256'].items():
        if digest(ROOT / name) != expected:
            raise AssertionError('Prepared participant/evaluator changed: ' + name)
    hidden = ROOT / 'evaluator/hidden'
    cases = json.loads((hidden / 'cases.json').read_text())
    references = json.loads((hidden / 'references.json').read_text())
    original_cases = json.loads((snapshot / 'evaluator/hidden/cases.json').read_text())
    original_references = json.loads((snapshot / 'evaluator/hidden/references.json').read_text())
    assert cases[:104] == original_cases and references[:104] == original_references
    assert len(cases) == len(references) == 1724
    target = json.loads((hidden / 'target.json').read_text())
    original_target = json.loads((snapshot / 'evaluator/hidden/target.json').read_text())
    assert target['runtime_ratio_limit'] == original_target['runtime_ratio_limit'] == 18.0
    for name in ['momentum_atol', 'shell_atol', 'conservation_atol', 'mapped_invariant_atol',
                 'invariant_rtol', 'invariant_atol', 'rotation_atol']:
        assert target[name] == original_target[name], name
    assert digest(hidden / 'oracle.py') == seal['sha256']['evaluator/hidden/oracle.py']
    assert digest(hidden / 'driver.f90') == seal['sha256']['evaluator/hidden/driver.f90']
    for section in ['baseline', 'workspace']:
        for path in (snapshot / 'participant' / section).iterdir():
            assert digest(ROOT / 'participant' / section / path.name) == digest(path)
    for path in (ROOT / 'participant').rglob('*'):
        assert not path.is_symlink(), path
    return {'passed': True, 'generation_1_sealed_files_verified': len(seal['sha256']),
            'original_cases_and_references_unchanged': True, 'numerical_contract_unchanged': True,
            'native_public_workspace_and_baseline_unchanged': True,
            'prepared_material_hash_count': len(commitment['sha256']),
            'target_sha256': digest(hidden / 'target.json')}


def resource_controls():
    cases = json.loads((ROOT / 'evaluator/hidden/cases.json').read_text())
    with tempfile.TemporaryDirectory(prefix='eerad3-timer-spoof-') as directory:
        executable = build(ROOT / 'adversary/timer_interposition', Path(directory))
        audit = {}
        unused, duration = run(executable, cases, 10, timing_audit=audit)
        assert audit['untrusted_native_cpu_seconds'] == 0.0
        assert duration > 0.02
        forged = {'passed': True, **audit,
                  'test': 'linked _gfortran_cpu_time_8 returns zero; trusted CPU remains measured and nonzero'}
    with tempfile.TemporaryDirectory(prefix='eerad3-descendant-') as directory:
        directory = Path(directory)
        shutil.copyfile(ROOT / 'adversary/descendant_probe.c', directory / 'probe.c')
        compile_result = subprocess.run(isolated_command(directory, ['gcc', '-O2', 'probe.c', '-o', 'runner']),
                                        capture_output=True, text=True, timeout=45, preexec_fn=limits)
        if compile_result.returncode:
            raise RuntimeError(compile_result.stderr)
        result = subprocess.run(isolated_command(directory, ['/usr/bin/python3', '-I', '/trusted_runner.py'], trusted=True),
                                capture_output=True, text=True, timeout=40, preexec_fn=limits)
        if result.returncode:
            raise RuntimeError(result.stderr)
        data = json.loads(result.stdout)
        assert data['returncode'] == 0 and data['cpu_seconds'] >= 0.14
        descendant = {'passed': True, 'trusted_cpu_seconds': data['cpu_seconds'],
                      'test': 'parent exits without waiting; adopted child consumes 0.15 CPU seconds'}
        readonly = subprocess.run(isolated_command(directory, ['/bin/sh', '-c', 'printf tampered > /trusted_runner.py'], trusted=True),
                                  capture_output=True, text=True, timeout=10, preexec_fn=limits)
        assert readonly.returncode != 0 and 'Read-only' in readonly.stderr
    return {'timer_interposition': forged, 'adopted_descendant': descendant,
            'trusted_wrapper_readonly': {'passed': True}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--static-only', action='store_true')
    parser.add_argument('--controls-only', action='store_true')
    parser.add_argument('--artifacts', nargs='+', default=['participant/baseline', 'champions/generation_1/workspace',
                                                          'adversary/extended_wide', 'adversary/adaptive_wide'])
    arguments = parser.parse_args()
    audit = audit_package()
    put(ROOT / 'adversary/generation_2_package_audit.json', audit)
    print('package audit passed', flush=True)
    if arguments.static_only:
        return
    controls = resource_controls()
    put(ROOT / 'adversary/generation_2_resource_controls.json', controls)
    print('trusted CPU controls passed', flush=True)
    if arguments.controls_only:
        return
    names = {'participant/baseline': 'baseline', 'champions/generation_1/workspace': 'incumbent',
             'adversary/extended_wide': 'demoted', 'adversary/adaptive_wide': 'adaptive'}
    reports = {}
    for artifact in arguments.artifacts:
        name = names.get(artifact, Path(artifact).name)
        try:
            result = evaluate(ROOT / artifact)
        except Exception as error:
            result = {'passed': False, 'reason': type(error).__name__ + ': ' + str(error), 'measurement_invalid': True}
        result['artifact'] = artifact
        result['source_sha256'] = {filename: digest(ROOT / artifact / filename)
                                   for filename in ['kinematics.f', 'phaseee.f', 'eerad3lib.f']}
        put(ROOT / 'adversary' / ('generation_2_' + name + '_score.json'), result)
        reports[name] = result
        print(name, json.dumps({key: result.get(key) for key in ['passed', 'failed_case_count', 'runtime_ratio', 'reason']}), flush=True)
    status = json.loads((ROOT / 'status.json').read_text())
    for name, key in [('baseline', 'baseline_score'), ('incumbent', 'incumbent_score'), ('adaptive', 'privileged_score')]:
        if name in reports:
            status[key] = reports[name]
    if reports.get('adaptive', {}).get('passed'):
        status['solvability'] = 'demonstrated_private_adaptive_precision'
        status['private_passing_artifact'] = 'adversary/adaptive_wide'
    elif 'adaptive' in reports:
        status['solvability'] = 'hard_open_candidate'
    status['resource_controls'] = 'adversary/generation_2_resource_controls.json'
    status['package_audit'] = 'adversary/generation_2_package_audit.json'
    put(ROOT / 'status.json', status)
    audit_package()


if __name__ == '__main__':
    main()
