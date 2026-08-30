import json
import resource
import subprocess
import sys


def main():
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    completed = subprocess.run(['/usr/bin/python3', '/submission/predict.py',
                                '/query/input.npz', '/query/output.npz'],
                               capture_output=True, timeout=90)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    elapsed = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    print(json.dumps({'cpu_seconds': elapsed, 'returncode': completed.returncode,
                      'stderr': completed.stderr.decode(errors='replace')[-4000:]}))
    return 0 if completed.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
