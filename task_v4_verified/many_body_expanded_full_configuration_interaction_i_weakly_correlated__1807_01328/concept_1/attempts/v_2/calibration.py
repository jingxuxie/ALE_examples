import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import time
import numpy as np
from quadrature import ORDERS,HIGH,CANDIDATES,SELECTOR,SUBSET,SINGLE,features,mobius
from design import covariance,design,estimate,greedy

if __name__ == '__main__':
    start = time.process_time()
    ASSETS = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_1/adversary/ratchet_1/participant'
    practice=np.load(ASSETS+'/input/practice.npz')['energies']
    extra=np.concatenate((np.load('synthetic.npz')['energies'],np.load('cancellation.npz')['energies']))
    tables=np.concatenate((practice,extra[np.arange(0,len(extra),5)]))
    indices=np.r_[np.arange(36),np.arange(37,len(tables),2)]
    factor=np.load('quadrature_model.npz')['variance_scale'][ORDERS[HIGH]-4]
    weights=np.array([features(table)[1]*factor for table in tables])
    targets=np.array([SELECTOR@mobius(table)[HIGH] for table in tables])
    prior=[]
    for kind in ['neural','canonical']:
        means=np.zeros((len(tables),len(HIGH)))
        for order in [4,5]:
            predicted=np.load(kind+'_predictions_'+str(order)+'.npz')
            means[:,ORDERS[HIGH]==order]=np.concatenate((predicted['practice'],predicted['validation']))
        prior.append(means)
    for correlation,power in [(.1,4),(.3,4),(.7,8)]:
        matrices=[covariance(weights[index],correlation,power) for index in indices]
        for mode in ['simple','anchor','optimal']:
            chosen=[]
            for matrix in matrices:
                if mode=='simple':
                    utility=matrix[-1,:-1]**2/np.maximum(np.diag(matrix)[:-1],1e-28)
                    utility[ORDERS[CANDIDATES]!=6]=-1
                    chosen.append(greedy(matrix,int(np.argmax(utility)))[1])
                else:
                    chosen.append(design(matrix,mode))
            for feature_kind in ['none','global','node','ensemble']:
                for strength in ([0.] if feature_kind=='none' else [.03,.1,.3,1.,3.]):
                    errors=[]
                    for local,index in enumerate(indices):
                        matrix=matrices[local].copy()
                        feature_list=[]
                        if feature_kind!='none':
                            for order in [4,5]:
                                mask=(ORDERS[HIGH]==order)
                                feature_list.append(SELECTOR@(prior[0][index]*mask))
                                if feature_kind=='ensemble':
                                    feature_list.append(SELECTOR@(prior[1][index]*mask))
                                if feature_kind=='node':
                                    for site in range(8):
                                        feature_list.append(SELECTOR@(prior[0][index]*mask*SUBSET[HIGH,1 << site])*.5)
                        if feature_list:
                            feature=np.array(feature_list).T
                            matrix += strength*(feature@feature.T)
                        prediction=estimate(matrix,np.zeros(len(CANDIDATES)+1),targets[index],chosen[local])[0]
                        errors.append((prediction-targets[index,-1])*1e6)
                    errors=np.array(errors)
                    print(correlation,power,mode,feature_kind,strength,'practice',round(np.sqrt(np.mean(errors[:36]**2)),2),'ordinary',round(np.sqrt(np.mean(errors[36:96]**2)),2),'stress',round(np.sqrt(np.mean(errors[96:156]**2)),2),'cancel',round(np.sqrt(np.mean(errors[156:]**2)),2),'hard',np.round(errors[[14,26,29,32]],1).tolist(),flush=True)
    print('cpu',time.process_time()-start,flush=True)
