import json
from pathlib import Path
import numpy as np

root = Path(__file__).parent
rng = np.random.default_rng(59237)
settings = [
    ('critical', 64, 14, 24, 'even', -.042, .075, .62),
    ('critical_odd', 48, 12, 16, 'odd', -.063, .10, .8),
    ('broken', 48, 10, 16, 'even', -.17, .075, 1.2),
    ('broken_odd', 64, 14, 24, 'odd', -.15, .095, .95),
    ('alternating', 48, 12, 20, 'even', -.075, .17, 1.1),
    ('alternating_odd', 32, 8, 12, 'odd', -.10, .21, 1.5),
    ('weak', 64, 14, 20, 'even', -.055, .085, .75),
    ('weak_odd', 56, 10, 16, 'odd', -.08, .14, 1.0),
]
for name, length, dimension, cap, sector, mass, quartic, omega in settings:
    sites = np.arange(length)
    masses = mass + .012*np.cos(2*np.pi*sites/(length-1))
    lambdas = quartic*(1+.12*np.sin(sites*.63))
    frequencies = omega*(1+.12*(sites%2))
    couplings = .85+.2*np.sin(np.arange(length-1)*.4)
    if 'alternating' in name:
        couplings = np.where(np.arange(length-1)%2, .2, 1.4)
        masses += .025*(2*(sites%2)-1)
    if 'weak' in name:
        couplings[length//2-1] = .05
        couplings[length//4] = .10
        masses += .012*np.where(sites < length//2, 1, -1)
    request = dict(version=1, case_id=name, seed=1247, n_sites=length,
        local_dim=dimension, bond_cap=cap, sector=sector,
        mass2=masses.tolist(), lambda4=lambdas.tolist(), omega=frequencies.tolist(),
        field=[0.0]*length, coupling=couplings.tolist())
    for budget in [6, 40, 160]:
        request.update(budget_seconds=budget, wall_seconds=3*budget)
        (root/(name+str(budget)+'.json')).write_text(json.dumps(request))
