import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import time
import numpy as np
from scipy.optimize import brentq
ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
sys.path.insert(0, ASSETS+'/workspace')
from pair_model import CASOracle

generator = np.random.default_rng(145729)
tables = []
orbitals = []
diagnostics = []
start = time.process_time()
for trial in range(800):
    onsite = np.r_[[-.45, -.22, 0.], generator.uniform(1.05, 2.1, 8)]
    hopping = np.zeros((11,11))
    hopping[:3,3:] = generator.normal(0, generator.uniform(.025,.065), (3,8))
    hopping[3:,:3] = hopping[:3,3:].T
    density = generator.normal(0,.06,(11,11))
    density = (density+density.T)/2
    np.fill_diagonal(density,0)
    model = {'family':'cancellation', 'orbital_energy':onsite.tolist(), 'hopping':hopping.tolist(), 'density':density.tolist()}
    base = CASOracle(model)
    singles = np.array([base.energy(1 << site) for site in range(8)])
    ordering = generator.permutation(8)
    chain = {tuple(sorted(pair)) for pair in zip(ordering[:-1], ordering[1:])}
    for left in range(8):
        for right in range(left+1,8):
            if (left,right) not in chain and generator.random() > .2:
                continue
            target = singles[left] + singles[right]
            mask = (1 << left) | (1 << right)
            def objective(value):
                model['hopping'][left+3][right+3] = float(value)
                model['hopping'][right+3][left+3] = float(value)
                return CASOracle(model).energy(mask) - target
            roots = []
            grid = np.linspace(-.89,.89,13)
            values = [objective(value) for value in grid]
            for interval in range(len(grid)-1):
                if values[interval]*values[interval+1] < 0:
                    roots.append(brentq(objective, grid[interval], grid[interval+1], xtol=1e-12))
            best = max(roots, key=abs) if roots else 0.
            objective(best)
    oracle = CASOracle(model)
    diagnostic = oracle.spectrum()
    if diagnostic['reference_weight'] < .94 or diagnostic['gap'] < .35:
        continue
    tables.append(oracle.all_energies())
    orbitals.append(onsite)
    diagnostics.append([diagnostic['reference_weight'],diagnostic['gap']])
    if len(tables) % 20 == 0:
        np.savez_compressed('cancellation.npz', energies=tables, orbital_energy=orbitals, diagnostics=diagnostics)
        print(len(tables), 'trials',trial+1,'cpu',round(time.process_time()-start,2),flush=True)
    if len(tables) >= 120:
        break
