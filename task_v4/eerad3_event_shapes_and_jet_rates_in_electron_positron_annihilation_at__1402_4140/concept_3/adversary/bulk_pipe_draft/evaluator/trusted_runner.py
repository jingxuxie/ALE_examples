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
    raise TimeoutError('native executable or adopted descendant exceeded wrapper deadline')


def main():
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('cannot enable descendant CPU accounting')
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError('cannot protect trusted wrapper process')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(55)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        completed = subprocess.run(['/work/runner'], stdout=output, stderr=errors, timeout=54)
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        user_seconds = after.ru_utime - before.ru_utime
        system_seconds = after.ru_stime - before.ru_stime
        duration = user_seconds + system_seconds
        wall_seconds = time.monotonic() - started
        output.seek(0)
        stdout = output.read(32 * 1024**2 + 1)
        if len(stdout) > 32 * 1024**2:
            raise ValueError('native output exceeds bounded log limit')
        errors.seek(max(0, errors.seek(0, os.SEEK_END) - 4000))
        stderr = errors.read().decode(errors='replace')
    signal.alarm(0)
    print(json.dumps({'cpu_seconds': duration, 'user_seconds': user_seconds, 'system_seconds': system_seconds,
                      'wall_seconds': wall_seconds, 'returncode': completed.returncode,
                      'stdout_b64': base64.b64encode(stdout).decode('ascii'), 'stderr': stderr}, allow_nan=False))
    return 0 if completed.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
