import os
import sys
import time

STARTED=time.monotonic()

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
os.environ['NUMEXPR_NUM_THREADS']='1'
sys.dont_write_bytecode=True

import json
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
import runtime_features
import fast_exact
import baseline_features

ROOT=Path(__file__).resolve().parent

def predict_model(inputs,descriptors,model,uncertainty=None):
    predictions=np.empty((len(descriptors),2))
    prefixes=[key[:-6] for key in model if key.endswith('offset')]
    for prefix in prefixes:
        parts=prefix.rstrip('_').split('_')
        family,size,target=(int(part[1:]) for part in parts)
        selected=inputs['family']==family
        if size:
            selected&=inputs['n_sites']==size
        if not np.any(selected):
            continue
        active=model[prefix+'active'].astype(int)
        transformed=(descriptors[selected][:,active]-model[prefix+'offset'][active])/model[prefix+'scale'][active]
        weights=model[prefix+'weights']
        training=model[prefix+'train']
        distances=np.sum(transformed**2*weights,axis=1)[:,None]+np.sum(training**2*weights,axis=1)[None,:]-2*(transformed*weights)@training.T
        distances=np.maximum(distances,0.)
        kind=str(model[prefix+'kernel']) if prefix+'kernel' in model else 'rbf'
        if kind=='matern':
            radius=np.sqrt(5*distances)
            kernel=(1+radius+radius**2/3)*np.exp(-radius)
        else:
            kernel=np.exp(-0.5*distances)
        predicted=float(model[prefix+'amplitude'])*kernel@model[prefix+'dual']+float(model[prefix+'mean'])
        if uncertainty is not None and target==0 and prefix+'chol' in model:
            cross=float(model[prefix+'amplitude'])*kernel
            projected=solve_triangular(model[prefix+'chol'],cross.T,lower=True,check_finite=False)
            uncertainty[selected]=np.maximum(float(model[prefix+'amplitude'])-np.sum(projected**2,axis=0),0)*float(model[prefix+'output_scale'])**2
        prior=str(model[prefix+'prior'])
        if prior=='physics':
            predicted+=descriptors[selected,88 if target==0 else 85]
        elif prior=='active':
            predicted+=descriptors[selected,104 if target==0 else 105]
        elif prior=='block':
            predicted+=descriptors[selected,115 if target==0 else 116]
        elif target==1 and prior=='hybrid4':
            predicted+=descriptors[selected,111]
        elif target==1 and prior=='hybrid6':
            predicted+=descriptors[selected,116]
        elif target==1 and prior=='hybridpt':
            predicted+=descriptors[selected,175]
        predictions[selected,target]=predicted
    return predictions

def main():
    request=json.loads(Path(sys.argv[1]).read_text())
    with np.load(request['inputs'],allow_pickle=False) as archive:
        inputs={key:archive[key] for key in ('hopping','interaction','potential','n_sites','family')}
    configuration=json.loads((ROOT/'config.json').read_text())
    full_inputs=inputs
    large=inputs['n_sites']!=10 if configuration.get('exact_small',False) else np.ones(len(inputs['n_sites']),dtype=bool)
    inputs={key:value[large] for key,value in full_inputs.items()}
    descriptors=runtime_features.features(inputs,configuration['features'])
    predictions=np.zeros((len(descriptors),2))
    total_weights=np.zeros_like(predictions)
    uncertainty=np.zeros(len(descriptors))
    for specification in configuration['models']:
        with np.load(ROOT/specification['path'],allow_pickle=False) as archive:
            model=dict(archive)
        current_uncertainty=np.zeros(len(descriptors))
        predicted=predict_model(inputs,descriptors,model,current_uncertainty if configuration.get('refine',0) else None)
        weights=np.asarray(specification['weights'],dtype=float)
        if weights.ndim==2:
            weights=weights[inputs['family']]
        predictions+=predicted*weights
        uncertainty+=current_uncertainty*(weights[:,0] if weights.ndim==2 else weights[0])
        total_weights+=np.broadcast_to(weights,predictions.shape)
    predictions/=total_weights
    predictions[:,1]=np.maximum(predictions[:,1],0.)
    if not np.all(large):
        combined=np.empty((len(large),2))
        combined[large]=predictions
        small_inputs={key:value[~large] for key,value in full_inputs.items()}
        with np.load(ROOT/'baseline_model.npz',allow_pickle=False) as archive:
            baseline=dict(archive)
        combined[~large]=baseline_features.predict(small_inputs,baseline)
        small_descriptors=baseline_features.features(small_inputs)
        novelty=np.zeros(len(small_descriptors))
        for family in range(4):
            selected=small_inputs['family']==family
            if not np.any(selected):
                continue
            prefix=f'f{family}_n10_'
            transformed=(small_descriptors[selected]-baseline[prefix+'offset'])/baseline[prefix+'scale']
            similarities=baseline_features.kernel(transformed,baseline[prefix+'train'],float(baseline[prefix+'gamma']))
            novelty[selected]=1-np.max(similarities,axis=1)
        fast_exact.LIBRARY.set_limits(24.0,STARTED+23.5)
        small_indices=np.flatnonzero(~large)
        for local_index in np.argsort(-novelty):
            index=small_indices[local_index]
            sites=int(full_inputs['n_sites'][index])
            result=fast_exact.calculate(full_inputs['hopping'][index,:sites,:sites],full_inputs['interaction'][index,:sites],full_inputs['potential'][index,:sites])
            if fast_exact.LIBRARY.timed_out() or not np.isfinite(result).all():
                break
            combined[index]=result
        predictions=combined
        if configuration.get('refine',0) and not fast_exact.LIBRARY.timed_out():
            large_indices=np.flatnonzero(large)
            for local_index in np.argsort(-uncertainty)[:configuration['refine']]:
                index=large_indices[local_index]
                sites=int(full_inputs['n_sites'][index])
                result=fast_exact.calculate(full_inputs['hopping'][index,:sites,:sites],full_inputs['interaction'][index,:sites],full_inputs['potential'][index,:sites],steps=100)
                if fast_exact.LIBRARY.timed_out() or not np.isfinite(result).all():
                    break
                predictions[index]=result
    if predictions.shape!=(request['n_instances'],2) or not np.isfinite(predictions).all():
        raise ValueError('Invalid predictions')
    result={'schema_version':1,'predictions':predictions.tolist()}
    Path(sys.argv[2]).write_text(json.dumps(result,allow_nan=False,separators=(',',':'))+'\n')

if __name__=='__main__':
    main()
