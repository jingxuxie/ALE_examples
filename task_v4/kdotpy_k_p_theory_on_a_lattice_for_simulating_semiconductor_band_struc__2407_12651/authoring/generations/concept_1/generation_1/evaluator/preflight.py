import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'evaluator'))
from isolation import replay

PROBE = '''import argparse
import json
import os
import socket
from pathlib import Path
import numpy as np
import scipy.linalg

parser = argparse.ArgumentParser()
parser.add_argument('--input')
parser.add_argument('--output')
arguments = parser.parse_args()
directory = Path(arguments.input)
configuration = json.loads((directory / 'probe.json').read_text())
def denied(path, mode='r'):
    try:
        with open(path, mode) as stream:
            if mode == 'r':
                stream.read(1)
        return False
    except OSError:
        return True
results = {'numpy_scipy_work': bool(np.allclose(scipy.linalg.eigvalsh(np.eye(2)), [1, 1])),
           'public_read': (directory / 'public.txt').read_text() == 'public positive canary',
           'private_dummy_denied': denied(configuration['outside_canary']),
           'sibling_dummy_denied': denied(configuration['sibling_canary']),
           'symlink_escape_denied': denied(directory / 'escape'),
           'public_write_denied': denied(directory / 'public.txt', 'w'),
           'outside_write_denied': denied(configuration['outside_canary'], 'w'),
           'clean_environment': 'ALE_PREFLIGHT_DUMMY' not in os.environ,
           'network_namespace': os.readlink('/proc/self/ns/net') != configuration['host_network_namespace'],
           'pid_namespace': os.readlink('/proc/self/ns/pid') != configuration['host_pid_namespace']}
try:
    socket.create_connection(('192.0.2.1', 9), timeout=0.2).close()
    results['network_denied'] = False
except OSError:
    results['network_denied'] = True
Path(arguments.output).write_text(json.dumps(results))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    destination = arguments.output.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='public_canary_preflight_', dir=destination.parent))
    submission = directory / 'submission'
    inputs = directory / 'inputs'
    submission.mkdir()
    inputs.mkdir()
    (submission / 'solve.py').write_text(PROBE)
    outside = directory / 'public_negative_canary.txt'
    sibling = directory / 'public_sibling_canary.txt'
    outside.write_text('nonsecret negative canary')
    sibling.write_text('nonsecret sibling canary')
    (inputs / 'public.txt').write_text('public positive canary')
    (inputs / 'escape').symlink_to(outside)
    (inputs / 'probe.json').write_text(json.dumps({'outside_canary': str(outside), 'sibling_canary': str(sibling),
                                                 'host_network_namespace': os.readlink('/proc/self/ns/net'),
                                                 'host_pid_namespace': os.readlink('/proc/self/ns/pid')}))
    os.environ['ALE_PREFLIGHT_DUMMY'] = 'public inherited-environment canary'
    results, runtime = replay(submission, ROOT / 'participant' / 'workspace', inputs, directory / 'output', seconds=15)
    report = {'passed': results is not None and all(results.values()), 'controls': results,
              'runtime': runtime, 'fixtures': str(directory),
              'scope': 'Exact evaluator replay configuration; no agent, credentials, or private scientific data accessed.'}
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
