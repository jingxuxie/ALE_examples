import json
from pathlib import Path

import numpy as np


cases = [(32, 8, 24, 'odd'), (64, 13, 17, 'even'), (48, 11, 23, 'odd')]
for index, (length, dimension, cap, sector) in enumerate(cases):
    coordinates = np.linspace(0, 2 * np.pi, length)
    if index == 0:
        omega = np.full(length, 1.85)
        mass = np.full(length, -0.20)
        quartic = np.full(length, 0.05)
        coupling = np.where(np.arange(length - 1) % 2, 0.05, 1.50)
    elif index == 1:
        omega = np.where(np.arange(length) % 2, 0.55, 1.85)
        mass = np.where(np.arange(length) % 2, -0.20, 0.03)
        quartic = np.where(np.arange(length) % 2, 0.05, 0.30)
        coupling = np.where(np.arange(length - 1) % 2, 0.05, 1.50)
    else:
        omega = np.full(length, 0.70)
        mass = -0.03 + 0.01 * np.cos(coordinates)
        quartic = np.full(length, 0.06)
        coupling = np.ones(length - 1)
        coupling[[11, 23, 35]] = 0.05
    request = dict(version=1, case_id=f'stress-{index}', seed=73, n_sites=length,
                   local_dim=dimension, bond_cap=cap, sector=sector,
                   omega=omega.tolist(), mass2=mass.tolist(), lambda4=quartic.tolist(),
                   coupling=coupling.tolist(), field=[0.0] * length,
                   budget_seconds=6, wall_seconds=30)
    Path(f'experiments/stress_{index}.json').write_text(json.dumps(request))
