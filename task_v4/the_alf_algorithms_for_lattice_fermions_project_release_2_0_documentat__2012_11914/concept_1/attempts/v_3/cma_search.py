import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import json
import time
import numpy as np
from permutation_search import evaluate
from search import OUT,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()

def main():
    double=len(sys.argv)>2
    dimension=64 if double else 32
    population=128 if double else 96
    elite=32
    weights=np.log(elite+.5)-np.log(np.arange(1,elite+1))
    weights/=weights.sum()
    effective=1/np.sum(weights**2)
    covariance_rate=(4+effective/dimension)/(dimension+4+2*effective/dimension)
    sigma_rate=(effective+2)/(dimension+effective+5)
    rank_one_rate=2/((dimension+1.3)**2+effective)
    rank_mu_rate=min(1-rank_one_rate,2*(effective-2+1/effective)/((dimension+2)**2+effective))
    damping=1+2*max(0,np.sqrt((effective-1)/(dimension+1))-1)+sigma_rate
    expected=np.sqrt(dimension)*(1-1/(4*dimension)+1/(21*dimension**2))
    best=10
    for restart in range(10000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_CMA').exists():
            return
        filename=['critical_best_698.json','single_best_921.json','structured_best.json','quotient_best_815.json'][restart%4]
        base=np.array(json.loads((OUT/filename).read_text())['fields'])
        offsets=[]
        durations=[]
        for site in range(16):
            starts=np.flatnonzero((base[:,site]>0)&(np.roll(base[:,site],1)<0))
            if len(starts):
                offsets.append(starts[0])
            else:
                offsets.append(0)
            durations.append(np.count_nonzero(base[:,site]>0))
        mean=np.concatenate([offsets,durations]).astype(float)
        if double:
            mean=np.concatenate([mean,random.integers(0,16,size=16),np.zeros(16)])
        sigma=float(random.choice([.6,1.,1.5,2.,3.]))
        if restart%5==0:
            mean[:16]+=random.normal(0,2,size=16)
            mean[16:32]+=random.normal(0,1,size=16)
        covariance=np.eye(dimension)
        path_covariance=np.zeros(dimension)
        path_sigma=np.zeros(dimension)
        local=10
        for generation in range(300):
            eigenvalues,eigenvectors=np.linalg.eigh(covariance)
            scales=np.sqrt(np.maximum(eigenvalues,1e-12))
            transform=eigenvectors*scales[None]
            inverse=(eigenvectors/scales[None])@eigenvectors.T
            steps=random.normal(size=(population,dimension))@transform.T
            samples=mean[None]+sigma*steps
            starts=np.rint(samples[:,:16]).astype(int)%16
            lengths=np.clip(np.rint(samples[:,16:32]).astype(int),0,16)
            active=(np.arange(16)[None,:,None]-starts[:,None,:])%16<lengths[:,None,:]
            if double:
                secondary_starts=np.rint(samples[:,32:48]).astype(int)%16
                secondary_lengths=np.clip(np.rint(samples[:,48:64]).astype(int),0,8)
                secondary=(np.arange(16)[None,:,None]-secondary_starts[:,None,:])%16<secondary_lengths[:,None,:]
                active^=secondary
            fields=np.where(active,1,-1).astype(np.int8)
            scores,full=evaluate(fields)
            negative=np.flatnonzero(full<-1e-7)
            if len(negative):
                save(fields[negative[0]])
                print('FOUND',full[negative[0]],flush=True)
                return
            selected=np.argsort(scores)[:elite]
            if scores[selected[0]]<best:
                best=scores[selected[0]]
                save(fields[selected[0]],'cma_best_'+sys.argv[1]+'.json')
                print(f'{time.time()-started:.2f}s restart={restart} generation={generation} best={best:.12g}',flush=True)
            local=min(local,scores[selected[0]])
            displacement=weights@steps[selected]
            mean+=sigma*displacement
            path_sigma=(1-sigma_rate)*path_sigma+np.sqrt(sigma_rate*(2-sigma_rate)*effective)*(inverse@displacement)
            active=np.linalg.norm(path_sigma)/np.sqrt(1-(1-sigma_rate)**(2*(generation+1)))<(1.4+2/(dimension+1))*expected
            path_covariance=(1-covariance_rate)*path_covariance+active*np.sqrt(covariance_rate*(2-covariance_rate)*effective)*displacement
            covariance=(1-rank_one_rate-rank_mu_rate)*covariance+rank_one_rate*(np.outer(path_covariance,path_covariance)+(1-active)*covariance_rate*(2-covariance_rate)*covariance)+rank_mu_rate*(steps[selected].T*weights)@steps[selected]
            sigma*=np.exp((sigma_rate/damping)*(np.linalg.norm(path_sigma)/expected-1))
            if sigma<.1 or sigma>8:
                break
        print(f'{time.time()-started:.2f}s restart={restart} local={local:.12g} sigma={sigma:.4g}',flush=True)

if __name__=='__main__':
    main()
