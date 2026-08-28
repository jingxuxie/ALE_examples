import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time


def run_submission(submission, case, output, participant, timeout=180, memory_gib=1.5):
    submission = Path(submission).resolve()
    case = Path(case).resolve()
    output = Path(output).resolve()
    participant = Path(participant).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = output.parent / (output.name + '.resources')
    command = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session']
    for folder in ('/usr', '/bin', '/lib', '/lib64'):
        if Path(folder).exists():
            command.extend(['--ro-bind', folder, folder])
    if Path('/etc/ld.so.cache').exists():
        command.extend(['--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache'])
    command.extend(['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp'])
    for folder in (submission, participant):
        command.extend(['--ro-bind', str(folder), str(folder)])
    command.extend(['--ro-bind', str(case), str(case), '--bind', str(output.parent), str(output.parent),
        '--chdir', str(submission), '--', '/usr/bin/time', '-f', '%e %M', '-o', str(metrics),
        sys.executable, str(submission / 'solve.py'), str(case), str(output)])
    environment = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C.UTF-8',
        'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPATH': str(participant / 'workspace' / 'vendor') + ':' + str(participant / 'workspace'),
        'NUMBA_CACHE_DIR': '/tmp/numba', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1', 'NUMBA_NUM_THREADS': '1', 'MALLOC_ARENA_MAX': '2'}

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (int(memory_gib * 2 ** 30),) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 2, int(timeout) + 3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 2 ** 20,) * 2)
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))

    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=environment, preexec_fn=limits, start_new_session=True, text=True)
    expired = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    result = dict(returncode=process.returncode, elapsed=time.monotonic() - started,
        timeout=expired, stdout=stdout[-16000:], stderr=stderr[-16000:], isolation='bubblewrap-unshare-all')
    if metrics.exists():
        try:
            seconds, peak_kib = metrics.read_text().strip().splitlines()[-1].split()
            result.update(compute_seconds=float(seconds), peak_rss_kib=int(peak_kib))
        except (ValueError, IndexError):
            pass
    return result
