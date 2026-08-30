from investigate import *
from quartic_search import MESHES
import argparse

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('base')
    parser.add_argument('--trials',type=int,default=5000)
    arguments=parser.parse_args()
    document=json.loads(Path(arguments.base).read_text())
    original=unpack(document)
    assert len(original)<=23
    point=float(Fraction(document['x']))
    coordinate=2*point-1
    square=cheb.chebmul([-coordinate,1],[-coordinate,1])
    vector=np.array([float(Fraction(value)) for value in document['vector']])
    vector/=np.linalg.norm(vector)
    random=np.random.default_rng(796531)
    best=-1e99
    start=time.time()
    for trial in range(arguments.trials):
        if trial%3==0:
            projector=(np.eye(4)-np.outer(vector,vector))/3
        else:
            directions=random.normal(size=(4,int(random.integers(1,5))))
            directions-=random.uniform(0,1)*np.outer(vector,vector@directions)
            projector=directions@directions.T
            projector/=np.trace(projector)
        strength=10**random.uniform(-4,np.log10(.95/(1+abs(coordinate))**2))
        scaling=-strength*square
        scaling[0]+=1
        coefficients=np.zeros((len(original)+2,4,4))
        for row in range(4):
            for column in range(4):
                coefficients[:,row,column]=cheb.chebmul(scaling,original[:,row,column])
        coefficients[:3]+=strength*square[:,None,None]*projector
        candidate=package_rotated(coefficients,point,np.eye(4))
        candidate['vector']=document['vector']
        coefficients=unpack(candidate)
        if max(np.sum(np.abs(coefficients),axis=(0,2)))>4:
            continue
        candidates=guard.determinant_candidates(coefficients)
        points=np.concatenate((MESHES,candidates))
        minimum=np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,points))[:,0].min()
        if minimum>best:
            best=minimum
            Path('mix_best.json').write_text(json.dumps(candidate))
            print('BEST',trial,minimum,strength,time.time()-start,flush=True)
        if minimum>=-guard.NEGATIVE_TOLERANCE:
            reports=guard.screen_all(coefficients)
            print('ESCAPE',trial,reports,flush=True)
            Path(f'mix_escape_{trial}.json').write_text(json.dumps(candidate))
            if all(report['accepted'] for report in reports):
                Path('witness.json').write_text(json.dumps(candidate))
                return
        if trial%500==0:
            print('PROGRESS',trial,best,time.time()-start,flush=True)
    print('DONE',best,time.time()-start,flush=True)

if __name__=='__main__':
    main()
