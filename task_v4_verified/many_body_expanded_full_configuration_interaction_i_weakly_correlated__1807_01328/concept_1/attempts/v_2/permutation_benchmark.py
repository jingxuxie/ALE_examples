import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import numpy as np
from quadrature import ORDERS,HIGH,CANDIDATES,SELECTOR,PAIR,TRIPLES,SINGLE,features,mobius
from response_fit import MASKS
from design import covariance,design,estimate
from angle_fit import AngleFit
ASSETS='/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
tables=np.load(ASSETS+'/input/practice.npz')['energies']
models=json.load(open(ASSETS+'/input/practice_models.json'))
old=json.load(open('physical_benchmark.json'))
factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
start=time.process_time()
records=[]
for index,table in enumerate(tables):
    if old[index]['std']<2:
        records.append({'index':index,'error':old[index]['baseline'],'score':0.})
        continue
    ordering=np.argsort(table[SINGLE])
    mapping=(MASKS.astype(int)*(1 << ordering)[None]).sum(axis=1)
    reverse=np.argsort(mapping)
    orbital=np.array(models[index]['orbital_energy'])
    orbital[3:]=orbital[3:][ordering]
    matrix=covariance(features(table)[1]*factor,.7,8)
    chosen=design(matrix,'anchor')
    target=SELECTOR@mobius(table)[HIGH]
    fit=AngleFit(table[mapping],orbital,reverse[np.r_[PAIR,TRIPLES,CANDIDATES[chosen]]])
    predicted=fit.fit(starts=5,iterations=250,time_budget=1.2)[reverse]
    error=(estimate(matrix,SELECTOR@mobius(predicted)[HIGH],target,chosen)[0]-target[-1])*1e6
    record={'index':index,'error':error,'score':fit.score}
    records.append(record)
    print(record,'cpu',time.process_time()-start,flush=True)
json.dump(records,open('permutation_benchmark.json','w'),indent=2)
for cutoff in [.003,.004,.005,.007]:
    error=np.array([row['error'] if row['score']<cutoff else old[index]['baseline'] for index,row in enumerate(records)])
    print(cutoff,np.sqrt(np.mean(error**2)),max(abs(error)),flush=True)
print('cpu',time.process_time()-start,flush=True)
