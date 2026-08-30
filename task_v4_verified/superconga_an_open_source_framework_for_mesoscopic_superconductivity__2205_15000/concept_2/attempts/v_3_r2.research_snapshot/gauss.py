import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares

from pole_optimize import PoleModel
from optimize import OUTPUT, response, discrepancies


class GaussModel(PoleModel):
    def __init__(self):
        super().__init__()
        self.last_pattern = None
        self.last_result = None
        self.raw = False
        self.start_time = time.time()
        self.seed = 0
        self.best = np.inf
        self.jacobian_evaluations = 0
        self.family_strength = 1.0
        self.guard = True
        self.ramp = 0.0

    def physical(self,pattern):
        return pattern/(1+self.ramp*(1-pattern))

    def compute(self, pattern):
        if self.last_pattern is not None and np.array_equal(pattern,self.last_pattern):
            return self.last_result
        self.last_pattern = pattern.copy()
        physical=self.physical(pattern)
        physical_derivative=(1+self.ramp)/(1+self.ramp*(1-pattern))**2
        residuals = []
        jacobians = []
        for condition_index in range(3):
            matrix,amplitude = self.matrix(physical,condition_index)
            eigenvalues,eigenvectors = eigh(matrix,check_finite=False,driver='evr')
            changes = -self.base[condition_index][:self.sites,self.sites:][:,self.candidates] * amplitude[:,None]
            projected = np.zeros((144,4,512),dtype=complex)
            projected[:,0,:] = eigenvectors[self.candidates].conj()
            projected[:,1,:] = eigenvectors[self.candidates+self.sites].conj()
            projected[:,2,:] = (eigenvectors[self.sites:].conj().T @ changes.conj()).T
            projected[:,3,:] = (eigenvectors[:self.sites].conj().T @ changes).T
            coupling = np.array([[6,0,1,0],[0,-6,0,1],[1,0,0,0],[0,1,0,0]],dtype=complex)
            if self.raw:
                resolvent=1/(self.energies[None,:]+.01j-eigenvalues[:,None])
                probe_vectors=eigenvectors[self.probes]
                observed=-(np.abs(probe_vectors)**2 @ resolvent).imag/np.pi
                coefficients=probe_vectors[None,:,None,:]*projected[:,None,:,:]
                left=(coefficients.reshape(-1,512) @ resolvent).reshape(144,8,4,-1).transpose(0,3,1,2)
                right=(coefficients.conj().reshape(-1,512) @ resolvent).reshape(144,8,4,-1).transpose(0,3,2,1)
                jacobian=-np.einsum('nepa,ab,nebp->pen',left,coupling,right).imag/np.pi
                residual=observed-self.target[condition_index]
                if self.sigma:
                    from scipy.ndimage import gaussian_filter1d
                    residual=gaussian_filter1d(residual,self.sigma,axis=1)
                    jacobian=gaussian_filter1d(jacobian,self.sigma,axis=1)
                normalization=self.scale[condition_index]*np.sqrt(3*8*121)
                residuals.append((residual/normalization).ravel())
                jacobians.append((jacobian/normalization[:,:,None]).reshape(-1,144))
            else:
                count=len(self.pole_values[condition_index])//2
                selected=np.arange(self.sites-count,self.sites+count)
                vectors=eigenvectors[:,selected]
                weights=np.abs(vectors[self.probes])**2
                perturbation=(projected.transpose(0,2,1) @ coupling) @ projected[:,:,selected].conj()
                eigen_derivative=perturbation[:,selected,np.arange(2*count)].real.T
                normalization=self.energy_scale*np.sqrt(3*2*count)
                residuals.append((eigenvalues[selected]-self.pole_values[condition_index])/normalization)
                jacobians.append(eigen_derivative/normalization)
                denominator=eigenvalues[selected][None,:]-eigenvalues[:,None]
                denominator[selected,np.arange(2*count)]=1
                perturbation/=denominator[None]
                perturbation[:,selected,np.arange(2*count)]=0
                vector_derivative=eigenvectors[self.probes][None] @ perturbation
                weight_derivative=(2*(vectors[self.probes].conj()[None]*vector_derivative).real).transpose(1,2,0)
                if self.sqrt_weights:
                    coefficient=np.sqrt(2/(3*8*self.scale[condition_index]))
                    residuals.append((coefficient*(np.sqrt(weights+1e-10)-np.sqrt(self.pole_weights[condition_index]+1e-10))).ravel())
                    jacobians.append((coefficient[:,:,None]*weight_derivative/(2*np.sqrt(weights+1e-10)[:,:,None])).reshape(-1,144))
                else:
                    coefficient=np.sqrt(self.weight_scale/(3*8*self.scale[condition_index]**2))
                    residuals.append((coefficient*(weights-self.pole_weights[condition_index])).ravel())
                    jacobians.append((coefficient[:,:,None]*weight_derivative).reshape(-1,144))
            if self.guard:
                guard_index=self.sites+8
                guard_minimum=[.335,.325,.345][condition_index]
                guard_residual=min(0,eigenvalues[guard_index]-guard_minimum)/(.01*np.sqrt(3))
                guard_vector=projected[:,:,guard_index]
                guard_derivative=np.sum((guard_vector @ coupling)*guard_vector.conj(),axis=1).real/(.01*np.sqrt(3))
                residuals.append(np.array([guard_residual]))
                jacobians.append(guard_derivative[None] if guard_residual else np.zeros((1,144)))
        if self.family_strength != 1:
            transformation=np.array([[1,1,1],[0,1,-1],[-2,1,1]],dtype=float)/np.sqrt([3,2,6])[:,None]
            transformation[1]*=self.family_strength
            transformation[2]*=self.family_strength**2
            stacked_residual=np.concatenate(residuals).reshape(3,-1)
            stacked_jacobian=np.concatenate(jacobians).reshape(3,-1,144)
            residuals=[(transformation @ stacked_residual).ravel()]
            jacobians=[np.einsum('ab,bcp->acp',transformation,stacked_jacobian).reshape(-1,144)]
        jacobians=[jacobian*physical_derivative[None,:] for jacobian in jacobians]
        residuals.append(np.array([np.sqrt(self.budget)*(pattern.sum()-54)]))
        jacobians.append(np.full((1,144),np.sqrt(self.budget)))
        if self.binary:
            residuals.append(np.sqrt(self.binary/144)*np.sin(np.pi*pattern)/np.pi)
            jacobians.append(np.diag(np.sqrt(self.binary/144)*np.cos(np.pi*pattern)))
        self.last_result = np.concatenate(residuals),np.concatenate(jacobians)
        return self.last_result

    def fun(self,pattern):
        return self.compute(pattern)[0]

    def jac(self,pattern):
        residual,jacobian=self.compute(pattern)
        self.jacobian_evaluations+=1
        if self.seed and self.jacobian_evaluations%10==0:
            np.save(OUTPUT/f'gauss_{self.seed}_continuous.npy',self.physical(pattern))
            print(self.seed,self.jacobian_evaluations,'elapsed',round(time.time()-self.start_time,1),'loss',np.sum(residual**2),'binarity',np.mean(pattern*(1-pattern)),'sum',pattern.sum(),flush=True)
        if self.seed and self.jacobian_evaluations%40==0:
            observed=response(self.config,self.physical(pattern))
            print(self.seed,'CONTINUOUS',discrepancies(self.config,observed,self.target),flush=True)
            rounded=self.rounded(pattern)
            if rounded is not None:
                observed=response(self.config,rounded)
                metrics=discrepancies(self.config,observed,self.target)
                print(self.seed,'BINARY',metrics,flush=True)
                if metrics['relative_rmse']<self.best:
                    self.best=metrics['relative_rmse']
                    (OUTPUT/f'gauss_best_{self.seed}.json').write_text(json.dumps({'pattern':rounded.tolist()}))
                if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                    (OUTPUT/'design.json').write_text(json.dumps({'pattern':rounded.tolist()}))
                    raise SystemExit(0)
        return jacobian


def run(arguments):
    model=GaussModel()
    model.raw=arguments.raw
    model.sqrt_weights=arguments.sqrt_weights
    model.energy_scale=arguments.energy_scale
    model.family_strength=arguments.family_strength
    model.guard=not arguments.no_guard
    model.ramp=arguments.ramp
    model.budget=arguments.budget
    model.seed=arguments.seed
    random=np.random.default_rng(arguments.seed)
    if arguments.start:
        if arguments.start.endswith('.json'):
            pattern=np.asarray(json.loads(Path(arguments.start).read_text())['pattern'],dtype=float)
        else:
            pattern=np.load(arguments.start)
    else:
        pattern=np.zeros(144)
        pattern[random.choice(144,54,replace=False)]=1
        pattern=pattern*.9+.0375
    pattern=pattern*(1+model.ramp)/(1+model.ramp*pattern)
    for sigma,binary,maxiter in json.loads(arguments.stages):
        model.sigma=sigma
        model.binary=binary
        model.last_pattern=None
        print(arguments.seed,'STAGE',sigma,binary,maxiter,flush=True)
        lower,upper=arguments.bounds
        result=least_squares(model.fun,np.clip(pattern,lower+1e-10,upper-1e-10),jac=model.jac,bounds=(lower,upper),ftol=1e-11,xtol=1e-11,gtol=1e-9,max_nfev=maxiter,x_scale='jac')
        pattern=result.x
        np.save(OUTPUT/f'gauss_{arguments.seed}_stage_{sigma}_{binary}.npy',model.physical(pattern))
        print(arguments.seed,'END',result.message,2*result.cost,flush=True)
    model.jacobian_evaluations=39
    model.jac(pattern)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=301)
    parser.add_argument('--start')
    parser.add_argument('--stages',default='[[0,0,250],[0,0.1,250],[0,0.5,250]]')
    parser.add_argument('--raw',action='store_true')
    parser.add_argument('--sqrt-weights',action='store_true')
    parser.add_argument('--energy-scale',type=float,default=.03)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--bounds',type=float,nargs=2,default=[0,1])
    parser.add_argument('--family-strength',type=float,default=1)
    parser.add_argument('--no-guard',action='store_true')
    parser.add_argument('--ramp',type=float,default=0)
    parser.add_argument('--budget',type=float,default=.002)
    arguments=parser.parse_args()
    if arguments.check:
        model=GaussModel()
        model.raw=arguments.raw
        pattern=np.random.default_rng(7).uniform(0,1,144)
        start=time.time()
        residual,jacobian=model.compute(pattern)
        print('time',time.time()-start,'shape',jacobian.shape,flush=True)
        for index in [0,20,70,100]:
            delta=np.zeros(144)
            delta[index]=1e-5
            numerical=(model.fun(pattern+delta)-model.fun(pattern-delta))/2e-5
            print(index,'error',np.max(abs(numerical-jacobian[:,index])),flush=True)
    else:
        run(arguments)
