import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy.linalg import eigh

from pole_optimize import PoleModel
from optimize import OUTPUT,response,discrepancies

torch.set_num_threads(1)


def run(arguments):
    model=PoleModel()
    random=np.random.default_rng(arguments.seed)
    if arguments.start:
        if arguments.start.endswith('.json'):
            pattern=np.asarray(json.loads(Path(arguments.start).read_text())['pattern'],dtype=float)
        else:
            pattern=np.load(arguments.start)
    else:
        pattern=np.zeros(144)
        pattern[random.choice(144,54,replace=False)]=1
        pattern=.05+.866666666667*pattern
    vector_list=[]
    for condition_index in range(3):
        matrix,_=model.matrix(pattern,condition_index)
        eigenvalues,eigenvectors=eigh(matrix,check_finite=False,driver='evr')
        vector_list.append(eigenvectors[:,248:264])
    complex_dtype=torch.complex128
    real_dtype=torch.float64
    vectors=torch.nn.Parameter(torch.tensor(np.array(vector_list),dtype=complex_dtype))
    material=torch.nn.Parameter(torch.tensor(pattern,dtype=real_dtype))
    hopping=torch.tensor(np.array([base[:256,:256] for base in model.base]),dtype=complex_dtype)
    pairing=torch.tensor(np.array([base[:256,256:] for base in model.base]),dtype=complex_dtype)
    target_values=torch.tensor(np.array(model.pole_values),dtype=real_dtype)[:,None,:]
    target_weights=torch.tensor(np.array(model.pole_weights),dtype=real_dtype)
    scales=torch.tensor(model.scale,dtype=real_dtype)
    candidates=torch.tensor(model.candidates,dtype=torch.int64)
    probes=torch.tensor(model.probes,dtype=torch.int64)
    identity=torch.eye(16,dtype=complex_dtype)[None]
    optimizer=torch.optim.Adam([{'params':[vectors],'lr':arguments.vector_lr},{'params':[material],'lr':arguments.material_lr}])
    best=np.inf
    start=time.time()
    iteration=0
    for pde_weight,binary_weight,count in json.loads(arguments.stages):
        print(arguments.seed,'STAGE',pde_weight,binary_weight,count,flush=True)
        for stage_iteration in range(count):
            iteration+=1
            optimizer.zero_grad(set_to_none=True)
            normal=torch.zeros(256,dtype=real_dtype)
            normal[candidates]=material
            amplitude=(1-normal)[None,:,None]
            electron=vectors[:,:256]
            hole=vectors[:,256:]
            electron_response=hopping@electron+6*normal[None,:,None]*electron+amplitude*(pairing@(amplitude*hole))
            hole_response=-hopping.conj()@hole-6*normal[None,:,None]*hole+amplitude*(pairing.conj()@(amplitude*electron))
            residual=torch.cat([electron_response,hole_response],dim=1)-vectors*target_values
            pde_loss=torch.mean(torch.sum(torch.abs(residual)**2,dim=1))
            weights=torch.abs(vectors[:,probes])**2
            data_loss=26.5*torch.sum(((weights-target_weights)/scales)**2)/(3*8)
            gram=vectors.conj().transpose(1,2)@vectors
            orthogonal_loss=torch.sum(torch.abs(gram-identity)**2)/(3*16)
            binary_loss=torch.mean(material*(1-material))
            budget_loss=(torch.sum(material)-54)**2
            loss=pde_weight*pde_loss+data_loss+arguments.ortho*orthogonal_loss+binary_weight*binary_loss+.01*budget_loss
            loss.backward()
            if arguments.project:
                with torch.no_grad():
                    inner=vectors.conj().transpose(1,2)@vectors.grad
                    vectors.grad-=vectors@((inner+inner.conj().transpose(1,2))/2)
            optimizer.step()
            with torch.no_grad():
                material.clamp_(0,1)
                if arguments.project and iteration%10==0:
                    gram=vectors.conj().transpose(1,2)@vectors
                    values,basis=torch.linalg.eigh(gram)
                    inverse=basis@torch.diag_embed(values.rsqrt().to(complex_dtype))@basis.conj().transpose(1,2)
                    vectors.copy_(vectors@inverse)
            if iteration%100==0:
                current=material.detach().numpy().copy()
                np.save(OUTPUT/f'lifted_{arguments.seed}_continuous.npy',current)
                print(arguments.seed,iteration,'elapsed',round(time.time()-start,1),'loss',loss.item(),'pde',pde_loss.item(),'data',data_loss.item(),'ortho',orthogonal_loss.item(),'binary',binary_loss.item(),'sum',current.sum(),flush=True)
            if iteration%1000==0 or stage_iteration==count-1:
                current=material.detach().numpy().copy()
                observed=response(model.config,current)
                print(arguments.seed,'CONTINUOUS',discrepancies(model.config,observed,model.target),flush=True)
                rounded=model.rounded(current)
                if rounded is not None:
                    observed=response(model.config,rounded)
                    metrics=discrepancies(model.config,observed,model.target)
                    print(arguments.seed,'BINARY',metrics,flush=True)
                    if metrics['relative_rmse']<best:
                        best=metrics['relative_rmse']
                        (OUTPUT/f'lifted_best_{arguments.seed}.json').write_text(json.dumps({'pattern':rounded.tolist()}))
                    if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                        (OUTPUT/'design.json').write_text(json.dumps({'pattern':rounded.tolist()}))
                        return
        for group in optimizer.param_groups:
            group['lr']*=.7


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=501)
    parser.add_argument('--start')
    parser.add_argument('--stages',default='[[1,0,1500],[10,0.05,2000],[100,0.1,2000],[1000,0.5,2000],[10000,1,2000]]')
    parser.add_argument('--project',action='store_true')
    parser.add_argument('--ortho',type=float,default=10)
    parser.add_argument('--vector-lr',type=float,default=.002)
    parser.add_argument('--material-lr',type=float,default=.01)
    run(parser.parse_args())
