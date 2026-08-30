import argparse
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
