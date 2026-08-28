import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import concurrent.futures
import json
import time
import numpy as np
from physics import ForwardModel, feasibility
from fast_physics import Spectrum
from geometry import make_geometry
from gradient import derivatives, boundary_candidates


def evaluate(request,masks,count=2):
    values=[]
    for point in request['operating_points']:
        spectrum=Spectrum(ForwardModel(request,masks,point))
        if spectrum.invariant(True)!=-1:
            return -1,[]
        spectrum.scan(count)
        values.append(min(spectrum.values.values()))
    return float(.5*np.mean(values)+.5*min(values)),values


if __name__=='__main__':
    request=json.load(open('../participant/input/example.json'))
    masks=make_geometry(request,dict(frequency=3,amplitude=200,width=110))
    started=time.monotonic()
    score,values=evaluate(request,masks,5)
    print('START',score,values,time.monotonic()-started,flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        for iteration in range(15):
            futures=[pool.submit(derivatives,request,masks,point) for point in request['operating_points']]
            samples=[future.result() for future in futures]
            candidates=boundary_candidates(request,masks,samples,counts=(2,4,8,16,24,36))
            futures=[pool.submit(evaluate,request,candidate) for candidate in candidates]
            outcomes=[future.result() for future in futures]
            best=int(np.argmax([outcome[0] for outcome in outcomes]))
            print(iteration,'current',score,'proposals',outcomes,'time',time.monotonic()-started,flush=True)
            if outcomes[best][0] <= score+1e-5:
                break
            masks=candidates[best]
            score,values=outcomes[best]
            result=dict(schema_version=1,request_id=request['request_id'],geometry={name:mask.astype(int).tolist() for name,mask in masks.items()})
            with open('gradient_result.json','w') as handle:json.dump(result,handle)
    print('FINAL',evaluate(request,masks,9),feasibility(request,masks),time.monotonic()-started,flush=True)
