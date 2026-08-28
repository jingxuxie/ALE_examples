import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / 'private'
REFERENCE = PRIVATE / 'reference'
RESEARCH = ROOT.parents[1] / 'research'
VENDOR = Path(os.environ.get('PILOT02_VENDOR', RESEARCH / 'vendor')).resolve()
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['MPLCONFIGDIR'] = str(REFERENCE / '.cache' / 'matplotlib')
os.environ['XDG_CACHE_HOME'] = str(REFERENCE / '.cache')
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '2'
if VENDOR.is_dir():
    sys.path.insert(0, str(VENDOR))


def confined(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f'Output must remain in {ROOT}: {resolved}')
    return resolved
