import base64
import ctypes
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time


def deadline(signum, frame):
    raise TimeoutError('execution_failure: native process or descendant exceeded wall limit')


def supervise(payload):
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('environment_error: subreaper setup failed')
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError('environment_error: nondumpable supervisor setup failed')
    with tempfile.TemporaryFile() as inputs, tempfile.TemporaryFile() as outputs, tempfile.TemporaryFile() as errors:
        inputs.write(payload)
        inputs.seek(0)
        signal.signal(signal.SIGALRM, deadline)
        signal.alarm(38)
        started = time.monotonic()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        process = subprocess.Popen(['/work/runner'], stdin=inputs, stdout=outputs, stderr=errors, close_fds=True)
        returncode = process.wait()
        descendants = 0
        descendant_failures = []
        while True:
            try:
                child, status = os.waitpid(-1, 0)
                descendants += 1
                if os.waitstatus_to_exitcode(status) != 0:
                    descendant_failures.append(os.waitstatus_to_exitcode(status))
            except InterruptedError:
                continue
            except ChildProcessError:
                break
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        elapsed = time.monotonic() - started
        signal.alarm(0)
        outputs.seek(0)
        errors.seek(0)
        stdout = outputs.read(4 * 1024**2 + 1)
        stderr = errors.read(4096).decode('utf-8', errors='replace')
        if len(stdout) > 4 * 1024**2:
            raise ValueError('execution_failure: native stdout exceeds release limit')
        user = after.ru_utime - before.ru_utime
        system = after.ru_stime - before.ru_stime
        return {'returncode': returncode, 'cpu_seconds': user + system,
                'user_seconds': user, 'system_seconds': system,
                'full_child_cpu_seconds': user + system, 'trusted_setup_cpu_seconds': 0.0,
                'wall_seconds': elapsed, 'adopted_descendants': descendants,
                'cpu_affinity': sorted(os.sched_getaffinity(0)),
                'descendant_failures': descendant_failures,
                'minor_faults': after.ru_minflt - before.ru_minflt,
                'major_faults': after.ru_majflt - before.ru_majflt,
                'accounting': 'in-namespace RUSAGE_CHILDREN: full native startup, work, I/O and reaped descendants',
                'stdout_b64': base64.b64encode(stdout).decode('ascii'), 'stderr': stderr}


def main():
    try:
        payload = sys.stdin.buffer.read(4 * 1024**2 + 1)
        if len(payload) > 4 * 1024**2:
            raise ValueError('execution_failure: oversized native input')
        result = supervise(payload)
    except Exception as error:
        result = {'wrapper_error': type(error).__name__ + ': ' + str(error)}
    print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
