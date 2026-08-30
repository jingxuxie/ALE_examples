from investigate import *
from scipy.optimize import differential_evolution
import itertools

PAIRS = list(itertools.combinations(range(4),2))

def details(parameters):
    rotation = np.eye(4)
    for angle, (first, second) in zip(parameters[:6], PAIRS):
        cosine = np.cos(angle)
        sine = np.sin(angle)
        copied = rotation[:,[first,second]].copy()
        rotation[:,first] = cosine*copied[:,0]-sine*copied[:,1]
        rotation[:,second] = sine*copied[:,0]+cosine*copied[:,1]
    first, second, third, fourth = rotation.T
    plateau = np.exp(parameters[6])
    positive = np.exp(parameters[7])
    slope = parameters[8]*np.sqrt(plateau)
    width = np.sqrt(plateau/(positive*(plateau-slope**2)))
    curvature = positive*(second-slope*first)**2+(plateau-slope*slope)*third**2
    centers = (plateau*first-slope*second)*third/curvature
    ratio = min(abs(centers))/width
    minor = min((third[left]*fourth[right]-third[right]*fourth[left])**2 for left,right in PAIRS)
    return rotation, plateau, positive, slope, width, centers, ratio, minor

def objective(parameters):
    rotation, plateau, positive, slope, width, centers, ratio, minor = details(parameters)
    penalty = 100*max(0, .011-min(rotation[:,0]**2)) + 100*max(0,.021-min(rotation[:,3]**2)) + 50*max(0,.025-minor)
    penalty += 10*max(0,max(rotation[:,1]**2-plateau*rotation[:,0]**2))
    return -ratio+penalty

if __name__ == '__main__':
    for maximum in [8, 16, 32]:
        result = differential_evolution(objective,[(-np.pi,np.pi)]*6+[(0,np.log(maximum)),(-3,4),(-.95,.95)],popsize=20,maxiter=1000,seed=8223+maximum,workers=1,polish=False)
        rotation,plateau,positive,slope,width,centers,ratio,minor = details(result.x)
        record = dict(plateau=plateau,positive=positive,slope=slope,width=width,centers=centers.tolist(),ratio=ratio,minor=minor,rotation=rotation.tolist(),score=float(result.fun))
        Path(f'geometry_optimized_{maximum}.json').write_text(json.dumps(record))
        print(maximum,record,flush=True)
