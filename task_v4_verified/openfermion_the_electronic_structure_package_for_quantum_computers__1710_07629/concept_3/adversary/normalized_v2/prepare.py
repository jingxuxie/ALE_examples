import time
from pathlib import Path
import numpy as np
import baseline_features
import physics_features

for split in ('train','validation'):
    data = dict(np.load(Path('dev')/(split+'.npz')))
    started = time.perf_counter()
    basic = baseline_features.features(data)
    physics = []
    for index,sites in enumerate(data['n_sites']):
        physics.append(physics_features.calculate(
            np.ascontiguousarray(data['hopping'][index,:sites,:sites]),
            np.ascontiguousarray(data['interaction'][index,:sites]),
            np.ascontiguousarray(data['potential'][index,:sites])))
        if index%100 == 0:
            print(split,index,time.perf_counter()-started,flush=True)
    np.savez('dev/'+split+'_features.npz',basic=basic,physics=np.array(physics))
    print(split,'finished',time.perf_counter()-started,flush=True)
