import json
from pathlib import Path
import numpy as np

root = Path(__file__).parent
rng = np.random.default_rng(19610)
for index in range(4):
    length, dimension, cap = 64, 14, (12 if index == 3 else 24)
    sites = np.arange(length)
    masses = np.full(length, [-.19, -.08, -.09, -.033][index])
    quartic = np.full(length, [.30, .18, .10, .06][index])
    frequencies = np.full(length, [1.65, .55, 1.75, .7][index])
    couplings = np.full(length-1, [1.5, 1.45, .9, 1.][index])
    if index == 1:
        frequencies[1::2] = 1.85
        masses += .015*np.sin(sites*.13)
    elif index == 2:
        masses[:length//2] = -.17
        quartic[length//2:] = .17
        couplings[length//2-1] = .065
    elif index == 3:
        frequencies = rng.uniform(.55, 1.85, length)
        masses += rng.uniform(-.01, .01, length)
    request = dict(version=1, case_id='stress'+str(index), seed=2003, n_sites=length,
        local_dim=dimension, bond_cap=cap, sector='even' if index%2 == 0 else 'odd',
        mass2=masses.tolist(), lambda4=quartic.tolist(), omega=frequencies.tolist(),
        field=[0.0]*length, coupling=couplings.tolist())
    for budget in [6, 40, 160]:
        request.update(budget_seconds=budget, wall_seconds=3*budget)
        (root/('stress'+str(index)+'_'+str(budget)+'.json')).write_text(json.dumps(request))
