import argparse
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research'))
from isolation import run_submission
import numpy as np
import scipy.sparse as sparse

PILOT = Path(__file__).resolve().parents[1]


def matrix(case, prefix):
    return sparse.coo_matrix((np.ones(len(case[prefix + '_rows']), dtype=np.uint8), (case[prefix + '_rows'], case[prefix + '_cols'])), shape=tuple(case[prefix + '_shape'])).tocsr()


def measure(corrections, case, reference):
    expected = (len(case['syndromes']), int(case['h_shape'][1]))
    if corrections.shape != expected or not np.all((corrections == 0) | (corrections == 1)):
        raise ValueError('corrections must be binary with shape ' + str(expected))
    corrections = corrections.astype(np.uint8)
    parity = matrix(case, 'h')
    logical = matrix(reference, 'logical')
    validity = np.all(((parity @ corrections.T).T % 2) == case['syndromes'], axis=1)
    logical_success = np.all(((logical @ corrections.T).T % 2) == reference['truth'], axis=1)
    return float(np.mean(validity & logical_success)), float(validity.mean()), (validity & logical_success).astype(int).tolist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission')
    parser.add_argument('--report', required=True)
    parser.add_argument('--split', default='pilot')
    parser.add_argument('--reference', action='store_true')
    parser.add_argument('--weak', action='store_true')
    parser.add_argument('--save-predictions', type=Path)
    arguments = parser.parse_args()
    manifest = json.loads((PILOT / 'private/reference' / (arguments.split + '_manifest.json')).read_text())
    results = []
    for metadata in manifest:
        case_path = PILOT / 'private/challenge_pool' / arguments.split / (metadata['name'] + '.npz')
        case = dict(np.load(case_path, allow_pickle=False))
        reference = dict(np.load(PILOT / 'private/reference' / (metadata['name'] + '.npz'), allow_pickle=False))
        case['budget_seconds'] = np.array(metadata['budget_seconds'])
        weak_accuracy, _, _ = measure(reference['weak'], case, reference)
        reference_accuracy, _, _ = measure(reference['reference'], case, reference)
        if not np.isclose(reference_accuracy, metadata['reference_accuracy']) or not np.isclose(weak_accuracy, metadata['weak_accuracy']):
            raise ValueError('Stored reference audit does not match the generation manifest')
        result = dict(metadata)
        if arguments.reference or arguments.weak:
            label = 'reference' if arguments.reference else 'weak'
            corrections = reference[label]
            runtime = dict(elapsed_seconds=metadata[label + '_seconds'], returncode=0, timeout=False)
        else:
            with tempfile.TemporaryDirectory(prefix='ale-local-case-') as temporary:
                sanitized = Path(temporary) / 'case.npz'
                np.savez_compressed(sanitized, **case)
                runtime = run_submission(arguments.submission, PILOT / 'participant', sanitized, timeout=max(60, 3 * metadata['budget_seconds']), memory_mb=metadata['memory_mb'])
            answer = runtime.pop('answer_bytes')
            if answer and arguments.save_predictions:
                arguments.save_predictions.mkdir(parents=True, exist_ok=True)
                (arguments.save_predictions / (metadata['name'] + '.npz')).write_bytes(answer)
            try:
                corrections = np.load(io.BytesIO(answer), allow_pickle=False)['corrections'] if answer else None
            except Exception as error:
                corrections = None
                runtime['format_error'] = str(error)
        try:
            accuracy, valid, successes = measure(corrections, case, reference) if corrections is not None else (0.0, 0.0, [])
        except Exception as error:
            accuracy, valid, successes = 0.0, 0.0, []
            runtime['format_error'] = str(error)
        gap = reference_accuracy - weak_accuracy
        informative = gap > 0.01
        quality = (accuracy - weak_accuracy) / gap if informative else None
        clock_seconds = runtime.get('user_seconds', runtime['elapsed_seconds']) + runtime.get('system_seconds', 0)
        runtime['scored_cpu_seconds'] = clock_seconds
        latency = (1 + metadata['reference_seconds'] / metadata['budget_seconds']) / (1 + clock_seconds / metadata['budget_seconds'])
        score = quality * latency if informative and corrections is not None else 0.0
        if clock_seconds > metadata['budget_seconds']:
            score = 0.0
            runtime['cpu_budget_exceeded'] = True
        result.update(runtime)
        result.update(accuracy=accuracy, syndrome_validity=valid, quality_score=quality, latency_factor=latency, core_score=score, informative=informative, shot_success=successes)
        results.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != 'shot_success'}), flush=True)
    scored = [result for result in results if result['informative']]
    report = dict(split=arguments.split, submission='reference' if arguments.reference else ('weak' if arguments.weak else arguments.submission), mean_core=float(np.mean([result['core_score'] for result in scored])) if scored else None, worst_family=min((result['core_score'] for result in scored), default=None), reference_pass=all(result['reference_valid'] == 1 for result in results), cases=results)
    Path(arguments.report).parent.mkdir(parents=True, exist_ok=True)
    Path(arguments.report).write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}), flush=True)


if __name__ == '__main__':
    main()
