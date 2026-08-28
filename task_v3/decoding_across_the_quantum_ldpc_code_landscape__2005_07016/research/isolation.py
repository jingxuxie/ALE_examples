import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import time


def run_submission(submission, participant, input_path, output_suffix='.npz', timeout=120, memory_mb=1536, cpu_limit=None, submission_aliases=()):
    submission = Path(submission).resolve()
    participant = Path(participant).resolve()
    input_path = Path(input_path).resolve()
    with tempfile.TemporaryDirectory(prefix='ale-ldpc-eval-') as temporary:
        output_directory = Path(temporary)
        command = ['bwrap', '--die-with-parent', '--new-session', '--unshare-net', '--unshare-pid', '--unshare-ipc', '--unshare-uts']
        for system_path in ['/usr', '/bin', '/lib', '/lib64', '/etc/alternatives', '/etc/ld.so.cache']:
            if Path(system_path).exists():
                command.extend(['--ro-bind', system_path, system_path])
        command.extend(['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/home', '--bind', str(submission), '/submission', '--ro-bind', str(participant), '/task', '--bind', str(submission), str(submission), '--ro-bind', str(participant), str(participant), '--ro-bind', str(input_path), '/input' + input_path.suffix, '--bind', str(output_directory), '/result', '--chdir', '/submission'])
        for alias in submission_aliases:
            command.extend(['--bind', str(submission), str(Path(alias).resolve())])
        environment = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'PYTHONPATH': '/task/workspace:/submission', 'PYTHONNOUSERSITE': '1', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'MPLCONFIGDIR': '/tmp/mpl', 'LANG': 'C.UTF-8'}
        command.append('--clearenv')
        for name, value in environment.items():
            command.extend(['--setenv', name, value])
        command.extend(['/usr/bin/time', '-f', '{"max_rss_kb":%M,"user_seconds":%U,"system_seconds":%S}', '-o', '/result/usage.json', '/usr/bin/python3', '-s', '/submission/solve.py', '--input', '/input' + input_path.suffix, '--output', '/result/answer' + output_suffix])

        def limits():
            maximum = int(memory_mb * 1024 * 1024)
            resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024 * 1024, 512 * 1024 * 1024))
            if cpu_limit is not None:
                cpu_seconds = max(1, math.ceil(cpu_limit))
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))

        started = time.perf_counter()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, preexec_fn=limits)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        elapsed = time.perf_counter() - started
        result = dict(elapsed_seconds=elapsed, returncode=process.returncode, timeout=timed_out, stdout=stdout[-3000:], stderr=stderr[-3000:])
        usage_file = output_directory / 'usage.json'
        if usage_file.exists():
            try:
                result.update(json.loads(usage_file.read_text().splitlines()[-1]))
            except (ValueError, IndexError):
                pass
        answer = output_directory / ('answer' + output_suffix)
        result['answer_bytes'] = answer.read_bytes() if answer.exists() and not timed_out and process.returncode == 0 else None
        return result
