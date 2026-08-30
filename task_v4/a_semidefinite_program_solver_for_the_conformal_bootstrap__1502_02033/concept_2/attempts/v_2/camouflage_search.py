from investigate import *
from quartic_search import MESHES

def main():
    data=json.loads(Path('optimized_background.json').read_text())
    background=np.array(data['coefficients'])
    point=data['point']
    center=2*point-1
    geometry=json.loads(Path('geometry_product.json').read_text())
    rotation=np.array(geometry['rotation'])
    square=cheb.chebmul([-center,1],[-center,1])
    quartic=cheb.chebmul(square,square)
    depth=1.02e-7
    additions=np.zeros((5,4,4))
    additions[:3,0,0]=data['envelope']*square
    additions[0,0,0]-=depth
    additions[0,1,1]=depth*geometry['plateau']
    additions[0,2,2]=depth*geometry['positive']
    random=np.random.default_rng(9271753)
    best=-1e99
    start=time.time()
    for trial in range(3000):
        directions=random.normal(size=(4,int(random.integers(1,5))))
        projector=directions@directions.T
        projector/=np.trace(projector)
        strength=random.uniform(.0001,.9/(1+abs(center))**4)
        correction=additions+strength*quartic[:,None,None]*projector
        scaling=-np.trace(correction,axis1=1,axis2=2)
        scaling[0]+=1
        coefficients=np.zeros((len(background)+4,4,4))
        for row in range(4):
            for column in range(4):
                coefficients[:,row,column]=cheb.chebmul(scaling,background[:,row,column])
        coefficients[:5]+=correction
        document=package_rotated(coefficients,point,rotation)
        coefficients=unpack(document)
        if max(np.sum(np.abs(coefficients),axis=(0,2)))>4:
            continue
        candidates=guard.determinant_candidates(coefficients)
        points=np.concatenate((MESHES,candidates))
        minimum=np.linalg.eigvalsh(guard.evaluate_matrices(coefficients,points))[:,0].min()
        if minimum>best:
            best=minimum
            Path('camouflage_best.json').write_text(json.dumps(document))
            print('BEST',trial,minimum,strength,time.time()-start,flush=True)
        if minimum>=-guard.NEGATIVE_TOLERANCE:
            reports=guard.screen_all(coefficients)
            print('ESCAPE',trial,reports,flush=True)
            Path(f'camouflage_escape_{trial}.json').write_text(json.dumps(document))
            if all(report['accepted'] for report in reports):
                Path('witness.json').write_text(json.dumps(document))
                return
        if trial%500==0:
            print('PROGRESS',trial,best,time.time()-start,flush=True)
    print('DONE',best,time.time()-start,flush=True)

if __name__=='__main__':
    main()
