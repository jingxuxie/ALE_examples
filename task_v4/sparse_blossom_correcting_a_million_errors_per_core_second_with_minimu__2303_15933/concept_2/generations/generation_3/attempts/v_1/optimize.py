import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
import ctypes
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

PARTICIPANT = Path(os.environ['P'])
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
import check

LIB = ctypes.CDLL(str(Path(__file__).with_name('oracle.so')))
POINTER = ctypes.POINTER(ctypes.c_double)
LIB.infer.argtypes = [ctypes.c_int, POINTER, ctypes.c_int, ctypes.c_int, POINTER, POINTER, ctypes.c_void_p]

def oracle(rates, syndrome, physical=0, gradients=True):
    rates = np.ascontiguousarray(rates, dtype=np.float64)
    values = np.empty((len(rates), 3))
    jacobian = np.empty((len(rates), 3, 39)) if gradients else None
    masks = np.empty((len(rates), 2), dtype=np.uint64)
    LIB.infer(len(rates), rates.ctypes.data_as(POINTER), sum(1 << detector for detector in syndrome), physical,
              values.ctypes.data_as(POINTER), jacobian.ctypes.data_as(POINTER) if gradients else None, masks.ctypes.data)
    return values, jacobian, masks

class Problem:
    def __init__(self, data):
        self.data = data
        self.syndrome = data['syndrome']
        self.groups = check.calibrations(data)
        self.sparse = bool(int(os.environ.get('SPARSE','0')))
        self.keep_all = bool(int(os.environ.get('KEEPALL','0')))
        if self.sparse:
            for index,group in enumerate(self.groups):
                group['parameters'] = [.95,1.,1.05] if index==0 else ([-.05,0.,.05] if index<45 else [-.05,-.0475,0.,.0475,.05])
        self.global_count = len(self.groups[0]['parameters'])
        self.raw = np.array([group['levels'] for group in self.groups[1:]])
        self.background = np.array([group['background_scale'] for group in self.groups[1:]])
        self.parameters = np.concatenate([group['parameters'] for group in self.groups])
        self.group_index = np.concatenate([np.full(len(group['parameters']), index) for index, group in enumerate(self.groups)])
        self.starts = np.r_[0,np.cumsum([len(group['parameters']) for group in self.groups])]
        self.physical = int(check.frontier(data['probabilities'], self.syndrome)[1][1] < check.frontier(data['probabilities'], self.syndrome)[1][0])
        self.targets = np.array([[group['targets']['gap'],np.log(group['targets']['opposite_posterior']/(1-group['targets']['opposite_posterior'])),group['targets']['syndrome_probability']] for group in self.groups])
        self.last_x = None
        self.calls = 0
        self.best = -1e10
        self.started = time.time()
        self.temperature = float(os.environ.get('TEMPERATURE','0'))
        self.opposite_masks = np.empty(0,dtype=np.uint64)
        self.save_path = Path('best.json')
        self.verbose = True
        self.best_p = None

    def evaluate(self, probabilities):
        total = probabilities.sum()
        means = self.raw @ probabilities / total
        centered = self.raw - means[:,None]
        extrema = np.argmax(np.abs(centered),axis=1)
        maximum = np.abs(centered[np.arange(130),extrema])
        signs = np.sign(centered[np.arange(130),extrema])
        levels = centered / maximum[:,None]
        mean_jac = centered / total
        rank = (-1 + levels * signs[:,None]) / maximum[:,None]
        point_group = np.maximum(self.group_index-1,0)
        point_levels = levels[point_group]
        point_background = self.background[point_group]
        factors = point_background[:,None] * (1+self.parameters[:,None]*point_levels)
        factors[:self.global_count] = self.parameters[:self.global_count,None]
        rates = factors * probabilities
        values, rate_jac, masks = oracle(rates,self.syndrome,self.physical)
        if self.temperature:
            self.opposite_masks = np.union1d(self.opposite_masks,masks[:,1])
            bits = ((self.opposite_masks[:,None] >> np.arange(39,dtype=np.uint64))&1).astype(float)
            physical_bits = ((masks[:,0,None] >> np.arange(39,dtype=np.uint64))&1).astype(float)
            weights = np.log1p(-rates)-np.log(rates)
            energies = weights @ bits.T
            logits = -energies/self.temperature
            partition = logsumexp(logits,axis=1)
            expected = np.exp(logits-partition[:,None]) @ bits
            values[:,0] = -self.temperature*partition-np.sum(weights*physical_bits,axis=1)
            rate_jac[:,0] = (physical_bits-expected)/(rates*(1-rates))
        point_rank = point_background[:,None]*self.parameters[:,None]*probabilities*rank[point_group]
        point_rank[:self.global_count] = 0
        jacobian = rate_jac*factors[:,None,:] + np.einsum('nke,ne->nk',rate_jac,point_rank)[:,:,None]*mean_jac[point_group,None,:]
        certified = np.empty((131,3))
        cert_jac = np.empty((131,3,39))
        all_certified = []
        all_cert_jac = []
        row_groups = []
        global_bound = 39/.95 + np.sum(probabilities/(1-1.05*probabilities))
        global_bound_jac = 1/(1-1.05*probabilities)**2
        for group_index in range(131):
            start, end = self.starts[group_index:group_index+2]
            observation = values[start:end]
            derivative = jacobian[start:end]
            if group_index == 0:
                allowance = .0025*global_bound+1e-10
                allowance_jac = .0025*global_bound_jac
            else:
                local_index = group_index-1
                level = levels[local_index]
                background = self.background[local_index]
                if group_index < 45:
                    magnitude = np.abs(level)
                    first = 1-.05*magnitude
                    second = 1-background*probabilities*(1+.05*magnitude)
                    terms = magnitude/first/second
                    direct = terms*background*(1+.05*magnitude)/second
                    level_jac = np.sign(level)*(1/first/second+terms*.05/first+terms*background*probabilities*.05/second)
                    bound_jac = direct + np.dot(level_jac,rank[local_index])*mean_jac[local_index]
                    allowance = .001*terms.sum()+1e-10
                    allowance_jac = .001*bound_jac
                else:
                    parameters = self.parameters[start:end]
                    left = parameters[:-1,None]
                    right = parameters[1:,None]
                    low = np.where(level>=0,left,right)
                    high = np.where(level>=0,right,left)
                    first = 1+low*level
                    second = 1-background*probabilities*(1+high*level)
                    terms = np.abs(level)/first/second
                    direct = terms*background*(1+high*level)/second
                    level_jac = np.sign(level)/first/second-terms*low/first+terms*background*probabilities*high/second
                    bound_jac = direct + (level_jac @ rank[local_index])[:,None]*mean_jac[local_index]
                    widths = np.diff(parameters)
                    cones = (observation[:-1]+observation[1:]-terms.sum(axis=1)[:,None]*widths[:,None])/2
                    cone_jac = (derivative[:-1]+derivative[1:]-bound_jac[:,None,:]*widths[:,None,None])/2
                    if self.sparse:
                        valid = widths<.003
                        cones = cones[valid]
                        cone_jac = cone_jac[valid]
                    all_values = np.concatenate([observation,cones])
                    all_jac = np.concatenate([derivative,cone_jac])
                    indices = all_values.argmin(axis=0)
                    certified[group_index] = all_values[indices,np.arange(3)]-1e-10
                    cert_jac[group_index] = all_jac[indices,np.arange(3)]
                    if self.keep_all:
                        all_certified.append(all_values-1e-10)
                        all_cert_jac.append(all_jac)
                        row_groups.extend([group_index]*len(all_values))
                    continue
            indices = observation.argmin(axis=0)
            certified[group_index] = observation[indices,np.arange(3)]-allowance
            cert_jac[group_index] = derivative[indices,np.arange(3)]-allowance_jac
            if self.keep_all:
                all_certified.append(observation-allowance)
                all_cert_jac.append(derivative-allowance_jac)
                row_groups.extend([group_index]*len(observation))
        self.row_groups = np.asarray(row_groups) if self.keep_all else np.arange(131)
        if self.keep_all:
            certified = np.concatenate(all_certified)
            cert_jac = np.concatenate(all_cert_jac)
        targets = self.targets[self.row_groups]
        normalized = certified.copy()
        normalized[:,:2] /= targets[:,:2]
        normalized[:,2] = np.exp(certified[:,2])/targets[:,2]
        cert_jac[:,:2] /= targets[:,:2,None]
        cert_jac[:,2] *= normalized[:,2,None]
        return normalized,cert_jac

    def cache(self, variables):
        if self.last_x is not None and np.array_equal(self.last_x,variables):
            return
        self.last_x = variables.copy()
        probabilities = variables[:39]*.1
        normalized, jacobian = self.evaluate(probabilities)
        self.ratios = normalized
        self.constraint_values = np.r_[normalized.ravel()-variables[39],(.085-probabilities.mean())*100,(probabilities.std()-.015)*100]
        count = normalized.size
        self.constraint_jac = np.zeros((count+2,40))
        self.constraint_jac[:count,:39] = jacobian.reshape(-1,39)*.1
        self.constraint_jac[:count,39] = -1
        self.constraint_jac[count,:39] = -10/39
        self.constraint_jac[count+1,:39] = (probabilities-probabilities.mean())/39/probabilities.std()*10
        self.calls += 1
        score = normalized.min()
        if score > self.best and probabilities.mean() <= .085+1e-12 and probabilities.std() >= .015:
            self.best = score
            self.best_p = probabilities.copy()
            witness = {'version':1,'probabilities':probabilities.tolist(),'syndrome':self.syndrome}
            self.save_path.write_text(json.dumps(witness,indent=2)+'\n')
            worst = np.unravel_index(normalized.argmin(),normalized.shape)
            if self.verbose:
                print('BEST',self.calls,round(time.time()-self.started,2),score,self.groups[self.row_groups[worst[0]]]['id'],worst[1],flush=True)

    def fun(self, variables):
        self.cache(variables)
        return self.constraint_values

    def jac(self, variables):
        self.cache(variables)
        return self.constraint_jac

def run():
    source = sys.argv[1] if len(sys.argv)>1 else str(PARTICIPANT/'baseline/champion.json')
    data = json.loads(Path(source).read_text())
    problem = Problem(data)
    probabilities = np.array(data['probabilities'])
    values,jacobian = problem.evaluate(probabilities)
    print('Initial',values.min(),flush=True)
    variables = np.r_[probabilities*10,values.min()]
    objective_jac = np.r_[np.zeros(39),-1.0]
    result = minimize(lambda variables:-variables[39],variables,jac=lambda variables:objective_jac,
                      method='SLSQP',bounds=[(.2,1.4)]*39+[(.01,2)],
                      constraints={'type':'ineq','fun':problem.fun,'jac':problem.jac},
                      options={'maxiter':int(os.environ.get('MAXITER','1000')),'ftol':1e-11,'disp':True})
    print(result,flush=True)
    data['probabilities'] = (result.x[:39]*.1).tolist()
    Path('last.json').write_text(json.dumps(data,indent=2)+'\n')

if __name__ == '__main__':
    run()
