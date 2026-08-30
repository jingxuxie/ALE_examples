import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import numpy as np
from scipy.linalg import solve
from quadrature import ORDERS,HIGH,CANDIDATES,SELECTOR,PAIR,TRIPLES,SINGLE,LEFT,RIGHT,features,mobius
from response_fit import MASKS
from design import covariance,design,estimate
from angle_fit import AngleFit
synthetic=np.load('synthetic.npz')
cancellation=np.load('cancellation.npz')
tables=np.concatenate((synthetic['energies'][np.arange(0,240,5)],synthetic['energies'][np.arange(600,840,5)],cancellation['energies'][np.arange(0,120,5)]))
orbitals=np.concatenate((synthetic['orbital_energy'][np.arange(0,240,5)],synthetic['orbital_energy'][np.arange(600,840,5)],cancellation['orbital_energy'][np.arange(0,120,5)]))
ordering=np.random.default_rng(46819).permutation(120)
tables,orbitals=tables[ordering],orbitals[ordering]
records=json.load(open('synthetic_validation_report.json'))['records']
factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
for record in sorted(records,key=lambda row:-abs(row['error']))[:12]:
    index=record['index']
    table=tables[index]
    matrix=covariance(features(table)[1]*factor,.7,8)
    chosen=design(matrix,'anchor')
    target=SELECTOR@mobius(table)[HIGH]
    baseline=(estimate(matrix,np.zeros(len(CANDIDATES)+1),target,chosen)[0]-target[-1])*1e6
    gram=matrix[np.ix_(chosen,chosen)]
    gram+=np.eye(len(chosen))*max(np.diag(gram).max()*1e-12,1e-26)
    baseline_norm=target[chosen]@solve(gram,target[chosen],assume_a='pos')
    results=[]
    for canonical in [False,True]:
        mapping=np.arange(256)
        orbital=orbitals[index].copy()
        if canonical:
            permutation=np.argsort(table[SINGLE])
            mapping=(MASKS.astype(int)*(1 << permutation)[None]).sum(axis=1)
            orbital[3:]=orbital[3:][permutation]
        reverse=np.argsort(mapping)
        fitted=AngleFit(table[mapping],orbital,reverse[np.r_[PAIR,TRIPLES,CANDIDATES[chosen]]])
        predicted=fitted.fit(starts=5,iterations=250,time_budget=1.2)[reverse]
        mean=SELECTOR@mobius(predicted)[HIGH]
        error=(estimate(matrix,mean,target,chosen)[0]-target[-1])*1e6
        residual=target[chosen]-mean[chosen]
        ratio=(residual@solve(gram,residual,assume_a='pos'))/max(baseline_norm,1e-20)
        response_matrix=np.eye(8)
        response_matrix[LEFT,RIGHT]=-.85*np.tanh(fitted.parameters[:28])
        response_matrix[RIGHT,LEFT]=response_matrix[LEFT,RIGHT]
        gap=np.linalg.eigvalsh(response_matrix*np.sqrt(fitted.denominator[:,None]*fitted.denominator[None,:]))[0]-predicted[-1]
        results.append({'canonical':canonical,'score':fitted.score,'error':error,'chi_ratio':ratio,'gap':gap})
    print(index,record['kind'],record['family'],'current',record['error']*1e6,'base',baseline,'fits',results,flush=True)
