from investigate import *
from collections import Counter
import argparse
import itertools

MESHES = np.unique(np.concatenate([guard._mesh(profile) for profile in guard.PROFILES]))
WIDTHS = np.diff(MESHES)
ELIGIBLE = np.where((MESHES[:-1]>.05)&(MESHES[1:]<.95))[0]
TOP = ELIGIBLE[np.argsort(WIDTHS[ELIGIBLE])[-70:]]

def quartic_candidate(random):
    location = int(random.choice(TOP))
    point = (MESHES[location]+MESHES[location+1])/2 + random.uniform(-.1,.1)*WIDTHS[location]
    center = 2*point-1
    order = 6
    first = random.normal(size=order+1)
    first /= np.linalg.norm(first)
    first *= random.uniform(.008, .018)
    first[0] -= cheb.chebval(center, first)
    depth = 1.03e-7
    parameter = random.uniform(2, 15)
    divisor = random.uniform(.5, 8)
    skew = random.uniform(-8,8)*np.sqrt(depth)
    first_square = cheb.chebmul(first, first)
    second = first_square.copy()
    second[:len(first)] += skew*first
    second[0] -= parameter*depth
    second /= np.sqrt(divisor*depth)
    height = random.uniform(.0133,.025)
    third = random.normal(size=7)
    third /= np.linalg.norm(third)
    third *= random.uniform(.05,.2)
    third[0] += height-cheb.chebval(center,third)
    plateau = 10**random.uniform(-9,-6)
    coupling = random.uniform(-.6,.6)
    envelope_scale = 10**random.uniform(-5,-2)
    spectral = np.zeros((25,4,4))
    spectral[:len(first_square),0,0] = first_square
    spectral[:3,0,0] += envelope_scale*cheb.chebmul([-center,1],[-center,1])
    spectral[0,0,0] -= depth
    spectral[:,1,1] = cheb.chebmul(second,second)
    spectral[0,1,1] += plateau
    third_square = cheb.chebmul(third,third)
    spectral[:len(third_square),2,2] = third_square
    spectral[0,2,2] += 1e-6
    mixed = coupling*cheb.chebmul(first,second)
    spectral[:len(mixed),0,1] = mixed
    spectral[:,1,0] = spectral[:,0,1]
    document = package(spectral,point)
    return document,dict(point=point,height=height,parameter=parameter,divisor=divisor,skew=skew,plateau=plateau,coupling=coupling,envelope_scale=envelope_scale)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=20000)
    parser.add_argument('--seed', type=int, default=291845)
    arguments = parser.parse_args()
    random = np.random.default_rng(arguments.seed)
    stages = Counter()
    best = -1e99
    start = time.time()
    for trial in range(arguments.trials):
        document, parameters = quartic_candidate(random)
        coefficients = unpack(document)
        matrix = guard.evaluate_matrices(coefficients,[parameters['point']])[0]
        if min(np.diag(matrix)) < .02 or min(np.linalg.det(matrix[np.ix_(pair,pair)]) for pair in itertools.combinations(range(4),2)) < 1e-5 or max(np.sum(np.abs(coefficients),axis=(0,2))) > 4 or np.max(np.abs(coefficients)) > 1:
            stages['invalid'] += 1
            continue
        meshmin = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,MESHES))[:,0].min()
        if meshmin < -guard.NEGATIVE_TOLERANCE:
            stages['mesh'] += 1
            continue
        candidates = guard.determinant_candidates(coefficients)
        minimum = np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,candidates))[:,0].min()
        stages['determinants'] += 1
        if minimum > best:
            best = minimum
            Path('quartic_best.json').write_text(json.dumps(document))
            print('BEST',trial,minimum,parameters,flush=True)
        if minimum >= -guard.NEGATIVE_TOLERANCE:
            reports = guard.screen_all(coefficients)
            count = sum(report['accepted'] for report in reports)
            print('ESCAPE',trial,parameters,reports,flush=True)
            Path(f'quartic_escape_{trial}.json').write_text(json.dumps(document))
            if count == 3:
                Path('witness.json').write_text(json.dumps(document))
                break
        if trial % 100 == 0:
            print('PROGRESS',trial,dict(stages),time.time()-start,flush=True)
    print('DONE',dict(stages),time.time()-start,flush=True)

if __name__ == '__main__':
    main()
