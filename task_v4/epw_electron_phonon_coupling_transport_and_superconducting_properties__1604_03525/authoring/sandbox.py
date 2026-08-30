import math
import os
from pathlib import Path
import signal
import subprocess
import time


def run_submission(submission_dir, input_path, output_dir, timeout=120, output_name='result.npz', memory_mb=4096):
    submission = Path(submission_dir).resolve()
    input_path = Path(input_path).resolve()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not (submission / 'solve.py').is_file():
        raise ValueError('submission must contain solve.py')
    if any(path.is_symlink() for path in submission.rglob('*')):
        raise ValueError('submission symlinks are not permitted')
    if not input_path.is_file() or Path(output_name).name != output_name:
        raise ValueError('input must be a file and output_name a basename')
    command = ['/usr/bin/bwrap', '--die-with-parent', '--new-session', '--unshare-all']
    for directory in ['/usr', '/lib', '/lib64', '/bin']:
        if Path(directory).exists():
            command += ['--ro-bind', directory, directory]
    for path in ['/etc/ld.so.cache', '/etc/alternatives', '/etc/localtime']:
        if Path(path).exists():
            command += ['--ro-bind', path, path]
    command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                '--ro-bind', str(submission), '/submission',
                '--ro-bind', str(input_path), '/input.npz',
                '--bind', str(output), '/output', '--chdir', '/submission',
                '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                '--setenv', 'HOME', '/tmp', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
                '--setenv', 'OPENBLAS_NUM_THREADS', '4', '--setenv', 'OMP_NUM_THREADS', '4',
                '--setenv', 'OMP_THREAD_LIMIT', '4', '--setenv', 'MKL_NUM_THREADS', '4',
                '--setenv', 'NUMEXPR_NUM_THREADS', '4',
                '--', '/usr/bin/prlimit', f'--as={memory_mb * 1024 ** 2}',
                f'--cpu={math.ceil(timeout) * 4 + 4}', '--fsize=67108864', '--nofile=128',
                '--', '/usr/bin/python3', '/submission/solve.py', '--input', '/input.npz',
                '--output', f'/output/{output_name}']
    start = time.monotonic()
    timed_out = False
    stdout_path = output / '_stdout.log'
    stderr_path = output / '_stderr.log'
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait(timeout=10)
    return {'returncode': returncode, 'timed_out': timed_out,
            'elapsed_seconds': time.monotonic() - start,
            'stdout': stdout_path.read_text(errors='replace')[-12000:],
            'stderr': stderr_path.read_text(errors='replace')[-12000:],
            'memory_limit_mb': memory_mb, 'numerical_thread_limit': 4,
            'isolation': 'bubblewrap allowlisted mounts, new network and PID namespaces'}
