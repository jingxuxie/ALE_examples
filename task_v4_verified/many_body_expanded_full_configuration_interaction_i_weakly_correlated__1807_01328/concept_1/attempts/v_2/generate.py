import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import time
import numpy as np

ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
sys.path.insert(0, ASSETS+'/workspace')
from pair_model import CASOracle, FAMILIES, sample_model

generator = np.random.default_rng(940817)
tables = []
orbitals = []
families = []
diagnostics = []
start = time.process_time()
for index in range(1200):
    family = FAMILIES[index % 6]
    model = sample_model(175023 + index, family)
    if index >= 600:
        hopping = np.array(model['hopping'])
        density = np.array(model['density'])
        hopping[3:, 3:] *= generator.uniform(1.3, 3.5)
        hopping = np.clip(hopping, -0.9, 0.9)
        density *= generator.uniform(0.5, 2.0)
        density = np.clip(density, -0.65, 0.65)
        hopping[:3, 3:] *= 0.5
        hopping[3:, :3] = hopping[:3, 3:].T
        model['density'] = density.tolist()
        for attempt in range(30):
            model['hopping'] = hopping.tolist()
            diagnostic = CASOracle(model).spectrum()
            if diagnostic['gap'] >= 0.35 and diagnostic['reference_weight'] >= 0.94:
                break
            hopping *= 0.9
    oracle = CASOracle(model)
    tables.append(oracle.all_energies())
    orbitals.append(model['orbital_energy'])
    families.append(family)
    diagnostics.append(list(oracle.spectrum().values())[:3])
    if index % 100 == 99:
        np.savez_compressed('synthetic.npz', energies=np.array(tables), orbital_energy=np.array(orbitals), families=np.array(families), diagnostics=np.array(diagnostics))
        print(index+1, 'cpu', round(time.process_time()-start, 2), flush=True)
