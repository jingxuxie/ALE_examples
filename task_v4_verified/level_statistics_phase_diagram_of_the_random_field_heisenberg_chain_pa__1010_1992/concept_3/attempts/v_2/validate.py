import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[variable] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse
import json
from pathlib import Path
import resource
import signal
import sys
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', type=Path)
    parser.add_argument('--output', type=Path, default=Path('validation.json'))
    arguments = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    signal.alarm(180)
    started = time.monotonic()
    participant = Path(__file__).resolve().parents[2] / 'participant'
    sys.path.insert(0, str(participant / 'workspace'))
    from exact import assess
    witness = json.loads(arguments.witness.read_text())
    protocol = json.loads((participant / 'input/protocol.json').read_text())
    report = assess(witness, protocol)
    report['resource'] = {'wall_seconds': time.monotonic()-started,
                          'maximum_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          'address_space_limit_bytes': 2*1024**3,
                          'workers': 1, 'blas_threads': 1}
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: report[key] for key in ('valid','pass','reason','core','worst_family','families','resource')}, indent=2))
    signal.alarm(0)
    if not report['pass']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
