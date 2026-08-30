import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import numpy as np
import solution
from design import design
from quadrature import ORDERS,PAIR,TRIPLES,mobius
data=np.load('cancellation.npz')
factors=solution.load_models()
errors=[]
for sequence,index in enumerate(range(0,120,5)):
    table=data['energies'][index]
    terms=mobius(table)
    ratio=abs(terms[TRIPLES]).sum()/max(abs(terms[PAIR]).sum(),1e-20)
    selected=[]
    result=[]
    def request(masks,values,observed):
        for mask in masks:
            selected.append(int(mask))
            values[mask]=table[mask]
            observed.add(int(mask))
    solution.request=request
    solution.send=lambda message:result.append(message['estimate'])
    solution.design=lambda matrix,mode:design(matrix,'anchor_two_fives' if ratio>1.5 else mode)
    observation={'values':[[mask,float(table[mask])] for mask in range(256) if ORDERS[mask]<=2],'orbital_energy':data['orbital_energy'][index]}
    solution.solve(observation,factors,sequence)
    error=(result[0]-table[-1])*1e6
    errors.append(error)
    print(index,'ratio',ratio,'error',error,'selected',[sum(ORDERS[mask]==order for mask in selected) for order in [3,4,5,6]],flush=True)
print('rmse',np.sqrt(np.mean(np.array(errors)**2)),flush=True)
