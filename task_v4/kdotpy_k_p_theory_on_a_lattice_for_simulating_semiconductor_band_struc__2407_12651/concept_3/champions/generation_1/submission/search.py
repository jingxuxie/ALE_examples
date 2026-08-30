import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares, minimize, linprog
from scipy.special import logsumexp

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/kdotpy_k_p_theory_on_a_lattice_for_simulating_semiconductor_band_struc__2407_12651/concept_3/participant')
sys.path.insert(0, str(ASSETS / 'workspace'))
from model import features, pack, unpack, SPIN_MODES, EVEN_MODES, manufacturing_tail

def grid(mesh=33):
    axis = np.linspace(0, np.pi, mesh)
    horizontal, vertical = np.meshgrid(axis, axis, indexing='ij')
    return horizontal.ravel(), vertical.ravel()

def projection(ratio):
    horizontal, vertical = grid(101)
    axis = np.linspace(-np.pi, np.pi, 128, endpoint=False)
    horizontal, vertical = np.meshgrid(axis, axis, indexing='ij')
    horizontal, vertical = horizontal.ravel(), vertical.ravel()
    offset, basis = features(horizontal, vertical)
    target = offset.copy()
    target[:, 3] = -ratio + np.cos(horizontal) + np.cos(vertical)
    target[:, 1:] /= np.linalg.norm(target[:, 1:], axis=1)[:, None]
    scale = 1 / (2 * np.mean(target[:, 1] * np.sin(horizontal)))
    target *= scale
    params = np.linalg.lstsq(basis.reshape(-1, 30), (target-offset).ravel(), rcond=None)[0]
    return params, scale

BOUNDS = [(-1.9,-.3)] + [(-.75,.75)]*11 + [(-1.5,1.5)]*9 + [(-.75,.75)]*9

class Problem:
    def __init__(self, mesh=33, uv=None):
        self.horizontal, self.vertical = grid(mesh)
        self.offset, self.basis = features(self.horizontal, self.vertical)
        if uv is None:
            uv = [(mass, anisotropy) for mass in [-.05, 0, .05] for anisotropy in [0, .06]]
        self.uv = uv
        self.offsets = np.repeat(self.offset[None], len(uv), axis=0)
        for index, (mass, anisotropy) in enumerate(uv):
            self.offsets[index,:,3] += mass
            self.offsets[index,:,1] += anisotropy*np.sin(self.horizontal)
            self.offsets[index,:,2] -= anisotropy*np.sin(self.vertical)

    def eval(self, params, jac=False):
        values = self.offsets + np.einsum('kdj,j->kd', self.basis, params)[None]
        radius = np.linalg.norm(values[:,:,1:], axis=2)
        lower, upper = values[:,:,0]-radius, values[:,:,0]+radius
        if not jac:
            return lower, upper, 2*radius
        dradius = np.einsum('skd,kdj->skj', values[:,:,1:]/radius[:,:,None], self.basis[:,1:])
        return lower, upper, 2*radius, self.basis[:,0]-dradius, self.basis[:,0]+dradius, 2*dradius

    def metrics(self, params):
        lower, upper, gap = self.eval(params)
        return [np.ptp(lower,axis=1).max(), gap.min(), (upper.min(axis=1)-lower.max(axis=1)).min()]

def nominal_fit(params, support=None, mesh=25):
    if support is None:
        support = np.arange(30)
    problem = Problem(mesh, [(0,0)])
    initial = np.r_[params[support], -problem.eval(params)[0].mean()]
    def residual(vector):
        full = np.zeros(30)
        full[support] = vector[:-1]
        lower, upper, gap = problem.eval(full)
        return np.r_[(lower+vector[-1]).ravel(), 2*np.maximum(3.13-gap,0).ravel()]
    def jac(vector):
        full = np.zeros(30)
        full[support] = vector[:-1]
        lower, upper, gap, dlower, dupper, dgap = problem.eval(full,True)
        return np.vstack([np.column_stack([dlower[0,:,support].T, np.ones(lower.size)]), np.column_stack([-2*dgap[0,:,support].T*(gap[0]<3.13)[:,None],np.zeros(gap.size)])])
    bounds = np.array([BOUNDS[index] for index in support]+[(.5,4)])
    result = least_squares(residual,np.clip(initial,bounds[:,0]+1e-9,bounds[:,1]-1e-9),jac=jac,bounds=(bounds[:,0],bounds[:,1]),max_nfev=200,ftol=1e-10,xtol=1e-10,gtol=1e-10)
    full = np.zeros(30)
    full[support] = result.x[:-1]
    return full, np.linalg.norm(result.fun), result.nfev

def save(params, name):
    Path(name).write_text(json.dumps(unpack(params),indent=2)+'\n')

def robust_fit(params, support, mesh=33, gap_target=3.001, rounds=8, maxiter=160):
    from certify import constants
    support=np.asarray(support)
    params=params.copy()
    params[np.setdiff1d(np.arange(30),support)]=0
    problem=Problem(mesh)
    scenarios=len(problem.uv)
    size=len(support)
    lower,upper,gap=problem.eval(params)
    vector=np.r_[params[support],lower.min(axis=1),lower.max(axis=1),np.ptp(lower,axis=1).max()]
    bounds=[BOUNDS[index] for index in support]+[(None,None)]*(2*scenarios)+[(0,None)]
    points=[[set() for unused in range(scenarios)] for channel in range(3)]
    for turn in range(rounds):
        full=np.zeros(30)
        full[support]=vector[:size]
        lower,upper,gap=problem.eval(full)
        for scenario in range(scenarios):
            for channel,data in enumerate([lower[scenario],-lower[scenario],upper[scenario]]):
                chosen=np.argpartition(data, min(9,len(data)-1))[:10]
                points[channel][scenario].update(chosen.tolist())
        selected=[]
        for channel in range(3):
            scenario_index=[]
            point_index=[]
            for scenario in range(scenarios):
                point_index.extend(sorted(points[channel][scenario]))
                scenario_index.extend([scenario]*len(points[channel][scenario]))
            selected.append((np.array(scenario_index),np.array(point_index)))
        reference_gap=max(gap.min(),2.)
        last_vector=None
        cache=None
        def values(candidate):
            nonlocal last_vector,cache
            if last_vector is not None and np.array_equal(candidate,last_vector):
                return cache
            full=np.zeros(30)
            full[support]=candidate[:size]
            correction=constants(full,reference_gap)['correction']
            derivative=np.zeros(size)
            for index in range(size):
                shifted=full.copy()
                shifted[support[index]]+=1e-6
                derivative[index]=(constants(shifted,reference_gap)['correction']-correction)/1e-6
            constraints=[]
            jacobians=[]
            for channel,(scenario_index,point_index) in enumerate(selected):
                basis=problem.basis[point_index]
                components=problem.offsets[scenario_index,point_index]+np.einsum('kdj,j->kd',basis,full)
                radius=np.linalg.norm(components[:,1:],axis=1)
                dradius=np.einsum('kd,kdj->kj',components[:,1:]/radius[:,None],basis[:,1:,support])
                ds=basis[:,0,support]
                matrix=np.zeros((len(point_index),len(candidate)))
                rows=np.arange(len(point_index))
                if channel==0:
                    value=components[:,0]-radius-candidate[size+scenario_index]
                    matrix[:,:size]=ds-dradius
                    matrix[rows,size+scenario_index]=-1
                elif channel==1:
                    value=candidate[size+scenarios+scenario_index]-components[:,0]+radius
                    matrix[:,:size]=-ds+dradius
                    matrix[rows,size+scenarios+scenario_index]=1
                else:
                    value=components[:,0]+radius-candidate[size+scenarios+scenario_index]-gap_target-correction
                    matrix[:,:size]=ds+dradius-derivative
                    matrix[rows,size+scenarios+scenario_index]=-1
                constraints.extend(value)
                jacobians.extend(matrix)
            value=candidate[-1]-candidate[size+scenarios:size+2*scenarios]+candidate[size:size+scenarios]
            matrix=np.zeros((scenarios,len(candidate)))
            rows=np.arange(scenarios)
            matrix[rows,size+rows]=1
            matrix[rows,size+scenarios+rows]=-1
            matrix[:,-1]=1
            constraints.extend(value)
            jacobians.extend(matrix)
            objective=candidate[-1]+correction
            gradient=np.r_[derivative,np.zeros(2*scenarios),1.]
            cache=(objective,gradient,np.array(constraints),np.array(jacobians))
            last_vector=candidate.copy()
            return cache
        result=minimize(lambda candidate:values(candidate)[0],vector,jac=lambda candidate:values(candidate)[1],method='SLSQP',bounds=bounds,constraints={'type':'ineq','fun':lambda candidate:values(candidate)[2],'jac':lambda candidate:values(candidate)[3]},options={'maxiter':maxiter,'ftol':2e-10})
        vector=result.x
        full=np.zeros(30)
        full[support]=vector[:size]
        metrics=problem.metrics(full)
        correction=constants(full,metrics[1])['correction']
        violation=max(metrics[0]-vector[-1],gap_target+correction-metrics[2])
        if violation<2e-6:
            break
    return full, [metrics[0]+correction, metrics[1]-correction, metrics[2]-correction], (result.success,result.message,turn)

if __name__ == '__main__':
    problem=Problem(49)
    for ratio in [.7,1.,1.3,1.5,1.7]:
        params, scale = projection(ratio)
        print('PROJ',ratio,scale,problem.metrics(params),flush=True)
        params, cost, count = nominal_fit(params)
        print('FIT',ratio,cost,count,problem.metrics(params),flush=True)
        print(np.round(params,5),flush=True)
        save(params, f'fit_{ratio}.json')
