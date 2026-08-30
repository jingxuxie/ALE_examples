import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import itertools
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from optimize import oracle, PARTICIPANT

class Nominal:
    def __init__(self, syndrome, physical, temperature=.005):
        self.syndrome=syndrome
        self.physical=physical
        self.temperature=temperature
        self.masks=np.empty(0,dtype=np.uint64)
        self.last=None
        self.best=-1e10
        self.best_p=None
        self.scales=np.array([.95,1.,1.05])

    def constraints(self, variables):
        if self.last is not None and np.array_equal(variables,self.last):return self.values
        self.last=variables.copy()
        probabilities=variables[:39]*.1
        rates=self.scales[:,None]*probabilities
        values,jac,masks=oracle(rates,self.syndrome,self.physical)
        self.masks=np.union1d(self.masks,masks[:,1])
        bits=((self.masks[:,None]>>np.arange(39,dtype=np.uint64))&1).astype(float)
        physical_bits=((masks[:,0,None]>>np.arange(39,dtype=np.uint64))&1).astype(float)
        weights=np.log1p(-rates)-np.log(rates)
        energies=weights@bits.T
        logits=-energies/self.temperature
        partition=logsumexp(logits,axis=1)
        expected=np.exp(logits-partition[:,None])@bits
        values[:,0]=-self.temperature*partition-np.sum(weights*physical_bits,axis=1)
        jac[:,0]=(physical_bits-expected)/(rates*(1-rates))
        allowance=.0025*(39/.95+np.sum(probabilities/(1-1.05*probabilities)))
        allowance_jac=.0025/(1-1.05*probabilities)**2
        values-=allowance
        jac=jac*self.scales[:,None,None]-allowance_jac
        values[:,:2]/=np.array([1.08,np.log(.85/.15)])
        jac[:,:2]/=np.array([1.08,np.log(.85/.15)])[None,:,None]
        values[:,2]=np.exp(values[:,2])/1.75e-5
        jac[:,2]*=values[:,2,None]
        self.values=np.r_[values.ravel()-variables[39],(.085-probabilities.mean())*100]
        self.derivative=np.zeros((10,40));self.derivative[:9,:39]=jac.reshape(-1,39)*.1
        self.derivative[:9,39]=-1;self.derivative[9,:39]=-10/39
        score=values.min()
        if score>self.best and probabilities.mean()<=.085+1e-9:
            self.best=score;self.best_p=probabilities.copy()
        return self.values

    def jac(self,variables):
        self.constraints(variables)
        return self.derivative

def solve(probabilities, syndrome, physical=None, iterations=150):
    if physical is None:
        physical=int(oracle(np.array([probabilities]),syndrome,0,False)[0][0,0]<0)
    problem=Nominal(syndrome,physical)
    variables=np.r_[probabilities*10,.1]
    if os.environ.get('WEIGHTSPACE'):
        variables[:39]=np.log1p(-probabilities)-np.log(probabilities)
        def transform(variables):
            rates=np.clip(1/(1+np.exp(variables[:39])),.02,.14)
            return np.r_[rates*10,variables[39]],rates
        def constraint(variables):
            transformed,rates=transform(variables)
            return problem.constraints(transformed)
        def jacobian(variables):
            transformed,rates=transform(variables)
            jac=problem.jac(transformed).copy()
            jac[:,:39]*=-10*rates*(1-rates)
            return jac
        result=minimize(lambda variables:-variables[39],variables,jac=lambda variables:np.r_[np.zeros(39),-1],
                        bounds=[(np.log(.86/.14),np.log(.98/.02))]*39+[(-3,3)],method='SLSQP',
                        constraints={'type':'ineq','fun':constraint,'jac':jacobian},
                        options={'maxiter':iterations,'ftol':1e-9})
        return problem.best,problem.best_p,result
    result=minimize(lambda variables:-variables[39],variables,jac=lambda variables:np.r_[np.zeros(39),-1],
                    bounds=[(.2,1.4)]*39+[(-3,3)],method='SLSQP',
                    constraints={'type':'ineq','fun':problem.constraints,'jac':problem.jac},
                    options={'maxiter':iterations,'ftol':1e-8})
    return problem.best, problem.best_p, result

def main():
    data=json.loads((PARTICIPANT/'baseline/champion.json').read_text())
    probabilities=np.array(data['probabilities'])
    original=data['syndrome']
    candidates={tuple(original)}
    for remove in original:
        for add in range(20):
            syndrome=sorted(set(original)-{remove}|{add})
            if 3<=len(syndrome)<=6 and len({detector//4 for detector in syndrome})>=3 and len({detector%4 for detector in syndrome})>=3:
                candidates.add(tuple(syndrome))
    for add in range(20):
        syndrome=sorted(set(original)|{add})
        if len(syndrome)<=6:candidates.add(tuple(syndrome))
    candidates=sorted(candidates)
    rng=np.random.default_rng(712)
    rng.shuffle(candidates)
    directory=Path('nominal_candidates');directory.mkdir(exist_ok=True)
    started=time.time()
    for index,syndrome in enumerate(candidates):
        score,best,result=solve(probabilities,list(syndrome))
        print(index,list(syndrome),score,result.success,result.nit,round(time.time()-started,2),flush=True)
        if score>1:
            witness={'version':1,'probabilities':best.tolist(),'syndrome':list(syndrome)}
            (directory/('candidate_'+str(index)+'.json')).write_text(json.dumps(witness))

if __name__=='__main__':main()
