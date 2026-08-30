from investigate import *
from scipy.optimize import minimize_scalar,differential_evolution
from quartic_search import MESHES

GEOMETRY=json.loads(Path('geometry_product.json').read_text())
ROTATION=np.array(GEOMETRY['rotation'])
DOCUMENT=json.loads(Path('filter_best.json').read_text())
BASE=unpack(DOCUMENT)
BASE_POINT=float(Fraction(DOCUMENT['x']))
DEPTH=1.02e-7
SPECTRAL=ROTATION.T@BASE@ROTATION
CHECK=np.linspace(.03,.97,19)
VALUES=guard.evaluate_matrices(SPECTRAL,CHECK)

def residual(logarithm):
    scale=np.exp(logarithm)
    corrections=np.zeros((len(CHECK),4,4))
    corrections[:,0,0]=scale*(2*(CHECK-BASE_POINT))**2-DEPTH
    corrections[:,1,1]=DEPTH*GEOMETRY['plateau']
    corrections[:,2,2]=DEPTH*GEOMETRY['positive']
    values=np.linalg.eigvalsh(VALUES-corrections)
    return np.sum(values[:,:2]**2)

FIT=minimize_scalar(residual,bounds=(np.log(1e-5),np.log(1e-3)),method='bounded',options={'xatol':1e-13})
ENVELOPE=np.exp(FIT.x)
NODES=np.cos(np.pi*(np.arange(101)+.5)/101)
POINTS=(NODES+1)/2
VALUES=guard.evaluate_matrices(SPECTRAL,POINTS)
CORRECTIONS=np.zeros_like(VALUES)
CORRECTIONS[:,0,0]=ENVELOPE*(2*(POINTS-BASE_POINT))**2-DEPTH
CORRECTIONS[:,1,1]=DEPTH*GEOMETRY['plateau']
CORRECTIONS[:,2,2]=DEPTH*GEOMETRY['positive']
SCALES=1-np.trace(CORRECTIONS,axis1=1,axis2=2)
BACKGROUND=cheb.chebfit(NODES,((VALUES-CORRECTIONS)/SCALES[:,None,None]).reshape(101,16),len(BASE)-3).reshape(len(BASE)-2,4,4)
BACKGROUND=(BACKGROUND+BACKGROUND.transpose(0,2,1))/2
Path('optimized_background.json').write_text(json.dumps(dict(coefficients=BACKGROUND.tolist(),point=BASE_POINT,envelope=ENVELOPE,residual=float(FIT.fun))))
print('RECONSTRUCT',BASE_POINT,ENVELOPE,FIT.fun,flush=True)
BEST=-1e99
COUNT=0
START=time.time()
EXTRA=os.environ.get('EXTRA_MODE')=='1'
ROTATE=os.environ.get('ROTATE_MODE')=='1'
FOURTH=os.environ.get('FOURTH_MODE')=='1'
PREFIX='fourth_filter' if FOURTH else ('rotate_filter' if ROTATE else ('extra_filter' if EXTRA else 'opt_filter'))

def objective(parameters):
    global BEST,COUNT
    COUNT+=1
    point,angle,log_plateau,log_positive,log_envelope=parameters[:5]
    matrix=guard.evaluate_matrices(BACKGROUND,[point])[0]
    eigenvalues,basis=np.linalg.eigh(matrix)
    null=basis[:,:2].copy()
    derivative=guard.evaluate_matrices(2*cheb.chebder(BACKGROUND,axis=0),[point])[0]
    direction=null.T@derivative@basis[:,2]
    direction/=np.linalg.norm(direction)
    perpendicular=np.array([-direction[1],direction[0]])
    basis[:,0]=null@(np.cos(angle)*direction+np.sin(angle)*perpendicular)
    basis[:,1]=null@(-np.sin(angle)*direction+np.cos(angle)*perpendicular)
    spectral=basis.T@BACKGROUND@basis
    additions=np.zeros((3,4,4))
    center=2*point-1
    additions[:,0,0]=np.exp(log_envelope)*cheb.chebmul([-center,1],[-center,1])
    additions[0,0,0]-=DEPTH
    additions[0,1,1]=DEPTH*np.exp(log_plateau)
    additions[0,2,2]=DEPTH*np.exp(log_positive)
    if EXTRA:
        linear=2*parameters[5]*np.sqrt(DEPTH*np.exp(log_envelope))
        additions[:2,0,0]+=linear*np.array([-center,1])
        for coordinate,slope in [(1,parameters[6]),(2,parameters[7])]:
            constant=np.sqrt(additions[0,coordinate,coordinate])
            additions[:,coordinate,coordinate]=cheb.chebmul([constant-slope*center,slope],[constant-slope*center,slope])
    if FOURTH:
        constant=np.exp(parameters[11]/2)
        slope=parameters[12]
        additions[:,3,3]=cheb.chebmul([constant-slope*center,slope],[constant-slope*center,slope])
    scaling=-np.trace(additions,axis1=1,axis2=2)
    scaling[0]+=1
    coefficients=np.zeros((len(spectral)+2,4,4))
    for row in range(4):
        for column in range(4):
            coefficients[:,row,column]=cheb.chebmul(scaling,spectral[:,row,column])
    coefficients[:3]+=additions
    rotation=ROTATION.copy()
    if ROTATE:
        for rotation_angle,(left,right) in zip(parameters[8:11],[(0,1),(0,2),(1,2)]):
            copied=rotation[:,[left,right]].copy()
            rotation[:,left]=np.cos(rotation_angle)*copied[:,0]-np.sin(rotation_angle)*copied[:,1]
            rotation[:,right]=np.sin(rotation_angle)*copied[:,0]+np.cos(rotation_angle)*copied[:,1]
    if min(rotation[:,0]**2)<.010001:
        return 3
    document=package_rotated(coefficients,point,rotation)
    coefficients=unpack(document)
    matrix=guard.evaluate_matrices(coefficients,[point])[0]
    pairs=[(left,right) for left in range(4) for right in range(left+1,4)]
    principal=min(matrix[left,left]*matrix[right,right]-matrix[left,right]**2 for left,right in pairs)
    rowbound=max(np.sum(np.abs(coefficients),axis=(0,2)))
    if principal<1.00001e-5 or min(np.diag(matrix))<.02000001 or rowbound>4 or eigenvalues[0]<-1e-9:
        return 2+max(0,1-principal/1e-5)+max(0,rowbound-4)
    meshmin=np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,MESHES))[:,0].min()
    if meshmin < -DEPTH:
        return -meshmin/DEPTH
    candidates=guard.determinant_candidates(coefficients)
    minimum=min(meshmin,np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,candidates))[:,0].min())
    if minimum>BEST:
        BEST=minimum
        Path(f'{PREFIX}_best.json').write_text(json.dumps(document))
        Path(f'{PREFIX}_parameters.json').write_text(json.dumps(parameters.tolist()))
        print('BEST',COUNT,minimum,parameters.tolist(),time.time()-START,flush=True)
    if minimum>=-guard.NEGATIVE_TOLERANCE:
        reports=guard.screen_all(coefficients)
        print('ESCAPE',COUNT,reports,flush=True)
        Path(f'{PREFIX}_escape_{COUNT}.json').write_text(json.dumps(document))
        if all(report['accepted'] for report in reports):
            Path('witness.json').write_text(json.dumps(document))
            raise SystemExit(0)
    if COUNT%500==0:
        print('PROGRESS',COUNT,BEST,time.time()-START,flush=True)
    return -minimum/DEPTH

if __name__=='__main__':
    location=np.searchsorted(MESHES,BASE_POINT)
    bounds=[(MESHES[location-1]+1e-5,MESHES[location]-1e-5),(-1.5,1.5),(np.log(2),np.log(100)),(np.log(.05),np.log(100)),(np.log(1e-6),np.log(.1))]
    initial=[BASE_POINT,0,np.log(GEOMETRY['plateau']),np.log(GEOMETRY['positive']),np.log(ENVELOPE)]
    if EXTRA:
        bounds += [(-3,3),(-.2,.2),(-.2,.2)]
        initial += [0,0,0]
    if ROTATE:
        bounds += [(-.5,.5)]*3
        initial=json.loads(Path('extra_filter_parameters.json').read_text())+[0,0,0]
    if FOURTH:
        bounds += [(-18,-3),(-.3,.3)]
        initial += [-18,0]
    result=differential_evolution(objective,bounds,popsize=10 if FOURTH else 12,maxiter=90 if ROTATE else 120,tol=1e-6,seed=737130 if FOURTH else (737129 if ROTATE else (737128 if EXTRA else 737127)),polish=False,x0=initial)
    print('DONE',result.fun,result.x.tolist(),flush=True)
