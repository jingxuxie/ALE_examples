import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import numpy as np
from scipy.linalg import solve
from quadrature import ORDERS,HIGH,CANDIDATES,SELECTOR,PAIR,TRIPLES,features,mobius
from design import covariance,design,estimate
from angle_fit import AngleFit
from channel_fit import ChannelFit

ASSETS='/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
tables=np.load(ASSETS+'/input/practice.npz')['energies']
models=json.load(open(ASSETS+'/input/practice_models.json'))
factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
start=time.process_time()
records=[]
for index,table in enumerate(tables):
    matrix=covariance(features(table)[1]*factor,.7,8)
    chosen=design(matrix,'anchor')
    gram=matrix[np.ix_(chosen,chosen)]
    remaining=matrix[-1,-1]-matrix[-1,chosen]@solve(gram+np.eye(len(chosen))*1e-24,matrix[chosen,-1],assume_a='pos')
    uncertainty=np.sqrt(max(remaining,0))
    target=SELECTOR@mobius(table)[HIGH]
    baseline=estimate(matrix,np.zeros(len(CANDIDATES)+1),target,chosen)[0]-target[-1]
    record={'index':index,'family':models[index]['family'],'std':uncertainty*1e6,'baseline':baseline*1e6}
    if uncertainty>2e-6:
        angle=AngleFit(table,models[index]['orbital_energy'],np.r_[PAIR,TRIPLES,CANDIDATES[chosen]])
        predicted=angle.fit(starts=5,iterations=250)
        record['angle']=(estimate(matrix,SELECTOR@mobius(predicted)[HIGH],target,chosen)[0]-target[-1])*1e6
        record['angle_score']=angle.score
        channel=ChannelFit(angle)
        predicted=channel.fit(starts=1,iterations=250)
        record['channel']=(estimate(matrix,SELECTOR@mobius(predicted)[HIGH],target,chosen)[0]-target[-1])*1e6
        record['channel_score']=channel.score
    else:
        record.update(angle=record['baseline'],channel=record['baseline'],angle_score=0.,channel_score=0.)
    records.append(record)
    print(record,'cpu',time.process_time()-start,flush=True)
with open('physical_benchmark.json','w') as output:
    json.dump(records,output,indent=2)
for label in ['baseline','angle','channel']:
    errors=np.array([record[label] for record in records])
    print(label,np.sqrt(np.mean(errors**2)),{family:np.sqrt(np.mean([record[label]**2 for record in records if record['family']==family])) for family in set(record['family'] for record in records)},flush=True)
print('cpu',time.process_time()-start,flush=True)
