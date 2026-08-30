import ctypes
import json
import os
import resource
import subprocess
import sys


def main():
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('cannot enable descendant CPU accounting')
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with open('/query/predictor.log', 'w+b') as logfile:
        completed = subprocess.run(['/usr/bin/python3', '/submission/predict.py',
                                    '/query/input.npz', '/query/output.npz'],
                                   stdout=logfile, stderr=subprocess.STDOUT, timeout=90)
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break
        logfile.seek(max(0, logfile.seek(0, os.SEEK_END) - 4000))
        diagnostic = logfile.read().decode(errors='replace')
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    elapsed = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    print(json.dumps({'cpu_seconds': elapsed, 'returncode': completed.returncode,
                      'stderr': diagnostic}))
    return 0 if completed.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
