from investigate import *
from highgram_search import MESHES,WIDTHS,TOP,GEOMETRY
from scipy.optimize import brentq
from collections import Counter
import argparse

def append_filter(coefficients, direction):
    projected = np.outer(coefficients @ direction,direction)
    result = np.zeros((len(coefficients)+1,4))
    result[:-1] = coefficients-projected
    result[1:] += projected
    return result

def filter_candidate(random):
    location = int(random.choice(TOP[-5:]))
    point = (MESHES[location]+MESHES[location+1])/2+random.uniform(-.08,.08)*WIDTHS[location]
    center = 2*point-1
    phase = np.arccos(center)
    unit = np.exp(1j*phase)
    initial = random.normal(size=4)
    initial /= np.linalg.norm(initial)
    factors = initial[None,:]
    order = int(random.choice([12,16,20,22]))
    anchor = random.normal(size=(2,4))
    anchor /= np.linalg.norm(anchor,axis=1)[:,None]
    for index in range(order-1):
        direction = random.normal(size=4)*.2 + anchor[index*2//order]
        direction /= np.linalg.norm(direction)
        factors = append_filter(factors,direction)
    value = (unit**np.arange(len(factors)))@factors
    covariance = np.outer(value.real,value.real)+np.outer(value.imag,value.imag)
    eigenvalues,eigenvectors = np.linalg.eigh(covariance)
    plane = eigenvectors[:,-2:]
    coordinates = plane.T@value
    area = np.imag(coordinates[0]*np.conj(coordinates[1]))
    ratio = -2*np.cos(phase)*area/(np.sin(phase)*(eigenvalues[-1]-eigenvalues[-2]))
    if abs(ratio)>=1:
        return None,None,'phase'
    angle = .5*np.arcsin(ratio)
    height_squared = 1.07e-5/GEOMETRY['minor']
    def minor_angle(offset):
        direction = plane@np.array([np.cos(angle+offset),np.sin(angle+offset)])
        transformed = value+(unit-1)*direction*np.dot(direction,value)
        gram = np.array([[np.dot(transformed.real,transformed.real),np.dot(transformed.real,transformed.imag)],[np.dot(transformed.real,transformed.imag),np.dot(transformed.imag,transformed.imag)]])
        return np.linalg.eigvalsh(gram)[0]-height_squared
    if minor_angle(0)>0 or minor_angle(.3)<0:
        return None,None,'phase'
    offset = brentq(minor_angle,0,.3,xtol=1e-13)
    direction = plane@np.array([np.cos(angle+offset),np.sin(angle+offset)])
    factors = append_filter(factors,direction)
    matrices = np.zeros((len(factors),4,4))
    matrices[0] = factors.T@factors
    for degree in range(1,len(factors)):
        product = factors[:-degree].T@factors[degree:]
        matrices[degree] = product+product.T
    value = guard.evaluate_matrices(matrices,[point])[0]
    eigenvalues,eigenvectors = np.linalg.eigh(value)
    derivative = guard.evaluate_matrices(2*cheb.chebder(matrices,axis=0),[point])[0]
    null = eigenvectors[:,:2]
    projected = null.T@derivative@eigenvectors[:,2]
    if np.linalg.norm(projected)<1e-10:
        return None,None,'slope'
    projected /= np.linalg.norm(projected)
    basis = eigenvectors.copy()
    basis[:,0] = null@projected
    basis[:,1] = null@np.array([-projected[1],projected[0]])
    width = eigenvalues[2]*GEOMETRY['width']/abs(basis[:,0]@derivative@basis[:,2])
    if width>.49*WIDTHS[location]:
        return None,None,'wide'
    spectral = basis.T@matrices@basis
    depth = 1.02e-7
    envelope = 10**random.uniform(-5,-3)*cheb.chebmul([-center,1],[-center,1])
    additions = np.zeros((3,4,4))
    additions[:,0,0] = envelope
    additions[0,0,0] -= depth
    additions[0,1,1] = depth*GEOMETRY['plateau']
    additions[0,2,2] = depth*GEOMETRY['positive']
    scale = -np.trace(additions,axis1=1,axis2=2)
    scale[0] += 1
    scaled = np.zeros((len(spectral)+2,4,4))
    for row in range(4):
        for column in range(4):
            scaled[:,row,column] = cheb.chebmul(scale,spectral[:,row,column])
    scaled[:3] += additions
    document = package_rotated(scaled,point,np.array(GEOMETRY['rotation']))
    return document,dict(point=point,width=width,order=order),'okay'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--trials',type=int,default=50000)
    parser.add_argument('--seed',type=int,default=78925)
    arguments=parser.parse_args()
    random=np.random.default_rng(arguments.seed)
    stages=Counter()
    best=-1e99
    start=time.time()
    for trial in range(arguments.trials):
        document,parameters,stage=filter_candidate(random)
        if document is None:
            stages[stage]+=1
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
            Path('filter_best.json').write_text(json.dumps(document))
            print('BEST',trial,minimum,parameters,flush=True)
        if minimum>=-guard.NEGATIVE_TOLERANCE:
            reports=guard.screen_all(coefficients)
            count=sum(report['accepted'] for report in reports)
            print('ESCAPE',trial,parameters,reports,flush=True)
            Path(f'filter_escape_{trial}.json').write_text(json.dumps(document))
            if count==3:
                Path('witness.json').write_text(json.dumps(document))
                break
        if trial%100==0:
            print('PROGRESS',trial,dict(stages),time.time()-start,flush=True)
    print('DONE',dict(stages),time.time()-start,flush=True)

if __name__=='__main__':
    main()
