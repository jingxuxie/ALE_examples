import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize

from optimize import Model, OUTPUT, response, discrepancies


class PoleModel(Model):
    def __init__(self):
        super().__init__()
        data = np.load(OUTPUT/'poles.npz')
        self.pole_values = []
        self.pole_weights = []
        for condition_index in range(3):
            positive = data[f'values_{condition_index}']
            self.pole_values.append(np.concatenate([-positive[::-1],positive]))
            self.pole_weights.append(data[f'weights_{condition_index}'])
        self.energy_scale = .03
        self.weight_scale = 26.5
        self.sqrt_weights = False

    def evaluate(self, pattern, gradient=True, conditions=None):
        if conditions is None:
            conditions = range(3)
        objective = 0.0
        derivative = np.zeros(len(pattern))
        for condition_index in conditions:
            matrix, amplitude = self.matrix(pattern, condition_index)
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr')
            count = len(self.pole_values[condition_index])//2
            selected = np.arange(self.sites-count,self.sites+count)
            vectors = eigenvectors[:, selected]
            weights = np.abs(vectors[self.probes])**2
            difference = eigenvalues[selected] - self.pole_values[condition_index]
            objective += np.mean(difference**2)/self.energy_scale**2 /len(conditions)
            diagonal_gradient = 2*difference / (len(conditions)*len(selected)*self.energy_scale**2)
            if self.sqrt_weights:
                weight_difference = np.sqrt(weights+1e-10)-np.sqrt(self.pole_weights[condition_index]+1e-10)
                coefficient = 2.0 / (len(conditions)*8*self.scale[condition_index])
                objective += np.sum(coefficient*weight_difference**2)
                adjoint = coefficient*weight_difference/np.sqrt(weights+1e-10)
            else:
                weight_difference = weights-self.pole_weights[condition_index]
                coefficient = self.weight_scale / (len(conditions)*8*self.scale[condition_index]**2)
                objective += np.sum(coefficient*weight_difference**2)
                adjoint = 2*coefficient*weight_difference
            if not gradient:
                continue
            transformed = eigenvectors[self.probes].conj().T @ (adjoint * vectors[self.probes])
            denominator = eigenvalues[selected][None,:] - eigenvalues[:,None]
            denominator[selected,np.arange(len(selected))] = 1
            transformed /= denominator
            transformed[selected,np.arange(len(selected))] = 0
            mixed = eigenvectors @ transformed
            mixed += vectors * (diagonal_gradient/2)[None,:]
            diagonal = 2*np.einsum('ij,ij->i',mixed,vectors.conj()).real
            onsite = self.config['pin_potential'] * (diagonal[:self.sites]-diagonal[self.sites:])
            forward = np.einsum('ij,ij->i',mixed[self.edges_source],vectors[self.edges_destination+self.sites].conj()) + np.einsum('ij,ij->i',vectors[self.edges_source],mixed[self.edges_destination+self.sites].conj())
            reverse = np.einsum('ij,ij->i',mixed[self.edges_destination],vectors[self.edges_source+self.sites].conj()) + np.einsum('ij,ij->i',vectors[self.edges_destination],mixed[self.edges_source+self.sites].conj())
            edge_derivative = -2*np.real((forward+reverse).conj()*self.pair[condition_index])
            np.add.at(onsite,self.edges_source,edge_derivative*amplitude[self.edges_destination])
            np.add.at(onsite,self.edges_destination,edge_derivative*amplitude[self.edges_source])
            derivative += onsite[self.candidates]
        self.calls += 1
        budget_error = pattern.sum()-54
        objective += self.budget*budget_error**2 + self.binary*np.mean(pattern*(1-pattern))
        derivative += 2*self.budget*budget_error + self.binary*(1-2*pattern)/len(pattern)
        return objective,derivative


def run(arguments):
    model=PoleModel()
    model.energy_scale=arguments.energy_scale
    model.sqrt_weights=arguments.sqrt_weights
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
    best=np.inf
    start=time.time()
    iteration=0
    prefix=OUTPUT/f'pole_{arguments.seed}'
    def callback(current):
        nonlocal iteration,best
        iteration+=1
        if iteration%20==0:
            loss,_=model.evaluate(current)
            np.save(str(prefix)+'_continuous.npy',current)
            print(arguments.seed,iteration,'elapsed',round(time.time()-start,1),'loss',loss,'sum',current.sum(),'binarity',np.mean(current*(1-current)),flush=True)
        if iteration%100==0:
            observed=response(model.config,current)
            print(arguments.seed,'CONTINUOUS',discrepancies(model.config,observed,model.target),flush=True)
            rounded=model.rounded(current)
            if rounded is not None:
                observed=response(model.config,rounded)
                metrics=discrepancies(model.config,observed,model.target)
                print(arguments.seed,'BINARY',metrics,flush=True)
                if metrics['relative_rmse']<best:
                    best=metrics['relative_rmse']
                    (OUTPUT/f'pole_best_{arguments.seed}.json').write_text(json.dumps({'pattern':rounded.tolist()}))
    for binary,maxiter in json.loads(arguments.stages):
        model.binary=binary
        print(arguments.seed,'STAGE',binary,maxiter,flush=True)
        result=minimize(model.evaluate,pattern,jac=True,method='L-BFGS-B',bounds=[(0,1)]*144,callback=callback,options={'maxiter':maxiter,'ftol':1e-13,'gtol':1e-8,'maxcor':30,'maxls':30})
        pattern=result.x
        np.save(str(prefix)+f'_stage_{binary}.npy',pattern)
        print(arguments.seed,'END',result.message,result.fun,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=201)
    parser.add_argument('--start')
    parser.add_argument('--stages',default='[[0,600],[0.03,300],[0.1,300],[0.4,300]]')
    parser.add_argument('--sqrt-weights',action='store_true')
    parser.add_argument('--energy-scale',type=float,default=.03)
    parser.add_argument('--check',action='store_true')
    arguments=parser.parse_args()
    if arguments.check:
        model=PoleModel()
        pattern=np.random.default_rng(7).uniform(0,1,144)
        start=time.time()
        objective,gradient=model.evaluate(pattern)
        print('time',time.time()-start,'objective',objective,flush=True)
        for index in [0,20,70,100]:
            delta=np.zeros(144)
            delta[index]=1e-5
            numerical=(model.evaluate(pattern+delta)[0]-model.evaluate(pattern-delta)[0])/2e-5
            print(index,gradient[index],numerical,flush=True)
    else:
        run(arguments)
