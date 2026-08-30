import json

import numpy as np
from scipy.stats import qmc

from optimize import OUT, PROTOCOL, PUBLIC
from screen import full_cases

corners = full_cases()
bits = qmc.Sobol(8, scramble=True, seed=472).random_base2(5) >= 0.5
indices = bits.astype(int) @ (2 ** np.arange(7, -1, -1))
selected = PUBLIC + [corners[index] for index in indices]
reports = json.loads((OUT / 'baseline_corners.json').read_text())
selected += [report['case'] for report in reports[:12]]
unique = {}
for case in selected:
    key = tuple(case[name] for name in PROTOCOL['uncertainty'])
    unique[key] = case
(OUT / 'training.json').write_text(json.dumps(list(unique.values()), indent=2) + '\n')
print('training cases', len(unique))
