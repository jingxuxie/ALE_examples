import argparse
import hashlib
import json
import math
import pathlib
import sys
import tempfile
import time
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'authoring'))
from isolated import run_submission
from metrics import errors, scores

WALL_TIMEOUT_SECONDS = 90
COMMAND_LIMIT_SECONDS = 20


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(submission, split):
    submission = pathlib.Path(submission).resolve()
    if not (submission / 'solve.py').is_file():
        raise ValueError('Submission must contain solve.py')
    for path in submission.rglob('*'):
        if path.is_symlink():
            raise ValueError('Submission symlinks are not allowed')
    manifest_path = ROOT / 'private/challenge_pool/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    calibration_path = ROOT / 'private/challenge_pool/calibration.json'
    if checksum(calibration_path) != manifest['calibration_sha256']:
        raise ValueError('Frozen calibration integrity check failed')
    calibration = json.loads(calibration_path.read_text())
    results = []
    started = time.monotonic()
    for entry in manifest['splits'][split]:
        case_path = ROOT / 'private/challenge_pool' / entry['case']
        reference_path = ROOT / 'private/challenge_pool' / entry['expected']
        if checksum(case_path) != entry['case_sha256'] or checksum(reference_path) != entry['expected_sha256']:
            raise ValueError('Frozen case integrity check failed: '+entry['id'])
        expected = dict(np.load(reference_path, allow_pickle=False))
        row = {'id': entry['id'], 'family': entry['family'], 'score': 0.0, 'valid': False}
        with tempfile.TemporaryDirectory(prefix='transport-eval-') as scratch:
            output_path = pathlib.Path(scratch) / 'result.json'
            execution = run_submission(submission, case_path, output_path, ROOT / 'participant', timeout=WALL_TIMEOUT_SECONDS, memory_gib=1.0)
            row.update({key: execution[key] for key in ['returncode', 'elapsed', 'timeout', 'isolation', 'compute_seconds', 'peak_rss_kib'] if key in execution})
            command_seconds = execution.get('compute_seconds')
            timing_valid = isinstance(command_seconds, (int, float)) and math.isfinite(command_seconds) and 0.0 <= command_seconds <= COMMAND_LIMIT_SECONDS
            if execution['returncode'] == 0 and not timing_valid:
                row['error'] = 'Missing or invalid command timing, or in-sandbox command elapsed time exceeds 20 seconds'
            elif execution['returncode'] == 0 and not execution.get('timeout', False) and output_path.is_file():
                try:
                    if output_path.stat().st_size > 64*1024*1024:
                        raise ValueError('Output exceeds 64 MiB')
                    predicted = json.loads(output_path.read_text())
                    error = errors(predicted, expected)
                    group_scores = scores(error, calibration[entry['family']])
                    row.update(valid=True, errors=error, group_scores=group_scores, score=float(np.mean(list(group_scores.values()))))
                except (ValueError, KeyError, TypeError, OverflowError, OSError) as problem:
                    row['error'] = str(problem)[:1000]
            else:
                row['error'] = execution.get('stderr', '')[-1500:]
            results.append(row)
    families = {}
    for family in sorted({row['family'] for row in results}):
        selected = [row for row in results if row['family'] == family]
        families[family] = {'score': float(np.mean([row['score'] for row in selected])), 'valid': sum(row['valid'] for row in selected), 'cases': len(selected), 'elapsed': sum(row.get('elapsed', 0.0) for row in selected)}
    mean_score = float(np.mean([value['score'] for value in families.values()]))
    worst_score = min(value['score'] for value in families.values())
    return {'split': split, 'score': 0.5*(mean_score+worst_score), 'mean_family_score': mean_score, 'worst_family_score': worst_score, 'families': families, 'elapsed_total': time.monotonic()-started, 'submission_elapsed_total': sum(row.get('elapsed', 0.0) for row in results), 'peak_rss_kib': max([row.get('peak_rss_kib', 0) for row in results] or [0]), 'limits': {'parent_wall_seconds': WALL_TIMEOUT_SECONDS, 'command_elapsed_seconds': COMMAND_LIMIT_SECONDS, 'address_space_gib': 1.0}, 'strict_isolation': True, 'harness': str(ROOT.parents[1]/'authoring/isolated.py'), 'manifest_sha256': checksum(manifest_path), 'calibration': 'exp(-ln(2)*relative_RMS_error/frozen_initial_family_weak_error), four equal groups', 'cases': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--split', choices=['initial', 'challenge', 'confirmation'], default='initial')
    arguments = parser.parse_args()
    result = evaluate(arguments.submission, arguments.split)
    destination = pathlib.Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: result[key] for key in ['split', 'score', 'mean_family_score', 'worst_family_score', 'submission_elapsed_total']}))


if __name__ == '__main__':
    main()
