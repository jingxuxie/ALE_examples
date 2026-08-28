import difflib
import json
from lib2to3.refactor import RefactoringTool, get_fixers_from_package
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
source = ROOT / 'private' / 'source' / 'anc' / 'code'
destination = ROOT / 'private' / 'official_port'
tool = RefactoringTool(get_fixers_from_package('lib2to3.fixes'))
patch = '*** Begin Patch\n'
for path in source.glob('*.py'):
    content = str(tool.refactor_string(path.read_text(), str(path)))
    content = content.replace('if(M == None)', 'if(M is None)')
    content = content.replace('numpy.load(fname)', 'numpy.load(fname, allow_pickle=True)')
    content = content.replace('scipy.load(fname)', 'scipy.load(fname, allow_pickle=True)')
    patch += f'*** Add File: {destination / path.name}\n'
    patch += ''.join('+' + line + '\n' for line in content.splitlines())
patch += '*** End Patch\n'
if not destination.exists():
    subprocess.run(['apply_patch', patch], check=True, stdout=subprocess.DEVNULL)
sys.path.insert(0, str(destination))
import phi1234
sys.path.insert(0, str(ROOT / 'private' / 'engine'))
from basis import enumerate_basis
from operators import operator_matrix

model = phi1234.Phi1234()
for parity in [1, -1]:
    model.buildFullBasis(parity, 4.0, 1.0, 9.0)
model.buildMatrix()
errors = {}
for parity in [1, -1]:
    modes, frequencies, states, energies = enumerate_basis(4.0, 1.0, 9.0, 'periodic', 0, (1 - parity) // 2)
    lookup = {tuple(state): index for index, state in enumerate(states)}
    original = model.fullBasis[parity]
    projection = np.zeros((len(states), original.size))
    for column, state in enumerate(original):
        padding = (len(modes) - len(state.occs)) // 2
        padded = tuple([0] * padding + state.occs + [0] * padding)
        reverse = padded[::-1]
        if padded == reverse:
            projection[lookup[padded], column] = 1.0
        else:
            projection[lookup[padded], column] = 2**-0.5
            projection[lookup[reverse], column] = 2**-0.5
    for degree in [0, 2, 4]:
        matrix = operator_matrix(modes, frequencies, states, 4.0, degree)
        transformed = projection.T @ matrix @ projection
        official = model.potential[parity][degree].M.toarray()
        error = float(np.max(abs(transformed - official)))
        errors[f'parity_{parity}_degree_{degree}'] = error
        assert error < 1e-10, (parity, degree, error)
(ROOT / 'private' / 'official_crosscheck.json').write_text(json.dumps(errors, indent=2))
print('Official ancillary operator cross-check:', errors)
