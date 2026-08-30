import json
import numpy as np
from pathlib import Path
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix

root = Path('/tmp/cascade-c2-g2-v3-mirk7s27')
signatures = np.loadtxt(root / 'attempts/v_3/signatures.txt', dtype=int)
size = len(signatures)
matrix = lil_matrix((385, size + 384))
for position, signature in enumerate(signatures):
    for pass_index, block in enumerate(signature):
        matrix[64 * pass_index + block, position] = 1
    matrix[384, position] = 1
for check in range(384):
    matrix[check, size + check] = -2
lower = np.zeros(385)
upper = np.zeros(385)
lower[-1] = 8
upper[-1] = 18
objective = np.zeros(size + 384)
objective[:size] = 1
result = milp(objective, integrality=np.ones(size + 384), bounds=Bounds(np.zeros(size + 384), np.r_[np.ones(size), np.full(384, 9)]), constraints=LinearConstraint(matrix.tocsc(), lower, upper), options={'time_limit': 600, 'disp': True})
print(result, flush=True)
if result.x is not None:
    errors = np.flatnonzero(result.x[:size] > 0.5).tolist()
    (root / 'attempts/v_3/milp_core.json').write_text(json.dumps({'errors': errors}) + '\n')
