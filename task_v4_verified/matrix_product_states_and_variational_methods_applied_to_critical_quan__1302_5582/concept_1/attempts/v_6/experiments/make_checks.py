import json
from pathlib import Path

import numpy as np


def create(name, length, dimension, cap, sector, omega, mass, quartic, coupling):
    request = dict(version=1, case_id=name, seed=9371, n_sites=length,
                   local_dim=dimension, bond_cap=cap, sector=sector,
                   omega=np.broadcast_to(omega, (length,)).tolist(),
                   mass2=np.broadcast_to(mass, (length,)).tolist(),
                   lambda4=np.broadcast_to(quartic, (length,)).tolist(),
                   coupling=np.broadcast_to(coupling, (length - 1,)).tolist(),
                   field=[0.0] * length)
    for budget in (6, 40, 120):
        request.update(budget_seconds=budget, wall_seconds=3 * budget + 12)
        Path(f'experiments/{name}_{budget}.json').write_text(json.dumps(request))


coordinate = np.linspace(0, 1, 64)
links = 1.0 + 0.4 * np.sin(np.linspace(0, 2 * np.pi, 63)) ** 2
links[[12, 31, 50]] = [0.12, 0.05, 0.2]
create('largecritical', 64, 14, 24, 'even', 0.65, -0.03, 0.06, links)
links = np.where(np.arange(55) % 2, 0.12, 1.4)
coordinate = np.linspace(0, 2 * np.pi, 56)
create('alternating', 56, 10, 16, 'odd', 0.75 + 0.1 * np.cos(coordinate),
       -0.045 + 0.035 * np.cos(coordinate), 0.10, links)
coordinate = np.linspace(0, 1, 48)
links = 0.1 + 1.3 * np.sin(np.linspace(0, 3 * np.pi, 47)) ** 2
create('mixed', 48, 14, 20, 'even', 1.2 + 0.6 * np.cos(2 * np.pi * coordinate),
       -0.02 - 0.15 * np.exp(-((coordinate - 0.5) / 0.22) ** 2),
       0.08 + 0.18 * coordinate, links)
links = np.ones(63)
links[[15, 47]] = 0.05
create('shallowodd', 64, 12, 16, 'odd', 0.58, -0.035, 0.05, links)
create('ordered', 32, 8, 12, 'even', 0.9, -0.18, 0.06, 1.3)
coordinate = np.linspace(0, 2 * np.pi, 32)
links = 0.1 + 1.3 * np.sin(np.linspace(0, 3 * np.pi, 31)) ** 2
create('oddcutoff', 32, 9, 13, 'odd', 0.7 + 0.1 * np.cos(coordinate),
       -0.04 + 0.03 * np.cos(coordinate), 0.09 + 0.04 * np.sin(coordinate), links)
