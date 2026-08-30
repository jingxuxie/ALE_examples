import argparse
import json
import time
from pathlib import Path
from multiprocessing import Pool
import numpy as np
import geometry_features
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

def make_features(data, saved):
    perturb=saved.get('perturb',np.zeros((len(data['gaps']),20)))
    return np.column_stack([saved['basic'],saved['physics'],saved['active'],saved['block'],saved['meanfield'],geometry_features.features(data),perturb])

def run_job(job):
    family,size,target,train_x,train_y,test_x,test_y,prior,steps,kind,noise_floor = job
    offset = train_x.mean(0)
    scale = train_x.std(0)
    active = np.flatnonzero(scale > 1e-8)
    scale[scale < 1e-8] = 1
    train_x = ((train_x-offset)/scale)[:,active]
    test_x = ((test_x-offset)/scale)[:,active]
    mean = train_y.mean()
    output_scale = train_y.std()
    labels = (train_y-mean)/output_scale
    count,dimensions = train_x.shape
    distances = (train_x[:,None,:]-train_x[None,:,:])**2
    distances = np.ascontiguousarray(distances.transpose(2,0,1))
    identity = np.eye(count)
    def objective(parameters):
        amplitude = np.exp(parameters[0])
        weights = np.exp(parameters[1:-1])
        noise = np.exp(parameters[-1])
        distance=np.einsum('k,kij->ij',weights,distances)
        if kind=='matern':
            radius=np.sqrt(5*distance)
            matrix=amplitude*(1+radius+radius**2/3)*np.exp(-radius)
        else:
            matrix=amplitude*np.exp(-0.5*distance)
        factor = cho_factor(matrix+(noise+1e-8)*identity,lower=True,check_finite=False)
        dual = cho_solve(factor,labels,check_finite=False)
        loss = 0.5*np.dot(labels,dual)+np.log(np.diag(factor[0])).sum()+0.5*count*np.log(2*np.pi)
        derivative = cho_solve(factor,identity,check_finite=False)-np.outer(dual,dual)
        combined = derivative*matrix
        if kind=='matern':
            weighted_gradient=-5/12*weights*np.einsum('ij,kij->k',derivative*amplitude*(1+radius)*np.exp(-radius),distances)
        else:
            weighted_gradient=-0.25*weights*np.einsum('ij,kij->k',combined,distances)
        gradient = np.r_[0.5*combined.sum(),weighted_gradient,0.5*noise*np.trace(derivative)]
        penalty = 0.02*np.sum((parameters[1:-1]+4)**2)
        gradient[1:-1] += 0.04*(parameters[1:-1]+4)
        return loss+penalty,gradient
    initial = np.r_[0.,np.full(dimensions,-4.),-6.]
    lower_noise=max(-13,2*np.log(max(noise_floor,1e-9)/output_scale))
    initial[-1]=max(initial[-1],lower_noise)
    optimized = minimize(objective, initial, jac=True, method='L-BFGS-B',bounds=[(-4,6)]+[(-14,3)]*dimensions+[(lower_noise,0)],options={'maxiter':steps,'ftol':1e-8})
    parameters = optimized.x
    amplitude = np.exp(parameters[0])
    weights = np.exp(parameters[1:-1])
    noise = np.exp(parameters[-1])
    distance=np.einsum('k,kij->ij',weights,distances)
    if kind=='matern':
        radius=np.sqrt(5*distance)
        matrix=amplitude*(1+radius+radius**2/3)*np.exp(-radius)
    else:
        matrix=amplitude*np.exp(-0.5*distance)
    dual = cho_solve(cho_factor(matrix+(noise+1e-8)*identity,lower=True),labels)
    cross = np.sum((test_x[:,None,:]-train_x[None,:,:])**2*weights,axis=2)
    if kind=='matern':
        radius=np.sqrt(5*cross)
        cross_kernel=amplitude*(1+radius+radius**2/3)*np.exp(-radius)
    else:
        cross_kernel=amplitude*np.exp(-0.5*cross)
    predictions = cross_kernel@dual*output_scale+mean
    errors = np.sqrt(np.mean((predictions-test_y)**2))
    ranked = sorted(zip(weights,active),reverse=True)[:12]
    print('fit',family,size,target,'rmse',round(errors,5),'noise',round(np.sqrt(noise)*output_scale,5),'nit',optimized.nit,'features',[(int(index),round(value,2)) for value,index in ranked],flush=True)
    artifact = {'offset':offset,'scale':scale,'active':active,'train':train_x,'weights':weights,'amplitude':amplitude,'dual':dual*output_scale,'mean':mean,'prior':prior,'kernel':kind}
    return family,size,target,artifact,predictions,errors

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--group-size',action='store_true')
    parser.add_argument('--prior',default='physics')
    parser.add_argument('--steps',default=180,type=int)
    parser.add_argument('--output',default='ard')
    parser.add_argument('--selection',default='all')
    parser.add_argument('--extra',default='')
    parser.add_argument('--workers',default=2,type=int)
    parser.add_argument('--kernel',default='rbf')
    parser.add_argument('--noise-floor',default=0.,type=float)
    parser.add_argument('--corrected',action='store_true')
    parser.add_argument('--perturb',action='store_true')
    arguments=parser.parse_args()
    training=dict(np.load('dev/train.npz'))
    validation=dict(np.load('dev/validation.npz'))
    saved_train=dict(np.load('dev/train_features.npz'))
    saved_test=dict(np.load('dev/validation_features.npz'))
    saved_train['active']=np.load('dev/train_active.npy')
    saved_test['active']=np.load('dev/validation_active.npy')
    for name in ('block','meanfield'):
        saved_train[name]=np.load('dev/train_'+name+'.npy')
        saved_test[name]=np.load('dev/validation_'+name+'.npy')
    if arguments.corrected:
        saved_train['block']=np.load('dev/train_corrected.npy')
        saved_test['block']=np.load('dev/validation_corrected.npy')
    if arguments.perturb:
        saved_train['perturb']=np.load('dev/train_perturb.npy')
        saved_test['perturb']=np.load('dev/validation_perturb.npy')
    if arguments.extra:
        for extra in arguments.extra.split(','):
            additional=dict(np.load('dev/'+extra+'.npz'))
            additional_features=dict(np.load('dev/'+extra+'_features.npz'))
            if arguments.perturb:
                additional_features['perturb']=np.load('dev/'+extra+'_perturb.npy')
            if arguments.corrected:
                additional_features['block']=np.load('dev/'+extra+'_corrected.npy')
                count=len(additional_features['block'])
                additional={key:value[:count] for key,value in additional.items()}
                additional_features={key:value[:count] for key,value in additional_features.items()}
            count=min(len(value) for value in additional_features.values())
            additional={key:value[:count] for key,value in additional.items()}
            additional_features={key:value[:count] for key,value in additional_features.items()}
            for key in training:
                training[key]=np.concatenate([training[key],additional[key]])
            for key in saved_train:
                saved_train[key]=np.concatenate([saved_train[key],additional_features[key]])
    train_x=make_features(training,saved_train)
    test_x=make_features(validation,saved_test)
    excluded=[]
    if arguments.selection in ('lean','leaner','minimal','leanerfast'):
        excluded.extend(range(115,137))
    if arguments.selection in ('leaner','minimal','leanerfast'):
        excluded.extend(range(104,109))
    if arguments.selection=='minimal':
        excluded.extend(range(84,96))
    if arguments.selection=='six':
        excluded.extend(range(104,109))
        excluded.extend(range(110,115))
        excluded.extend(range(120,137))
    if arguments.selection in ('perturb','perturbfast'):
        excluded.extend(range(104,137))
    if arguments.selection in ('leanfast','leanerfast','perturbfast'):
        excluded.extend(range(89,94))
    if arguments.selection=='leanfast':
        excluded.extend(range(115,137))
    train_x[:,excluded]=0
    test_x[:,excluded]=0
    prior_train=np.zeros_like(training['gaps'])
    prior_test=np.zeros_like(validation['gaps'])
    if arguments.prior == 'physics':
        prior_train=saved_train['physics'][:,[4,1]]
        prior_test=saved_test['physics'][:,[4,1]]
    elif arguments.prior == 'active':
        prior_train=saved_train['active'][:,[8,9]]
        prior_test=saved_test['active'][:,[8,9]]
    elif arguments.prior == 'block':
        prior_train=saved_train['block'][:,[6,7]]
        prior_test=saved_test['block'][:,[6,7]]
    elif arguments.prior == 'hybrid4':
        prior_train[:,1]=saved_train['block'][:,2]
        prior_test[:,1]=saved_test['block'][:,2]
    elif arguments.prior == 'hybrid6':
        prior_train[:,1]=saved_train['block'][:,7]
        prior_test[:,1]=saved_test['block'][:,7]
    elif arguments.prior == 'hybridpt':
        prior_train[:,1]=saved_train['perturb'][:,12]
        prior_test[:,1]=saved_test['perturb'][:,12]
    jobs=[]
    for family in range(4):
        for size in ((10,12) if arguments.group_size else (0,)):
            train_mask=(training['family']==family)&((training['n_sites']==size) if size else True)
            test_mask=(validation['family']==family)&((validation['n_sites']==size) if size else True)
            for target in range(2):
                jobs.append((family,size,target,train_x[train_mask],training['gaps'][train_mask,target]-prior_train[train_mask,target],test_x[test_mask],validation['gaps'][test_mask,target]-prior_test[test_mask,target],arguments.prior,arguments.steps,arguments.kernel,arguments.noise_floor))
    started=time.perf_counter()
    artifact={}
    predictions=np.zeros_like(validation['gaps'])
    with Pool(arguments.workers) as workers:
        for family,size,target,model,predicted,error in workers.imap_unordered(run_job,jobs):
            prefix=f'f{family}_n{size}_t{target}_'
            artifact.update({prefix+key:value for key,value in model.items()})
            selected=(validation['family']==family)&((validation['n_sites']==size) if size else True)
            predictions[selected,target]=predicted+prior_test[selected,target]
    np.savez_compressed('dev/'+arguments.output+'_model.npz',**artifact)
    np.save('dev/'+arguments.output+'_predictions.npy',predictions)
    residual=predictions-validation['gaps']
    report={'overall':np.sqrt(np.mean(residual**2,0)).tolist(),'families':[np.sqrt(np.mean(residual[validation['family']==family]**2,0)).tolist() for family in range(4)],'seconds':time.perf_counter()-started}
    Path('dev/'+arguments.output+'_report.json').write_text(json.dumps(report,indent=2))
    print(report,flush=True)

if __name__=='__main__':
    main()
