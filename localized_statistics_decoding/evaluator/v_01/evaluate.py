import argparse
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent


def ramp(error, good, bad):
    if not math.isfinite(error):
        return 0.0
    return min(1.0, max(0.0, (bad - error) / (bad - good)))


def distribution_error(predicted, expected):
    if not isinstance(predicted, list) or len(predicted) != len(expected):
        return math.inf
    if any(not isinstance(value, (int, float)) or not math.isfinite(value)
           or value < -1e-7 or value > 1.0000001 for value in predicted):
        return math.inf
    if abs(sum(predicted) - 1.0) > 0.005:
        return math.inf
    return sum(abs(left - right) for left, right in zip(predicted, expected)) / 2


def finite_error(predicted, expected, probability=False):
    if not isinstance(predicted, (int, float)) or not math.isfinite(predicted):
        return math.inf
    if probability and not 0.0 <= predicted <= 1.0:
        return math.inf
    return abs(predicted - expected)


def grade_case(predicted, expected):
    predicted = predicted if isinstance(predicted, dict) else {}
    log_error = finite_error(predicted.get('log_evidence'), expected['log_evidence'])
    mode_error = distribution_error(predicted.get('mode_posterior'), expected['mode_posterior'])
    shot_list = predicted.get('shots', [])
    by_id = {shot.get('id'): shot for shot in shot_list if isinstance(shot, dict)} if isinstance(shot_list, list) else {}
    logical_grades = []
    query_grades = []
    decisions = []
    logical_errors = []
    query_errors = []
    for shot in expected['shots']:
        candidate = by_id.get(shot['id'], {})
        error = distribution_error(candidate.get('logical_posterior'), shot['logical_posterior'])
        logical_errors.append(error)
        logical_grades.append(ramp(error, 0.02, 0.15))
        decision = candidate.get('logical_decision')
        if type(decision) is int and 0 <= decision < len(shot['logical_posterior']):
            regret = max(shot['logical_posterior']) - shot['logical_posterior'][decision]
            decisions.append(ramp(regret, 0.02, 0.15))
        else:
            decisions.append(0.0)
        query_predictions = candidate.get('query_probability', {})
        if not isinstance(query_predictions, dict):
            query_predictions = {}
        for query_id, truth in shot['query_probability'].items():
            error = finite_error(query_predictions.get(query_id), truth, probability=True)
            query_errors.append(error)
            query_grades.append(ramp(error, 0.025, 0.15))
    components = {'joint_logical': sum(logical_grades) / len(logical_grades),
                  'query_parity': sum(query_grades) / len(query_grades),
                  'log_evidence': ramp(log_error, 0.08, 2.0),
                  'mode_posterior': ramp(mode_error, 0.02, 0.15),
                  'logical_decision': sum(decisions) / len(decisions)}
    score = (0.4 * components['joint_logical'] + 0.25 * components['query_parity']
             + 0.2 * components['log_evidence'] + 0.1 * components['mode_posterior']
             + 0.05 * components['logical_decision'])

    def rounded(error):
        return round(error, 8) if math.isfinite(error) else None

    return score, {'components': {name: round(value, 6) for name, value in components.items()},
                   'logical_tv': [rounded(value) for value in logical_errors],
                   'query_abs_mean': rounded(sum(query_errors) / len(query_errors)),
                   'log_evidence_abs': rounded(log_error), 'mode_tv': rounded(mode_error)}


def restrict_resources():
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (65, 65))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def evaluate(submission):
    if not (submission / 'solve.py').is_file():
        return {'passed': False, 'score': 0.0, 'reason': 'Missing executable solve.py', 'cases': []}
    environment = dict(os.environ)
    environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                       NUMEXPR_NUM_THREADS='1', PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
    results = []
    scores = []
    for input_path in sorted((HERE / 'hidden').glob('case_*.json')):
        if input_path.name.endswith('_expected.json'):
            continue
        expected_path = input_path.with_name(input_path.stem + '_expected.json')
        expected = json.loads(expected_path.read_text())['cases'][0]
        started = time.monotonic()
        timed_out = False
        error_message = ''
        candidate = {}
        with tempfile.TemporaryDirectory(prefix='detector-evaluation-') as temporary:
            temporary = Path(temporary)
            public_input = temporary / 'batch.json'
            public_output = temporary / 'prediction.json'
            public_input.write_bytes(input_path.read_bytes())
            try:
                process = subprocess.run([sys.executable, str(submission / 'solve.py'),
                                          '--input', str(public_input), '--output', str(public_output)],
                                         cwd=submission, env=environment, capture_output=True,
                                         timeout=60, preexec_fn=restrict_resources)
                if process.returncode:
                    error_message = f'process_exit={process.returncode}: ' + process.stderr.decode(errors='replace')[-1000:]
            except subprocess.TimeoutExpired:
                timed_out = True
                error_message = '60-second inference timeout'
            except Exception as error:
                error_message = f'{type(error).__name__}: {error}'
            try:
                if public_output.is_file() and public_output.stat().st_size <= 8 * 1024 * 1024:
                    candidates = json.loads(public_output.read_text())['cases']
                    candidate = next((entry for entry in candidates if entry.get('id') == expected['id']), {})
            except Exception as error:
                error_message += f'; invalid output: {type(error).__name__}: {error}'
        score, metrics = grade_case(candidate, expected)
        if timed_out:
            score = 0.0
        scores.append(score)
        results.append({'id': expected['id'], 'score': round(score, 6), 'timed_out': timed_out,
                        'seconds': round(time.monotonic() - started, 3), 'error': error_message, **metrics})
    artifacts = {'diagnosis': (submission / 'diagnosis.md').is_file(), 'validation': False}
    try:
        expected_public = json.loads((HERE / 'hidden/public_expected.json').read_text())['cases']
        predicted_public = json.loads((submission / 'validation_predictions.json').read_text())['cases']
        by_id = {case['id']: case for case in predicted_public}
        public_scores = [grade_case(by_id.get(case['id'], {}), case)[0] for case in expected_public]
        artifacts['validation'] = min(public_scores) >= 0.9
    except Exception:
        pass
    core = sum(scores) / len(scores)
    passed = core >= 0.95 and min(scores) >= 0.9 and all(artifacts.values())
    failures = [result['id'] for result in results if result['score'] < 0.9]
    reason = 'Scientific inference and deliverables pass' if passed else (
        'Core shortfall: ' + ', '.join(failures) if failures else 'Missing or inaccurate validation deliverables')
    return {'passed': passed, 'score': round(core, 6), 'reason': reason,
            'cases': results, 'artifacts': artifacts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', required=True)
    arguments = parser.parse_args()
    try:
        result = evaluate(Path(arguments.submission).resolve())
    except Exception as error:
        result = {'passed': False, 'score': 0.0, 'reason': f'Evaluator error: {type(error).__name__}: {error}'}
    print(json.dumps(result, allow_nan=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
