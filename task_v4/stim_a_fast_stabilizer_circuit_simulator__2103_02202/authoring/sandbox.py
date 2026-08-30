"""Run concept_1 solve.py with one input; the trusted scorer stays outside."""

import argparse
import json
import os
from pathlib import Path
import stat

from isolation import private_directory, run_isolated, validate_tree


def run_file(submission, participant, input_path, timeout=45, memory_mb=2048):
    """Return (answer_dict_or_None, telemetry_dict), without importing submitted code."""
    submission = validate_tree(Path(submission).absolute())
    participant = validate_tree(Path(participant).absolute())
    if not (submission / 'solve.py').is_file():
        raise ValueError('Submission must contain a regular solve.py')
    if not 0 < timeout <= 3600 or not 64 <= memory_mb <= 65536:
        raise ValueError('Invalid time or memory limit')
    input_path = Path(input_path).absolute()
    if input_path.is_symlink() or not input_path.is_file():
        raise ValueError('Input must be a regular file')
    with private_directory('evaluation_') as directory:
        staging = Path(directory)
        current = staging / 'input.json'
        descriptor = os.open(input_path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16 * 1024**2:
                raise ValueError('Input is not a bounded regular file')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                current.write_bytes(stream.read(16 * 1024**2 + 1))
        finally:
            os.close(descriptor)
        scratch = staging / 'scratch'
        scratch.mkdir()
        mounts = [{'source': str(participant), 'target': '/task', 'readonly': True},
                  {'source': str(submission), 'target': '/submission', 'readonly': True},
                  {'source': str(current), 'target': '/input/instance.json', 'readonly': True},
                  {'source': str(scratch), 'target': '/work', 'readonly': False},
                  {'source': str(scratch), 'target': '/tmp', 'readonly': False}]
        for path in dict.fromkeys((participant, submission)):
            mounts.append({'source': str(path), 'target': str(path), 'readonly': True})
        environment = {'PATH': '/usr/bin:/bin', 'HOME': '/work', 'TMPDIR': '/work',
                       'LANG': 'C.UTF-8', 'PYTHONPATH': '/task/workspace:/submission',
                       'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                       'PYTHONHASHSEED': '0', 'OPENBLAS_NUM_THREADS': '1',
                       'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                       'NUMBA_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}
        spec = {'mounts': mounts, 'cwd': '/work', 'evaluation': True,
                'memory_mb': memory_mb, 'timeout': timeout,
                'command': ['/usr/bin/python3', '-B', str(submission / 'solve.py'),
                            '--input', '/input/instance.json', '--output', '/work/answer.json']}
        telemetry = run_isolated(spec, environment=environment, timeout=timeout)
        telemetry.update(memory_mb=memory_mb, cpu_count=1, current_input_only=True)
        answer = None
        if (telemetry['returncode'] == 0 and not telemetry['timed_out']
                and not telemetry['output_limited'] and not telemetry.get('infrastructure_error')):
            try:
                descriptor = os.open(scratch / 'answer.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                try:
                    metadata = os.fstat(descriptor)
                    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > 8 * 1024**2:
                        raise ValueError('Answer must be a bounded, non-linked regular file')
                    with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                        answer = json.loads(stream.read(8 * 1024**2 + 1))
                    if not isinstance(answer, dict):
                        raise ValueError('Answer must be a JSON object')
                finally:
                    os.close(descriptor)
            except (OSError, ValueError) as error:
                answer = None
                telemetry['answer_error'] = str(error)
        return answer, telemetry


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submission', required=True, type=Path)
    parser.add_argument('--participant', required=True, type=Path)
    parser.add_argument('--input', required=True, type=Path, dest='input_path')
    parser.add_argument('--timeout', default=45, type=float)
    parser.add_argument('--memory-mb', default=2048, type=int)
    arguments = parser.parse_args()
    answer, telemetry = run_file(**vars(arguments))
    print(json.dumps({'answer': answer, 'telemetry': telemetry}, indent=2))
    raise SystemExit(0 if answer is not None else 1)
