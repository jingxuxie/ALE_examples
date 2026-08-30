import os
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

def features(original,grouped):
    original_label=original.argmin(1);group_label=grouped.argmin(1);rows=np.arange(len(original))
    original_best=original[rows,original_label];group_best=grouped[rows,group_label]
    original_gap=original[rows,group_label]-original_best
    group_gap=grouped[rows,original_label]-group_best
    first=np.partition(original,1,axis=1)[:,1]-original_best
    second=np.partition(grouped,1,axis=1)[:,1]-group_best
    data=np.stack([np.ones(len(rows)),np.clip(original_best-group_best,-20,20)/5,np.clip(original_gap,0,20)/5,np.clip(group_gap,0,20)/5,np.clip(first,0,20)/5,np.clip(second,0,20)/5,np.minimum(original_best,group_best)/100],axis=1)
    return data,original_label,group_label

root=Path(os.environ['P'])
all_features=[];truth=[];orig=[];group=[];split=[]
cal_features=[];cal_truth=[];cal_orig=[];cal_group=[]
for case in sorted((root/'input/calibration').glob('*.npz')):
    labels=np.load('data_'+case.stem+'_83724_512.npz')['labels']@np.array([1,2,4,8])
    first=np.load('state16_'+case.stem+'.npz')['scores'][:,2]
    second=np.load('train_pfast2_'+case.stem+'.npz')['scores']
    data,first_label,second_label=features(first,second)
    all_features.append(data);truth.extend(labels);orig.extend(first_label);group.extend(second_label);split.extend(np.arange(len(labels))%2)
    labels=np.load(case)['labels']@np.array([1,2,4,8])
    first=np.load('adapt24_'+case.stem+'.npz')['scores'][:,2]
    second=np.load('pfast2_'+case.stem+'.npz')['scores']
    data,first_label,second_label=features(first,second)
    cal_features.append(data);cal_truth.extend(labels);cal_orig.extend(first_label);cal_group.extend(second_label)
data=np.concatenate(all_features);truth=np.array(truth);orig=np.array(orig);group=np.array(group);split=np.array(split)
cal_data=np.concatenate(cal_features);cal_truth=np.array(cal_truth);cal_orig=np.array(cal_orig);cal_group=np.array(cal_group)
informative=(orig==truth)^(group==truth)
target=(group==truth).astype(float)
for regularization in [1,5,20,50]:
    pred=np.empty(len(truth),int)
    for fold in [0,1]:
        chosen=informative&(split!=fold)
        def objective(weights):
            value=data[chosen]@weights
            loss=np.logaddexp(0,value).sum()-target[chosen]@value+regularization*np.sum(weights[1:]**2)/2
            gradient=data[chosen].T@(expit(value)-target[chosen]);gradient[1:]+=regularization*weights[1:]
            return loss,gradient
        result=minimize(objective,np.zeros(data.shape[1]),jac=True,method='L-BFGS-B')
        pred[split==fold]=np.where(data[split==fold]@result.x>0,group[split==fold],orig[split==fold])
    print('CV',regularization,np.sum(pred!=truth),'min',np.sum(np.where(data[:,1]>0,group,orig)!=truth))
    chosen=informative
    result=minimize(objective,np.zeros(data.shape[1]),jac=True,method='L-BFGS-B')
    cal_pred=np.where(cal_data@result.x>0,cal_group,cal_orig)
    print('CAL',np.sum(cal_pred!=cal_truth),'weights',result.x)
    np.save('meta_'+str(regularization)+'.npy',result.x)
