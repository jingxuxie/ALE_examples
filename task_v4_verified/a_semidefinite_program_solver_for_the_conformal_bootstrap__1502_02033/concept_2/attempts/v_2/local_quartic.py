from investigate import *
from numpy.polynomial import polynomial as poly

def local_score(parameter, divisor, skew, plateau, coupling):
    first = np.array([-1.,0,1.])
    factor = np.array([-parameter,skew,1.])/np.sqrt(divisor)
    second = poly.polymul(factor,factor)
    second[0] += plateau
    mixed = np.concatenate(([0],coupling*factor))
    candidates=[]
    for row in range(4):
        left,right = ROTATION_NUMERATORS[row,:2]/5
        determinant = poly.polyadd(left*left*second,right*right*first)
        determinant = poly.polyadd(determinant,-2*left*right*mixed)
        candidates.extend(poly.polyroots(determinant).real)
        candidates.extend(poly.polyroots(poly.polyder(determinant)).real)
    candidates=np.array(candidates)
    low=poly.polyval(candidates,first)
    high=poly.polyval(candidates,second)
    cross=poly.polyval(candidates,mixed)
    eigenvalues=(low+high-np.sqrt((low-high)**2+4*cross**2))/2
    return eigenvalues.min(),parameter*parameter/divisor+plateau

if __name__ == '__main__':
    random=np.random.default_rng(5271)
    best=-1e10
    records=[]
    for trial in range(50000):
        parameter=random.uniform(2,40)
        divisor=10**random.uniform(-.3,2)
        skew=random.uniform(-20,20)
        plateau=10**random.uniform(-3,1)
        coupling=random.uniform(-.8,.8)
        if parameter*parameter/divisor+plateau<4.01:
            continue
        minimum,center=local_score(parameter,divisor,skew,plateau,coupling)
        if minimum>=0:
            records.append(dict(parameter=parameter,divisor=divisor,skew=skew,plateau=plateau,coupling=coupling,minimum=minimum,center=center))
        score=minimum-.005*center
        if score>best:
            best=score
            print('BEST',trial,score,minimum,center,parameter,divisor,skew,plateau,coupling,flush=True)
    records.sort(key=lambda record:record['center'])
    Path('local_quartic_good.json').write_text(json.dumps(records))
    print('DONE',len(records),flush=True)
