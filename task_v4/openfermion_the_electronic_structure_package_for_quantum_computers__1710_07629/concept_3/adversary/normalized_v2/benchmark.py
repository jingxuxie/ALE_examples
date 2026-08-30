import argparse
import json
import time
import numpy as np
import baseline_features
import geometry_features
import physics_features
import active_features
import block_features

def calculate(inputs):
    started=time.process_time()
    basic=baseline_features.features(inputs)
    print('basic',time.process_time()-started,flush=True)
    geometry=geometry_features.features(inputs)
    print('geometry',time.process_time()-started,flush=True)
    result=[]
    timings=np.zeros(3)
    for index,sites in enumerate(inputs['n_sites']):
        arguments=(np.ascontiguousarray(inputs['hopping'][index,:sites,:sites]),np.ascontiguousarray(inputs['interaction'][index,:sites]),np.ascontiguousarray(inputs['potential'][index,:sites]))
        before=time.process_time()
        physics=physics_features.calculate(*arguments)
        timings[0]+=time.process_time()-before
        before=time.process_time()
        active=active_features.calculate(*arguments)
        timings[1]+=time.process_time()-before
        before=time.process_time()
        block=block_features.calculate(*arguments,counts=(4,))
        timings[2]+=time.process_time()-before
        result.append(np.r_[basic[index],physics,active,block,np.zeros(22),geometry[index]])
        if index%64==63:
            print('row',index+1,'cpu',time.process_time()-started,'components',timings,flush=True)
    return np.array(result)

if __name__=='__main__':
    inputs=dict(np.load('dev/validation.npz'))
    wall=time.perf_counter()
    features=calculate(inputs)
    np.save('dev/benchmark_features.npy',features)
    print('wall',time.perf_counter()-wall,'cpu',time.process_time(),flush=True)
