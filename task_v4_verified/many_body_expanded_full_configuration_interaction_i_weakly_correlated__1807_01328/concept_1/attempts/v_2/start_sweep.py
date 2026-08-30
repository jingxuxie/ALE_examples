import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import numpy as np
from quadrature import ORDERS,HIGH,CANDIDATES,SELECTOR,PAIR,TRIPLES,features,mobius
from design import covariance,design,estimate
from angle_fit import AngleFit
from channel_fit import ChannelFit
from covariance_fit import CovarianceFit
ASSETS='/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
tables=np.load(ASSETS+'/input/practice.npz')['energies']
models=json.load(open(ASSETS+'/input/practice_models.json'))
factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
start=time.process_time()
for index in [32,26,14,29]:
    table=tables[index]
    matrix=covariance(features(table)[1]*factor,.7,8)
    chosen=design(matrix,'anchor')
    target=SELECTOR@mobius(table)[HIGH]
    angle=AngleFit(table,models[index]['orbital_energy'],np.r_[PAIR,TRIPLES,CANDIDATES[chosen]])
    predicted=angle.fit(starts=24,iterations=600,initialization='pairs')
    results=[]
    for score,parameters in angle.fits:
        predicted=angle.evaluate(parameters,np.arange(256))
        for iteration in range(8):
            predicted=angle.evaluate(parameters,np.arange(256),predicted)
        error=(estimate(matrix,SELECTOR@mobius(predicted)[HIGH],target,chosen)[0]-target[-1])*1e6
        results.append((score,error))
    print(index,'starts',results,'cpu',time.process_time()-start,flush=True)
