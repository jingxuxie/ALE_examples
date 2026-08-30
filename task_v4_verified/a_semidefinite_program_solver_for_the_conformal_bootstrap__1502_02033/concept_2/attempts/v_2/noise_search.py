from investigate import *
import itertools
import argparse

PERMUTATIONS = list(itertools.permutations(range(4)))
SIGNS = [(-1 if sum(permutation[left]>permutation[right] for left in range(4) for right in range(left+1,4))%2 else 1) for permutation in PERMUTATIONS]

def full_polynomial(coefficients):
    determinant = np.zeros(4*(len(coefficients)-1)+1,dtype=coefficients.dtype)
    for permutation,sign in zip(PERMUTATIONS,SIGNS):
        polynomial = np.array([1.0],dtype=coefficients.dtype)
        for row,column in enumerate(permutation):
            polynomial = cheb.chebmul(polynomial,coefficients[:,row,column])
        determinant[:len(polynomial)] += sign*polynomial
    return determinant

def score(coefficients):
    polynomial = full_polynomial(coefficients)
    candidates = np.concatenate((guard._root_projections(polynomial),guard._root_projections(cheb.chebder(polynomial))))
    candidates = np.clip(np.concatenate((candidates,candidates-2e-7,candidates+2e-7)),0,1)
    minimum = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,candidates))[:,0].min()
    return minimum

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('base')
    parser.add_argument('--trials',type=int,default=10000)
    parser.add_argument('--seed',type=int,default=835123)
    arguments=parser.parse_args()
    document=json.loads(Path(arguments.base).read_text())
    original=np.array(document['coefficients'],dtype=np.int64)
    random=np.random.default_rng(arguments.seed)
    best=-1e99
    point=float(Fraction(document['x']))
    start=time.time()
    for trial in range(arguments.trials):
        integers=original.copy()
        noise=random.integers(-10,11,size=integers.shape)
        noise=np.triu(noise)
        noise=noise+noise.transpose(0,2,1)
        for degree,matrix in enumerate(noise):
            matrix[3,3]=-sum(int(matrix[index,index]) for index in range(3))
        integers+=noise
        coefficients=integers/document['denominator']
        minimum=score(coefficients)
        if minimum>best:
            best=minimum
            document['coefficients']=integers.tolist()
            Path('noise_best.json').write_text(json.dumps(document))
            print('BEST',trial,minimum,time.time()-start,flush=True)
        if minimum>=-guard.NEGATIVE_TOLERANCE:
            document['coefficients']=integers.tolist()
            reports=guard.screen_all(coefficients)
            print('ESCAPE',trial,reports,flush=True)
            Path(f'noise_escape_{trial}.json').write_text(json.dumps(document))
            if all(report['accepted'] for report in reports):
                Path('witness.json').write_text(json.dumps(document))
                break
        if trial%1000==0:
            print('PROGRESS',trial,best,time.time()-start,flush=True)
    print('DONE',best,time.time()-start,flush=True)

if __name__=='__main__':
    main()
