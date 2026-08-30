import json
from pathlib import Path
import socket
import sys
import numpy
import scipy


ROOT = Path(__file__).resolve().parent
checks = {}
private = ROOT.parent / 'private_canary.txt'
try:
    private.read_text()
    checks['private_denied'] = False
except OSError:
    checks['private_denied'] = True
try:
    (ROOT / 'readonly.txt').write_text('modified')
    checks['participant_read_only'] = False
except OSError:
    checks['participant_read_only'] = True
try:
    Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/kdotpy_k_p_theory_on_a_lattice_for_simulating_semiconductor_band_struc__2407_12651/authoring/SOURCES.md').read_text()
    checks['generation_sources_denied'] = False
except OSError:
    checks['generation_sources_denied'] = True
checks['python_dependencies'] = bool(numpy.__version__ and scipy.__version__)
checks['network_namespace'] = not Path('/proc/net/route').read_text().strip().splitlines()[1:]
report = {'passed': all(checks.values()), 'checks': checks, 'numpy': numpy.__version__,
          'scipy': scipy.__version__, 'python': sys.version}
destination = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if destination is not None:
    destination.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
