from investigate import *
from scipy.optimize import differential_evolution

rotation = ROTATION_NUMERATORS / 5
first, second, third = rotation[:,:3].T

def objective(parameters):
    plateau, positive, slope = parameters
    determinant_curve = positive*(plateau-slope**2)
    if determinant_curve <= 0:
        return 1000
    width = np.sqrt(plateau/determinant_curve)
    curvature = positive*(second-slope*first)**2+(plateau-slope*slope)*third**2
    centers = (plateau*first-slope*second)*third/curvature
    return -min(abs(centers))/width

result = differential_evolution(objective, [(4.01,100),(.01,100),(-9.99,9.99)],popsize=30,maxiter=500,tol=1e-10,seed=9840)
print(result.fun,result.x)
