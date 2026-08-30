from investigate import *
from quartic_search import MESHES, WIDTHS, TOP
from collections import Counter
import argparse
import itertools

CHECK_POINTS = np.linspace(0,1,1001)
CHECK_COORDS = 2*CHECK_POINTS-1
GEOMETRY = json.loads(Path(os.environ.get('GEOMETRY_FILE','geometry_optimized_8.json')).read_text())

def highgram_candidate(random):
    location = int(random.choice(TOP[-35:]))
    point = (MESHES[location]+MESHES[location+1])/2 + random.uniform(-.08,.08)*WIDTHS[location]
    center = 2*point-1
    order = int(random.choice([8,10,11,12]))
    height = np.sqrt(1.06e-5/GEOMETRY['minor'])
    first = random.normal(size=order+1)
    derivatives = cheb.chebval(center,cheb.chebder(np.eye(order+1),axis=0))
    first += random.uniform(.5,2)*derivatives/np.linalg.norm(derivatives)
    first[0] -= cheb.chebval(center,first)
    second = random.normal(size=order+1)
    target_slope = GEOMETRY['slope']*cheb.chebval(center,cheb.chebder(first))
    second += (target_slope-cheb.chebval(center,cheb.chebder(second)))*derivatives/np.dot(derivatives,derivatives)
    second[0] -= cheb.chebval(center,second)
    third = random.normal(size=order+1)*random.uniform(.1,1)
    third[0] -= cheb.chebval(center,third)
    vectors = np.array([first,second,third])
    values = np.array([cheb.chebval(CHECK_COORDS,polynomial) for polynomial in vectors])
    maximum = np.max(np.sum(values*values,axis=0))
    vectors *= random.uniform(.75,.96)/np.sqrt(maximum)
    vectors[2,0] += height
    width = height*GEOMETRY['width']/abs(2*cheb.chebval(center,cheb.chebder(vectors[0])))
    if width > .48*WIDTHS[location]:
        return None, None
    depth = 1.02e-7
    spectral = np.zeros((25,4,4))
    for row in range(3):
        for column in range(row,3):
            polynomial = cheb.chebmul(vectors[row],vectors[column])
            spectral[:len(polynomial),row,column] = polynomial
            spectral[:,column,row] = spectral[:,row,column]
    spectral[:3,0,0] += 10**random.uniform(-4.5,-3.5)*cheb.chebmul([-center,1],[-center,1])
    spectral[0,0,0] -= depth
    spectral[0,1,1] += depth*GEOMETRY['plateau']
    spectral[0,2,2] += depth*GEOMETRY['positive']
    rotation = np.array(GEOMETRY['rotation'])
    document = package_rotated(spectral,point,rotation)
    if order<12:
        integers = document['coefficients']
        scale = int(random.choice([1,10,100]))
        for row in range(4):
            for column in range(row,4):
                value = int(random.integers(-scale,scale+1))
                integers[-1][row][column] = value
                integers[-1][column][row] = value
        integers[-1][3][3] = -sum(integers[-1][index][index] for index in range(3))
    return document,dict(point=point,height=height,width=width)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--trials',type=int,default=50000)
    parser.add_argument('--seed',type=int,default=16471)
    arguments=parser.parse_args()
    random=np.random.default_rng(arguments.seed)
    stages=Counter()
    best=-1e99
    start=time.time()
    for trial in range(arguments.trials):
        document,parameters=highgram_candidate(random)
        if document is None:
            stages['wide']+=1
            continue
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
            Path('highgram_best.json').write_text(json.dumps(document))
            print('BEST',trial,minimum,parameters,flush=True)
        if minimum>=-guard.NEGATIVE_TOLERANCE:
            reports=guard.screen_all(coefficients)
            count=sum(report['accepted'] for report in reports)
            print('ESCAPE',trial,parameters,reports,flush=True)
            Path(f'highgram_escape_{trial}.json').write_text(json.dumps(document))
            if count==3:
                Path('witness.json').write_text(json.dumps(document))
                break
        if trial%100==0:
            print('PROGRESS',trial,dict(stages),time.time()-start,flush=True)
    print('DONE',dict(stages),time.time()-start,flush=True)

if __name__=='__main__':
    main()
