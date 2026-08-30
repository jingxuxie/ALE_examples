import ctypes
import itertools
import json
import os
import time
import numpy as np
from optimize import ROOT, Ensemble, load, save, library, array_pointer, optimize
from robustness import make_pool, unique, adversaries
from minimax import fit

library.nominal_sources.argtypes = [array_pointer,array_pointer,ctypes.c_int,ctypes.c_void_p,ctypes.c_int]
library.approximate_gauges.argtypes = [array_pointer,array_pointer,array_pointer,array_pointer,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p]

def search(angles,pool,seed):
    ensemble = Ensemble(pool)
    scores = ensemble.evaluate(angles,False)
    fields = []
    for index in np.argsort(scores):
        field = np.array(pool[index]['z_drift_radians_per_layer'])
        if np.any(field) and not any(np.max(abs(field-other)) < 1e-9 or np.max(abs(field+other)) < 1e-9 for other in fields):
            fields.append(field)
        if len(fields) >= 20:
            break
    fields = np.ascontiguousarray(fields)
    sources = np.empty((50+24*len(fields),4096),dtype=np.complex128)
    started = time.time()
    library.nominal_sources(np.ascontiguousarray(angles),fields,len(fields),sources.ctypes.data,4)
    amplitudes = (sources[:,0]+sources[:,-1])/np.sqrt(2)
    sources[:,0] -= amplitudes/np.sqrt(2)
    sources[:,-1] -= amplitudes/np.sqrt(2)
    residual = sources[-1]
    jacobians = sources[:48].reshape(24,2,4096)
    increments = np.where(angles.reshape(24,2) >= 0,-np.pi,np.pi)
    constants, linear, quadratic = [],[],[]
    for first,second,common in itertools.product([-1,1],repeat=3):
        gains = np.array([first*.025,second*.025])
        base = residual + np.einsum('lg,lgk->k',angles.reshape(24,2)*gains,jacobians) + common*.02*sources[48]
        changes = np.einsum('lg,lgk->lk',increments*gains,jacobians)
        constants.append(np.vdot(base,base).real)
        linear.append(2*(changes.conj()@base).real)
        quadratic.append((changes.conj()@changes.T).real)
    drift_sources = sources[49:-1].reshape(len(fields),24,4096)
    drift_quadratic = np.array([(values.conj()@values.T).real for values in drift_sources])
    arrays = [np.ascontiguousarray(values) for values in [constants,linear,quadratic,drift_quadratic]]
    masks = np.empty(64,dtype=np.uint32)
    losses = np.empty(64)
    library.approximate_gauges(*arrays,len(fields),len(masks),6000,seed,masks.ctypes.data,losses.ctypes.data)
    print('SURROGATE', 'seconds',time.time()-started,'predicted best',1-losses.min(),'candidates',len(np.unique(masks)),flush=True)
    candidates = [(float(scores.min()),angles.copy(),0)]
    for mask in np.unique(masks):
        if mask == 0:
            continue
        candidate = angles.copy().reshape(24,2)
        layers = np.array([(int(mask)>>layer)&1 for layer in range(24)],dtype=bool)
        candidate[layers] = (candidate[layers]+2*np.pi)%(2*np.pi)-np.pi
        candidate = candidate.ravel()
        trial_scores = ensemble.evaluate(candidate,False)
        candidates.append((float(trial_scores.min()),candidate,int(mask)))
    candidates.sort(key=lambda item:item[0],reverse=True)
    print('EXACT GAUGES',[(item[0],item[2]) for item in candidates[:8]],flush=True)
    return candidates

def refine(candidate,pool,core,label):
    ensemble = Ensemble(pool)
    for iteration in range(3):
        scores = ensemble.evaluate(candidate,False)
        training = unique(core+[pool[index] for index in np.argsort(scores)[:100]])
        candidate = fit(candidate,training,f'{label}_{iteration}.json',iterations=350)
        scores = ensemble.evaluate(candidate,False)
        incumbent = load(ROOT/'robust_best.json')
        incumbent_score = float(ensemble.evaluate(incumbent,False).min())
        print('SURROGATE REFINED',label,iteration,'min',scores.min(),'incumbent',incumbent_score,flush=True)
        if scores.min() > incumbent_score:
            save(candidate,'robust_best.json')
            save(candidate)
        if scores.min() > .954:
            return True
        trained_min = Ensemble(training).evaluate(candidate,False).min()
        if trained_min-scores.min() < 1e-6:
            break
    return False

def main():
    pool = make_pool()
    if (ROOT/'stress_scenarios.json').exists():
        pool = unique(pool+json.loads((ROOT/'stress_scenarios.json').read_text())['scenarios'])
    core = [scenario for scenario in make_pool() if scenario['name'].startswith('corner_') and
            scenario['name'].endswith(tuple(f'_field_{field}' for field in range(5)))]
    if os.environ.get('EXTRA_START'):
        if refine(load(ROOT/os.environ['EXTRA_START']),pool,core,'extra_start'):
            return
    for epoch in range(10):
        angles = load(ROOT/'robust_best.json')
        pool = unique(pool+adversaries(angles,starts=32,seed=419188+epoch))
        candidates = search(angles,pool,seed=9173+epoch)
        for rank, (initial_score,candidate,mask) in enumerate(candidates[:4]):
            if rank and mask == 0:
                continue
            if refine(candidate,pool,core,f'surrogate_{epoch}_{rank}'):
                (ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))
                return
        (ROOT/'stress_scenarios.json').write_text(json.dumps({'scenarios':pool}))

if __name__ == '__main__':
    main()
