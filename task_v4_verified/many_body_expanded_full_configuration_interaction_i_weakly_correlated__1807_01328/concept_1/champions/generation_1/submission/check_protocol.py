import json
import os
import resource
import sys
from pathlib import Path

import numpy as np

from protocol import run_policy, summarize


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))


data = np.load('fresh.npz')
families = ('local', 'collective', 'frustrated', 'bridge', 'density', 'mixed')
models = [{'family': families[int(family)], 'orbital_energy': orbitals.tolist()}
          for family, orbitals in zip(data['families'][:72], data['orbitals'][:72])]
records, elapsed = run_policy([sys.executable, str(Path('solution.py').resolve())], models, data['energies'][:72], environment=dict(os.environ), preexec_fn=limits)
report = summarize(records, elapsed)
Path('protocol_fresh.json').write_text(json.dumps(report, indent=2))
print(json.dumps({key: value for key, value in report.items() if key != 'records'}, indent=2))
