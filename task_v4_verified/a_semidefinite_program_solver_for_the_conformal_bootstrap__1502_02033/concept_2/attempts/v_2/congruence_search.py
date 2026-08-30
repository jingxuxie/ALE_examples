from investigate import *
from quartic_search import MESHES,WIDTHS,TOP
from collections import Counter
import argparse
import itertools

def congruence_candidate(random):
    location=int(random.choice(TOP[-40:]))
    point=(MESHES[location]+MESHES[location+1])/2+random.uniform(-.08,.08)*WIDTHS[location]
    center=2*point-1
    depth=1.02e-7
    small=depth*10**random.uniform(.7,4)
    large=max(10**random.uniform(-3.7,-1.3),4.1*small)
    pivot=np.sqrt(small*large)
    height=np.sqrt(small+large-2*pivot)
    order=12
    derivatives=cheb.chebval(center,cheb.chebder(np.eye(order+1),axis=0))
    polynomials=random.normal(size=(3,order+1))
    for polynomial in polynomials:
        polynomial+=random.uniform(-2,2)*derivatives/np.linalg.norm(derivatives)
        polynomial[0]-=cheb.chebval(center,polynomial)
    values=np.array([cheb.chebval(np.linspace(-1,1,1001),polynomial) for polynomial in polynomials])
    polynomials*=random.uniform(.65,.95)/np.sqrt(np.max(np.sum(values*values,axis=0)))
    polynomials[2,0]+=height
    first,second,third=polynomials
    spectral=np.zeros((25,4,4))
    spectral[:,0,0]=cheb.chebmul(first,first)+cheb.chebmul(second,second)
    spectral[:13,0,1]=np.sqrt(pivot)*first
    spectral[:,0,1]+=cheb.chebmul(second,third)
    spectral[:,1,0]=spectral[:,0,1]
    spectral[:13,0,2]=np.sqrt(pivot)*second
    spectral[:,2,0]=spectral[:,0,2]
    spectral[:,1,1]=cheb.chebmul(third,third)
    spectral[0,1,1]+=pivot
    spectral[:13,1,2]=np.sqrt(pivot)*third
    spectral[:,2,1]=spectral[:,1,2]
    spectral[0,2,2]=pivot
    envelope=10**random.uniform(-5,-2)*cheb.chebmul([-center,1],[-center,1])
    spectral[:3,0,0]+=envelope
    spectral[0,0,0]-=depth
    at_point=np.array([[pivot+height*height,np.sqrt(pivot)*height],[np.sqrt(pivot)*height,pivot]])
    _,vectors=np.linalg.eigh(at_point)
    basis=np.eye(4)
    basis[1:3,1:3]=vectors
    spectral=basis.T@spectral@basis
    document=package(spectral,point)
    return document,dict(point=point,small=small,large=large,pivot=pivot)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--trials',type=int,default=50000)
    parser.add_argument('--seed',type=int,default=57312)
    arguments=parser.parse_args()
    random=np.random.default_rng(arguments.seed)
    stages=Counter()
    best=-1e99
    start=time.time()
    for trial in range(arguments.trials):
        document,parameters=congruence_candidate(random)
        coefficients=unpack(document)
        if max(np.sum(np.abs(coefficients),axis=(0,2)))>4 or np.max(np.abs(coefficients))>1:
            stages['scale']+=1
            continue
        meshmin=np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,MESHES))[:,0].min()
        if meshmin < -guard.NEGATIVE_TOLERANCE:
            stages['mesh']+=1
            continue
        candidates=guard.determinant_candidates(coefficients)
        minimum=np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,candidates))[:,0].min()
        stages['determinants']+=1
        if minimum>best:
            best=minimum
            Path('congruence_best.json').write_text(json.dumps(document))
            print('BEST',trial,minimum,parameters,flush=True)
        if minimum>=-guard.NEGATIVE_TOLERANCE:
            reports=guard.screen_all(coefficients)
            count=sum(report['accepted'] for report in reports)
            print('ESCAPE',trial,parameters,reports,flush=True)
            Path(f'congruence_escape_{trial}.json').write_text(json.dumps(document))
            if count==3:
                Path('witness.json').write_text(json.dumps(document))
                break
        if trial%100==0:
            print('PROGRESS',trial,dict(stages),time.time()-start,flush=True)
    print('DONE',dict(stages),time.time()-start,flush=True)

if __name__=='__main__':
    main()
