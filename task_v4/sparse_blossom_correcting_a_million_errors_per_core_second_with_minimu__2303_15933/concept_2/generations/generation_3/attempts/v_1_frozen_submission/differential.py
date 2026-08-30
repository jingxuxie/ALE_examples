import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution
from optimize import Problem,oracle

class Score:
    def __init__(self,data,indices):
        self.problem=Problem(data)
        self.indices=indices
        self.groups=[self.problem.groups[index] for index in indices]
        self.parameters=[np.array([.95,1,1.05]) if index==0 else np.array([-.05,0,.05]) if index<45 else np.array([-.05,-.0475,.0475,.05]) for index in indices]
        self.starts=np.r_[0,np.cumsum([len(parameters) for parameters in self.parameters])]
        self.data=data
        self.calls=0
        self.best=-1e10
        self.best_p=None

    def evaluate(self,probabilities):
        raw=self.problem.raw
        centered=raw-(raw@probabilities/probabilities.sum())[:,None]
        levels=centered/np.max(np.abs(centered),axis=1)[:,None]
        rates=[]
        for index,parameters in zip(self.indices,self.parameters):
            rates.append(parameters[:,None]*probabilities if index==0 else self.problem.background[index-1]*probabilities*(1+parameters[:,None]*levels[index-1]))
        values=oracle(np.concatenate(rates),self.data['syndrome'],self.problem.physical,False)[0]
        score=100
        for local,(index,parameters) in enumerate(zip(self.indices,self.parameters)):
            observation=values[self.starts[local]:self.starts[local+1]]
            if index==0:
                allowance=.0025*(39/.95+np.sum(probabilities/(1-1.05*probabilities)))
                certified=observation.min(axis=0)-allowance
            elif index<45:
                level=np.abs(levels[index-1]);background=self.problem.background[index-1]
                bound=np.sum(level/(1-.05*level)/(1-background*probabilities*(1+.05*level)))
                certified=observation.min(axis=0)-.001*bound
            else:
                level=levels[index-1];background=self.problem.background[index-1]
                left=np.array([-.05,.0475])[:,None];right=np.array([-.0475,.05])[:,None]
                low=np.where(level>=0,left,right);high=np.where(level>=0,right,left)
                bound=np.sum(np.abs(level)/(1+low*level)/(1-background*probabilities*(1+high*level)),axis=1)
                cones=(observation[[0,2]]+observation[[1,3]]-.0025*bound[:,None])/2
                certified=np.minimum(observation.min(axis=0),cones.min(axis=0))
            certified-=1e-10
            target=self.problem.targets[index]
            score=min(score,certified[0]/target[0],certified[1]/target[1],np.exp(certified[2])/target[2])
        return score

def main():
    data=json.loads(Path('witness.json').read_text())
    base=np.array(data['probabilities'])
    reports=json.loads(Path('witness_metrics.json').read_text())['groups']
    indices=[index for index,group in enumerate(reports) if group['score']<1.02]
    selected=np.flatnonzero((base>.02001)&(base<.13999))
    print('groups',len(indices),'variables',selected.tolist(),flush=True)
    scorer=Score(data,indices)
    initial=scorer.evaluate(base)
    rng=np.random.default_rng(51281)
    population=rng.uniform(.02,.14,(18*len(selected),len(selected)))
    population[:len(population)//2]=np.clip(base[selected]+rng.normal(0,.015,(len(population)//2,len(selected))),.02,.14)
    population[0]=base[selected]
    started=time.time()
    def objective(variables):
        probabilities=base.copy();probabilities[selected]=variables
        if probabilities.mean()>.085:return 10+probabilities.mean()
        value=scorer.evaluate(probabilities)
        scorer.calls+=1
        if value>scorer.best:
            scorer.best=value;scorer.best_p=probabilities.copy()
            witness={'version':1,'probabilities':probabilities.tolist(),'syndrome':data['syndrome']}
            Path('de_best.json').write_text(json.dumps(witness,indent=2)+'\n')
            print('BEST',scorer.calls,value,round(time.time()-started,1),flush=True)
        return -value
    def callback(variables,convergence):
        if scorer.calls%20000<500:print('progress',scorer.calls,scorer.best,round(time.time()-started,1),flush=True)
    result=differential_evolution(objective,[(.02,.14)]*len(selected),init=population,maxiter=1200,tol=1e-9,
                                  mutation=(.5,1.2),recombination=.8,seed=2272,polish=False,callback=callback)
    print(result,flush=True)
    print('FULL',scorer.problem.evaluate(scorer.best_p)[0].min(),flush=True)

if __name__=='__main__':main()
