from optimize_geometry import *

def target(parameters):
    rotation,plateau,positive,slope,width,centers,ratio,minor = details(parameters)
    penalty = 1000*max(0,.011-min(rotation[:,0]**2))+1000*max(0,.021-min(rotation[:,3]**2))
    penalty += 100*max(0,max(rotation[:,1]**2-plateau*rotation[:,0]**2))
    penalty += 100*max(0,1.05-ratio)
    return np.log(plateau/max(minor,1e-10))+penalty

if __name__=='__main__':
    result=differential_evolution(target,[(-np.pi,np.pi)]*6+[(0,np.log(30)),(-3,4),(-.95,.95)],popsize=25,maxiter=1200,seed=31195,workers=1,polish=False)
    rotation,plateau,positive,slope,width,centers,ratio,minor=details(result.x)
    record=dict(plateau=plateau,positive=positive,slope=slope,width=width,centers=centers.tolist(),ratio=ratio,minor=minor,rotation=rotation.tolist(),score=float(result.fun))
    Path('geometry_product.json').write_text(json.dumps(record))
    print(record,flush=True)
