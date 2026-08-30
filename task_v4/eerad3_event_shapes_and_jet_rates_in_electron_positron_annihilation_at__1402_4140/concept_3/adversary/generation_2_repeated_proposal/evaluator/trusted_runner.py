import ctypes
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile


def deadline(signum, frame):
    raise TimeoutError('native executable or adopted descendant exceeded wrapper deadline')


def main():
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('cannot enable descendant CPU accounting')
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError('cannot protect trusted wrapper process')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(37)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        completed = subprocess.run(['/work/runner'], stdout=output, stderr=errors, timeout=36)
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        duration = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        output.seek(0)
        stdout = output.read(32 * 1024**2 + 1)
        if len(stdout) > 32 * 1024**2:
            raise ValueError('native output exceeds bounded log limit')
        errors.seek(max(0, errors.seek(0, os.SEEK_END) - 4000))
        stderr = errors.read().decode(errors='replace')
    signal.alarm(0)
    print(json.dumps({'cpu_seconds': duration, 'returncode': completed.returncode,
                      'stdout': stdout.decode(errors='replace'), 'stderr': stderr}, allow_nan=False))
    return 0 if completed.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
