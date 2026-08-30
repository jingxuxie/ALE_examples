import argparse
from pathlib import Path
import json
import numpy as np
from scipy.linalg import cho_factor,cho_solve
from train_models import make_features
from solver import predict_model

def load_split(name,perturb):
    data=dict(np.load('dev/'+name+'.npz'))
    saved=dict(np.load('dev/'+name+'_features.npz'))
    if name in ('train','validation'):
        for key in ('active','block','meanfield'):
            saved[key]=np.load('dev/'+name+'_'+key+'.npy')
    if perturb:
        saved['perturb']=np.load('dev/'+name+'_perturb.npy')
    count=min(len(value) for value in saved.values())
    return {key:value[:count] for key,value in data.items()},{key:value[:count] for key,value in saved.items()}

def kernel(left,right,weights,amplitude,kind):
    distances=np.maximum(np.sum(left**2*weights,axis=1)[:,None]+np.sum(right**2*weights,axis=1)[None,:]-2*(left*weights)@right.T,0.)
    if kind=='matern':
        radius=np.sqrt(5*distances)
        return amplitude*(1+radius+radius**2/3)*np.exp(-radius)
    return amplitude*np.exp(-0.5*distances)

def prior_values(features,prior,target):
    if prior=='physics': return features[:,88 if target==0 else 85]
    if prior=='active': return features[:,104 if target==0 else 105]
    if prior=='block': return features[:,115 if target==0 else 116]
    if target==1 and prior=='hybrid4': return features[:,111]
    if target==1 and prior=='hybrid6': return features[:,116]
    if target==1 and prior=='hybridpt': return features[:,175]
    return np.zeros(len(features))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',required=True)
    parser.add_argument('--extra',default='extra,extra2')
    parser.add_argument('--output',required=True)
    parser.add_argument('--perturb',action='store_true')
    parser.add_argument('--validation-training',action='store_true')
    arguments=parser.parse_args()
    training,saved=load_split('train',arguments.perturb)
    validation,saved_validation=load_split('validation',arguments.perturb)
    names=arguments.extra.split(',') if arguments.extra else []
    if arguments.validation_training: names.append('validation')
    for name in names:
        additional,additional_saved=load_split(name,arguments.perturb)
        training={key:np.concatenate([training[key],additional[key]]) for key in training}
        saved={key:np.concatenate([saved[key],additional_saved[key]]) for key in saved}
    train_features=make_features(training,saved)
    validation_features=make_features(validation,saved_validation)
    seed=dict(np.load(arguments.seed))
    models={multiplier:{} for multiplier in (0.5,1.,2.,4.)}
    for prefix in [key[:-6] for key in seed if key.endswith('offset')]:
        family,size,target=(int(part[1:]) for part in prefix.rstrip('_').split('_'))
        selected=(training['family']==family)&((training['n_sites']==size) if size else True)
        active=seed[prefix+'active'].astype(int)
        transformed=(train_features[selected][:,active]-seed[prefix+'offset'][active])/seed[prefix+'scale'][active]
        weights=seed[prefix+'weights']
        amplitude=float(seed[prefix+'amplitude'])
        kind=str(seed.get(prefix+'kernel','rbf'))
        prior=str(seed[prefix+'prior'])
        labels=training['gaps'][selected,target]-prior_values(train_features[selected],prior,target)
        mean=float(seed[prefix+'mean'])
        old_train=seed[prefix+'train']
        old_dual=seed[prefix+'dual']
        old_kernel=kernel(old_train,old_train,weights,amplitude,kind)
        remainder=labels[:len(old_train)]-mean-old_kernel@old_dual
        noise=max(float(np.dot(old_dual,remainder)/np.dot(old_dual,old_dual)),1e-8)
        output_scale=np.std(labels[:len(old_train)])
        floor=(0.004/output_scale)**2
        matrix=kernel(transformed,transformed,weights,amplitude,kind)
        for multiplier,artifact in models.items():
            reg=max(noise*multiplier,floor)
            diagonal=np.diag_indices(len(matrix))
            matrix[diagonal]+=reg
            factor=cho_factor(matrix,lower=True,check_finite=False)
            dual=cho_solve(factor,labels-mean,check_finite=False)
            matrix[diagonal]-=reg
            artifact.update({key:value for key,value in seed.items() if key.startswith(prefix)})
            artifact[prefix+'train']=transformed
            artifact[prefix+'dual']=dual
            artifact[prefix+'noise']=reg
            artifact[prefix+'output_scale']=output_scale
            if target==0:
                artifact[prefix+'chol']=np.tril(factor[0])
        print(prefix,'rows',len(labels),'noise',noise,'scale',output_scale,flush=True)
    for multiplier,artifact in models.items():
        suffix=str(multiplier).replace('.','p')
        name=arguments.output+'_m'+suffix
        predicted=predict_model(validation,validation_features,artifact)
        np.savez_compressed('dev/'+name+'_model.npz',**artifact)
        np.save('dev/'+name+'_predictions.npy',predicted)
        residual=predicted-validation['gaps']
        residual[validation['n_sites']==10]=0
        report={'training_examples':len(training['gaps']),'hybrid_overall':np.sqrt(np.mean(residual**2,axis=0)).tolist(),'hybrid_families':[np.sqrt(np.mean(residual[validation['family']==family]**2,axis=0)).tolist() for family in range(4)]}
        Path('dev/'+name+'_report.json').write_text(json.dumps(report,indent=2))
        print(name,report,flush=True)
