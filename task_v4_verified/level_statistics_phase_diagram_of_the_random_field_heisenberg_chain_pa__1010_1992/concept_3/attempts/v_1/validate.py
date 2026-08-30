import argparse
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
sys.dont_write_bytecode = True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', type=Path)
    parser.add_argument('--output', type=Path, default=Path('validation.json'))
    parser.add_argument('--driver', choices=['evr', 'evd'], default='evr')
    args = parser.parse_args()
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    signal.alarm(180)
    from search import PROTOCOL, assess
    witness = json.loads(args.witness.read_text())
    report = assess(witness, PROTOCOL, driver=args.driver)
    report['resource'] = dict(wall_seconds=time.monotonic() - started,
                              peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                              workers=1, blas_threads=1, address_space_limit_bytes=2 * 1024 ** 3)
    report['validation_source'] = 'supplied public exact.py helper'
    report['driver'] = args.driver
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key:report[key] for key in ('valid', 'pass', 'reason', 'core', 'worst_family', 'checks', 'constraints', 'families', 'resource')}, indent=2))
    signal.alarm(0)
    return 0 if report['pass'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
