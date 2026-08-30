import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[3]
PRIVATE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
import numpy as np
import model

from independent_check import check as independent_check


def patch_text(path, text):
    if path.exists():
        if path.read_text() == text:
            return
        raise RuntimeError('Refusing to overwrite test fixture: ' + str(path))
    relative = path.relative_to(ROOT)
    patch = '*** Begin Patch\n*** Add File: ' + str(relative) + '\n'
    patch += ''.join('+' + line + '\n' for line in text.splitlines())
    patch += '*** End Patch\n'
    applied = subprocess.run(['apply_patch'], input=patch, capture_output=True, text=True, cwd=ROOT)
    if applied.returncode:
        raise RuntimeError(applied.stdout + applied.stderr)


def official(path):
    command = [sys.executable, str(ROOT / 'evaluator' / 'evaluate.py'), '--submission', str(path)]
    environment = os.environ.copy()
    environment.pop('PYTHONDONTWRITEBYTECODE', None)
    process = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, env=environment)
    if process.returncode:
        raise RuntimeError(process.stderr)
    return json.loads(process.stdout)


def archive_hashes():
    result = {}
    for directory in (ROOT / 'champions' / 'generation_1', ROOT / 'champions' / 'generation_2',
                      ROOT / 'adversary' / 'generation_1_snapshot', ROOT / 'adversary' / 'generation_2_snapshot'):
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    started = time.perf_counter()
    preserved = archive_hashes()
    assertions = []
    targets = json.loads((ROOT / 'participant' / 'input' / 'targets.json').read_text())
    assert targets['generation'] == 3 and targets['minimum_relative_bias'] == model.BIAS_TARGET == 0.0235
    assert targets['maximum_fit_residual'] == 0.004 and targets['minimum_depth_256_polarization'] == 0.005
    assertions.append('Public target, generation and unchanged numeric caps agree.')
    for directory in (ROOT / 'participant', ROOT / 'evaluator'):
        for cache in directory.rglob('__pycache__'):
            shutil.rmtree(cache)
        for pattern in ('*.pyc', '*.pyo'):
            for compiled in directory.rglob(pattern):
                compiled.unlink()
    baseline = model.baseline()
    fixtures = PRIVATE / 'fixtures'
    patch_text(fixtures / 'baseline.json', json.dumps(baseline, indent=2) + '\n')
    generated_path = fixtures / 'runnable_baseline.json'
    generated = subprocess.run([sys.executable, str(ROOT / 'participant' / 'baseline' / 'solve.py'),
                                '--output', str(generated_path)], capture_output=True, text=True, cwd=ROOT)
    assert generated.returncode == 0 and json.loads(generated_path.read_text()) == baseline
    assert json.loads((ROOT / 'participant' / 'input' / 'baseline.json').read_text()) == baseline
    baseline_score = official(generated_path)
    assert baseline_score['admissible'] and not baseline_score['passed']
    assertions.append('Uniform baseline generator, packaged input and exact checker agree; baseline is admissible but nonwinning.')
    winner_path = PRIVATE / 'winning_witness.json'
    winner = model.load_artifact(winner_path)
    public_winner = official(winner_path)
    independent_winner = independent_check(winner)
    assert public_winner['passed'] and independent_winner['passed']
    public_curve = model.exact_curve(model.check_constraints(winner))
    difference = float(np.max(abs(public_curve - np.array(independent_winner['polarizations']))))
    assert difference < 2e-13
    assert abs(public_winner['relative_bias'] - independent_winner['fit']['bias']) < 1e-7
    assert abs(public_winner['max_residual'] - independent_winner['fit']['max_residual']) < 1e-7
    assertions.append('Privileged INTEGER winner passes official and independent tuple/probability-space checkers; all 129 polarizations agree.')
    family_counts = model.check_constraints(winner)
    for eta in (0.2, 0.35, 0.4, 0.65, 0.8):
        weights = np.array([(1 - eta) / 24] * 24 + [eta / 8] * 8)
        assert np.max(abs(weights @ family_counts - weights @ model.BASELINE_COUNTS)) < 1e-13
        products = np.sum(family_counts[model.INVERSE]
                          * np.take_along_axis(family_counts, model.PERMUTATIONS, axis=1), axis=1)
        baseline_products = np.sum(model.BASELINE_COUNTS[model.INVERSE]
                                   * np.take_along_axis(model.BASELINE_COUNTS, model.PERMUTATIONS, axis=1), axis=1)
        assert abs(weights @ products - weights @ baseline_products) < 1e-10
    assertions.append('Native-family calibrations transfer across five sampler mixtures; no off-nominal scoring gate is imposed.')
    previous = official(ROOT / 'champions' / 'generation_2' / 'witness.json')
    assert not previous['admissible'] and 'Family-resolved average-channel' in previous['reason']
    old_counts = model.count_matrix(model.load_artifact(ROOT / 'champions' / 'generation_2' / 'witness.json'))
    assert np.array_equal(model.WEIGHTS @ old_counts, model.BASELINE_MARGINALS)
    old_overlaps = np.sum(old_counts[model.INVERSE] * np.take_along_axis(old_counts, model.PERMUTATIONS, axis=1), axis=1)
    assert int(old_overlaps[:24].sum()) == 28800 and int(old_overlaps[24:].sum()) == 1920
    assert int(np.max(abs(old_counts[:24].sum(axis=0) - model.BASELINE_SINGLE_MARGINALS))) == 26
    assert int(np.max(abs(old_counts[24:].sum(axis=0) - model.BASELINE_CNOT_MARGINALS))) == 13
    assertions.append('Actual v2 champion preserves global mean and both pair calibrations but fails family means by exactly 26/13 counts.')
    isolated = copy.deepcopy(baseline)
    isolated['single'][0][3][0] += 1
    isolated['single'][0][3][1] -= 1
    isolated['single'][0][4][0] -= 1
    isolated['single'][0][4][1] += 1
    isolated['cx'][0][0] += 1
    isolated['cx'][0][4] -= 1
    isolated['cx'][3][3] -= 1
    isolated['cx'][3][4] += 1
    isolated_counts = model.count_matrix(isolated)
    assert np.array_equal(isolated_counts[:24].sum(axis=0), model.BASELINE_SINGLE_MARGINALS)
    assert np.array_equal(isolated_counts[24:].sum(axis=0), model.BASELINE_CNOT_MARGINALS)
    isolated_overlaps = np.sum(isolated_counts[model.INVERSE]
                              * np.take_along_axis(isolated_counts, model.PERMUTATIONS, axis=1), axis=1)
    assert int(model.WEIGHTS @ isolated_overlaps) == 32640
    assert (int(isolated_overlaps[:24].sum()), int(isolated_overlaps[24:].sum())) == (28802, 1919)
    assert not model.evaluate(isolated)['admissible']
    assertions.append('Split-pair guard independently rejects 28802/1919 even when family means and weighted overlap pass.')
    invalid_cases = []
    for name, value in (('boolean', True), ('float', 20.0), ('nan', float('nan')),
                        ('infinity', float('inf')), ('huge_integer', 10 ** 80), ('negative', -1)):
        artifact = copy.deepcopy(baseline)
        artifact['single'][0][0][0] = value
        invalid_cases.append((name, json.dumps(artifact)))
    invalid_cases.extend((('missing_keys', '{}'), ('wrong_shape', '{"single":[],"cx":[]}'),
                          ('duplicate_keys', '{"single":[],"single":[],"cx":[]}'),
                          ('extra_key', json.dumps({**baseline, 'extra': 0})),
                          ('oversized', ' ' * 65537)))
    rejections = []
    for name, content in invalid_cases:
        path = fixtures / (name + '.json')
        patch_text(path, content + '\n')
        result = official(path)
        assert not result['admissible'] and not result['passed'], (name, result)
        rejections.append({'case': name, 'reason': result['reason']})
    symbolic = fixtures / 'symlink.json'
    symbolic.symlink_to(winner_path)
    result = official(symbolic)
    assert not result['admissible'] and 'filesystem reference' in result['reason']
    rejections.append({'case': 'symlink', 'reason': result['reason']})
    symbolic.unlink()
    hardlinked = fixtures / 'hardlink.json'
    os.link(generated_path, hardlinked)
    result = official(hardlinked)
    assert not result['admissible'] and 'filesystem reference' in result['reason']
    rejections.append({'case': 'hardlink', 'reason': result['reason']})
    hardlinked.unlink()
    assertions.append('Official evaluator rejects malformed, noninteger, duplicate-key, oversized, symlink and hardlink submissions.')
    public_check = subprocess.run([sys.executable, str(ROOT / 'participant' / 'workspace' / 'check.py'), str(winner_path)],
                                  capture_output=True, text=True, cwd=ROOT,
                                  env={key: value for key, value in os.environ.items() if key != 'PYTHONDONTWRITEBYTECODE'})
    assert public_check.returncode == 0 and json.loads(public_check.stdout)['passed']
    caches = [str(path.relative_to(ROOT)) for directory in (ROOT / 'participant', ROOT / 'evaluator')
              for path in directory.rglob('__pycache__')]
    assert not caches, caches
    assert not [path for directory in (ROOT / 'participant', ROOT / 'evaluator')
                for pattern in ('*.pyc', '*.pyo') for path in directory.rglob(pattern)]
    assertions.append('Official and public entry points create no public bytecode cache even without the environment override.')
    assert archive_hashes() == preserved
    assertions.append('Generation-one/two champion directories and full snapshots remain byte-for-byte unchanged.')
    result = {'generation': 3, 'passed': True, 'elapsed_seconds': time.perf_counter() - started,
              'assertions': assertions, 'negative_cases': rejections, 'baseline': baseline_score,
              'privileged_witness': public_winner, 'v2_champion': previous,
              'max_independent_full_curve_difference': difference, 'public_bytecode_caches': caches,
              'immutable_archive_file_count': len(preserved), 'immutable_archive_sha256': preserved}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
