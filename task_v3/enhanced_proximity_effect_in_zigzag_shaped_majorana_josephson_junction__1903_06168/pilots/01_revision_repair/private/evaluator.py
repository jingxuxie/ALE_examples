import argparse
import json
import math
import os
from pathlib import Path
import resource
import signal
import statistics
import subprocess
import sys
import tempfile
import time


PILOT = Path(__file__).resolve().parent.parent


def reject_constant(value):
    raise ValueError('Nonfinite JSON constant: ' + value)


def read_json(path):
    return json.loads(path.read_text(), parse_constant=reject_constant)


def values(result, request):
    if not isinstance(result, dict) or type(result.get('version')) is not int or result['version'] != 1:
        raise ValueError('Result must be a version-1 object')
    if request['kind'] == 'barrier':
        output = result.get('response')
        if not isinstance(output, list) or len(output) != len(request['probes']):
            raise ValueError('Wrong response shape')
    else:
        output = [result.get('gap')]
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in output):
        raise ValueError('Core values must be finite numbers')
    return output


def score_result(result, expected, request, weak_rmse, factor=99.0):
    predicted_values = values(result, request)
    expected_values = values(expected, request)
    differences = [actual - target for actual, target in zip(predicted_values, expected_values)]
    normalization = math.sqrt(len(differences))
    error = math.hypot(*(difference / normalization for difference in differences))
    relative = error / weak_rmse
    score = 0.0 if relative > 1e150 else 1.0 / (1.0 + factor * relative * relative)
    return score, error


def run_case(submission, request, timeout, memory_mib):
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                       MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
                       PYTHONDONTWRITEBYTECODE='1')

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (memory_mib * 1024 ** 2,) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 ** 2,) * 2)

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='.evaluation-', dir=Path(__file__).resolve().parent) as temporary:
        directory = Path(temporary)
        request_path = directory / 'request.json'
        output_path = directory / 'result.json'
        request_path.write_text(json.dumps(request, allow_nan=False))
        with (directory / 'stdout.txt').open('w') as stdout, (directory / 'stderr.txt').open('w') as stderr:
            process = subprocess.Popen(
                [sys.executable, str(submission), '--input', str(request_path), '--output', str(output_path)],
                cwd=PILOT, env=environment, stdout=stdout, stderr=stderr,
                preexec_fn=limits, start_new_session=True
            )
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return None, time.perf_counter() - started, 'timeout', 'Exceeded wall-time limit'
        seconds = time.perf_counter() - started
        if process.returncode:
            message = (directory / 'stderr.txt').read_text(errors='replace')[-1800:]
            return None, seconds, 'execution_error', message
        try:
            if output_path.stat().st_size > 2 * 1024 ** 2:
                raise ValueError('Result exceeds 2 MiB')
            result = read_json(output_path)
        except (OSError, ValueError, OverflowError) as error:
            return None, seconds, 'protocol_error', str(error)
        return result, seconds, 'ok', ''


def evaluate(submission, pool):
    manifest = read_json(pool / 'manifest.json')
    rows = []
    for case in manifest['cases']:
        request = read_json(pool / case['request'])
        expected = read_json(pool / case['expected'])
        result, seconds, status, diagnostic = run_case(
            submission, request, manifest['timeout_seconds'], manifest['memory_mib']
        )
        row = dict(name=case['name'], family=case['family'], score=0.0,
                   runtime_seconds=seconds, status=status)
        if status == 'ok':
            try:
                row['score'], row['rmse'] = score_result(
                    result, expected, request, case['weak_rmse'], manifest['score_factor']
                )
            except (ValueError, TypeError, OverflowError) as error:
                row['status'] = 'protocol_error'
                diagnostic = str(error)
        if diagnostic:
            row['diagnostic'] = diagnostic
        rows.append(row)
    families = {}
    for family in sorted({row['family'] for row in rows}):
        members = [row for row in rows if row['family'] == family]
        families[family] = dict(score=statistics.mean(row['score'] for row in members),
                                completed=sum(row['status'] == 'ok' for row in members),
                                cases=len(members),
                                runtime_seconds=sum(row['runtime_seconds'] for row in members))
    return dict(
        version=1, submission=str(submission),
        mean_core_score=statistics.mean(family['score'] for family in families.values()),
        worst_family_score=min(family['score'] for family in families.values()),
        completed=sum(row['status'] == 'ok' for row in rows), cases=len(rows),
        runtime_seconds=sum(row['runtime_seconds'] for row in rows),
        families=families, results=rows,
        interpretation='Pilot correctness check; execution/protocol failures are not evidence of substantive difficulty.'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, required=True)
    parser.add_argument('--pool', type=Path, default=Path(__file__).resolve().parent / 'challenge_pool')
    parser.add_argument('--report', type=Path)
    arguments = parser.parse_args()
    submission = arguments.submission.resolve()
    if not submission.is_file():
        parser.error('Submission script does not exist')
    report = evaluate(submission, arguments.pool.resolve())
    if arguments.report:
        destination = arguments.report.resolve()
        if not destination.is_relative_to(PILOT):
            parser.error('Author reports must stay inside this pilot')
        sys.path.insert(0, str(PILOT / 'private/reference'))
        from author_tools import store_json
        store_json(str(destination.relative_to(PILOT)), report)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
