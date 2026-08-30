import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'adversary'))
from conditioned_cases import make_cases, validate_case, write_challenge

SEED = 804371927
SAMPLES = 180
LIMIT = 18.0


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + '\n')


def snapshot_generation_one():
    seal_path = ROOT / 'adversary/frozen_generation_1.json'
    seal = json.loads(seal_path.read_text())
    snapshot = ROOT / 'adversary/generation_1_snapshot'
    if not snapshot.exists():
        for name, expected in seal['sha256'].items():
            if digest(ROOT / name) != expected:
                raise RuntimeError('Generation-one input changed before snapshot: ' + name)
        snapshot.mkdir()
        for section in ['participant', 'evaluator']:
            shutil.copytree(ROOT / section, snapshot / section, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(ROOT / 'status.json', snapshot / 'status.json')
        shutil.copyfile(seal_path, snapshot / 'frozen_generation_1.json')
    for name, expected in seal['sha256'].items():
        if digest(snapshot / name) != expected:
            raise RuntimeError('Generation-one snapshot seal mismatch: ' + name)
    if digest(snapshot / 'frozen_generation_1.json') != digest(seal_path):
        raise RuntimeError('Generation-one seal was altered')
    return snapshot, seal


def main():
    commitment_path = ROOT / 'adversary/generation_2_preparation.json'
    if (ROOT / 'adversary/frozen_generation_2.json').exists() or commitment_path.exists():
        raise RuntimeError('Generation two is already committed; preparation cannot silently rewrite it')
    snapshot, seal = snapshot_generation_one()
    challenge = ROOT / 'adversary/conditioned_transition_challenge'
    if not (challenge / 'validation.json').exists():
        write_challenge(challenge, SEED, SAMPLES)
    light_cases = json.loads((challenge / 'cases.json').read_text())
    if light_cases != make_cases(SEED, SAMPLES):
        raise RuntimeError('Challenge differs from the complete specified stratified sample')
    light_references = json.loads((challenge / 'references.json').read_text())
    original_cases = json.loads((snapshot / 'evaluator/hidden/cases.json').read_text())
    original_references = json.loads((snapshot / 'evaluator/hidden/references.json').read_text())
    cases, references = original_cases + light_cases, original_references + light_references
    if len(cases) != len(references):
        raise AssertionError('Case/reference count mismatch')
    diagnostics = []
    for index, (case, reference) in enumerate(zip(cases, references)):
        verified, diagnostic = validate_case(case)
        energy = sum(vector[3] for vector in case['p'])
        stored_error = max(float(np.max(np.abs(np.asarray(verified['mapped']) - reference['mapped'])) / energy),
                           float(np.max(np.abs(np.asarray(verified['y']) - reference['y']))),
                           float(np.max(np.abs(np.asarray(verified['s']) - reference['s']))))
        if stored_error > 2e-13:
            raise AssertionError('Stored oracle differs from independent validation: ' + case['id'])
        diagnostic['stored_reference_disagreement'] = stored_error
        diagnostics.append(diagnostic)
        if (index + 1) % 300 == 0:
            print('preparation validated', index + 1, flush=True)
    if len(original_cases) != 104 or len(cases) != 1724 or len({case['id'] for case in cases}) != len(cases):
        raise AssertionError('Unexpected case count or duplicate identity')
    for section in ['baseline', 'workspace']:
        for filename in ['kinematics.f', 'phaseee.f', 'eerad3lib.f', 'driver.f90', 'Makefile']:
            name = f'participant/{section}/{filename}'
            if digest(ROOT / name) != seal['sha256'][name]:
                raise AssertionError('Public native starting files changed: ' + name)
    hidden = ROOT / 'evaluator/hidden'
    put(hidden / 'cases.json', cases)
    put(hidden / 'references.json', references)
    validation = {'case_count': len(cases), 'original_cases_preserved': len(original_cases),
                  'family_counts': dict(Counter(case['family'] for case in cases)),
                  'methods': ['covariant geometric quadratic at 140 and 190 digits',
                              'direct DAK algebra at 160 digits', 'independent rest-frame sphere at 180 digits'],
                  'max_binary64_reference_disagreement': max(item['oracle_disagreement'] for item in diagnostics),
                  'max_stored_reference_disagreement': max(item['stored_reference_disagreement'] for item in diagnostics),
                  'max_input_cm_residual': max(item['input_cm_residual'] for item in diagnostics),
                  'max_input_null_residual': max(item['input_null_residual'] for item in diagnostics),
                  'max_rest_frame_shell_residual': max(item['rest_frame_shell_residual'] for item in diagnostics),
                  'original_oracle_and_tolerances_unchanged': True,
                  'selection': 'All nine stratified samples retained; no artifact-based rejection sampling.'}
    put(hidden / 'oracle_validation.json', validation)
    original_target = json.loads((snapshot / 'evaluator/hidden/target.json').read_text())
    tolerance_names = ['momentum_atol', 'shell_atol', 'conservation_atol', 'mapped_invariant_atol',
                       'invariant_rtol', 'invariant_atol', 'rotation_atol']
    fixed_at = datetime.now(timezone.utc).isoformat()
    target = {name: original_target[name] for name in tolerance_names}
    target.update(generation=2, case_count=len(cases), family_count=len(validation['family_counts']),
                  runtime_ratio_limit=LIMIT, timing_repeats=500, timing_pairs=5,
                  minimum_baseline_cpu_seconds=0.5, maximum_timing_repeats=20000,
                  target_fixed_utc=fixed_at, freeze_utc=None, baseline_must_fail=True,
                  calibration_policy='Retain the previously fixed 18x budget; no threshold fit to a new solver.',
                  case_sha256=digest(hidden / 'cases.json'), reference_sha256=digest(hidden / 'references.json'),
                  original_case_sha256=seal['sha256']['evaluator/hidden/cases.json'],
                  original_reference_sha256=seal['sha256']['evaluator/hidden/references.json'],
                  distribution={'seed': SEED, 'samples_per_light_family': SAMPLES,
                                'family_counts': validation['family_counts'], 'timing_cases': 'all correctness cases once per repeat'})
    protected = ['evaluator/evaluate.py', 'evaluator/trusted_runner.py', 'evaluator/hidden/oracle.py',
                 'evaluator/hidden/generate.py', 'evaluator/hidden/driver.f90',
                 'evaluator/hidden/pristine/kinematics.f', 'evaluator/hidden/pristine/phaseee.f',
                 'evaluator/hidden/pristine/eerad3lib.f']
    target['required_sha256'] = {name: digest(ROOT / name) for name in protected}
    put(hidden / 'target.json', target)
    put(ROOT / 'participant/input/RESOURCE.json', {
        'generation': 2, 'runtime_ratio_limit': LIMIT,
        'metric': 'median of five alternating same-CPU trusted whole-process candidate/baseline CPU ratios',
        'accounting': 'read-only in-namespace supervisor reaps native process and adopted descendants; native CPU_TIME ignored',
        'initial_repeats': 500, 'minimum_baseline_cpu_seconds': 0.5, 'maximum_repeats': 20000,
        'absolute_runtime_floor': None, 'case_count': len(cases), 'target_fixed_utc': fixed_at,
        'freeze_utc': None})
    prior_status = json.loads((snapshot / 'status.json').read_text())
    put(ROOT / 'status.json', {
        'name': prior_status['name'], 'mode': 'F', 'generation': 2, 'status': 'prepared_for_main_review_not_frozen',
        'target': {'all_cases': len(cases), 'all_families': len(validation['family_counts']),
                   'runtime_ratio_max': LIMIT, 'numerical_tolerances': 'unchanged from generation one'},
        'target_fixed_utc': fixed_at, 'target_sha256': digest(hidden / 'target.json'),
        'baseline_score': None, 'incumbent_score': None, 'privileged_score': None,
        'solvability': 'hard_open_candidate_pending_private_validation', 'ratchet_generations': 1,
        'maximum_total_generations': 3, 'fresh_attempts': [],
        'generation_1_history': {'snapshot': 'adversary/generation_1_snapshot',
                                 'actual_attempt': 'attempts/v_1.run.json',
                                 'champion': 'champions/generation_1/workspace',
                                 'evaluation': 'champions/generation_1/evaluation.json',
                                 'original_light_score': 'adversary/generation_1_light_score.json',
                                 'conditioned_search': 'adversary/conditioned_transition_scores.json'},
        'oracle_validation': 'evaluator/hidden/oracle_validation.json',
        'preparation_manifest': 'adversary/generation_2_preparation.json',
        'fresh_generation_2_attempt_started': False, 'freeze_delegated_to_main': True})
    material = {}
    for section in ['participant', 'evaluator']:
        for path in sorted((ROOT / section).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                material[str(path.relative_to(ROOT))] = digest(path)
    put(commitment_path, {'generation': 2, 'prepared_utc': fixed_at, 'not_a_generation_freeze': True,
                          'target_sha256': digest(hidden / 'target.json'), 'sha256': material,
                          'recipe_sha256': digest(Path(__file__)),
                          'generator_sha256': digest(ROOT / 'adversary/conditioned_cases.py'),
                          'scientific_evidence': 'adversary/generation_2_science.md',
                          'original_seal_preserved': True, 'snapshot_file_count': len(seal['sha256']),
                          'fresh_attempts_started': 0})
    print('Prepared', len(cases), 'cases;', len(validation['family_counts']), 'families;', LIMIT, 'x; NOT FROZEN', flush=True)


if __name__ == '__main__':
    main()
