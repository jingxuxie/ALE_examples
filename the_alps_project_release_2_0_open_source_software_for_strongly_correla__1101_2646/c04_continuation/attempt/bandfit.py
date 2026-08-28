import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import time
import numpy as np
import scipy.linalg as la
from scipy.optimize import least_squares
from continuation import hermitian, spectral_green, norm_rows


def hermitian_basis(dimension):
    basis = []
    for orbital in range(dimension):
        matrix = np.zeros((dimension, dimension), complex)
        matrix[orbital, orbital] = 1
        basis.append(matrix)
    for row in range(dimension):
        for column in range(row + 1, dimension):
            matrix = np.zeros((dimension, dimension), complex)
            matrix[row, column] = matrix[column, row] = 1 / np.sqrt(2)
            basis.append(matrix)
            matrix = np.zeros((dimension, dimension), complex)
            matrix[row, column] = 1j / np.sqrt(2)
            matrix[column, row] = -1j / np.sqrt(2)
            basis.append(matrix)
    return np.array(basis)


def band_green(nodes, static, coefficients, count=512):
    phase = 2 * np.pi * np.arange(count) / count
    functions = np.array([function(order * phase) for order in range(1, len(coefficients) // 2 + 1) for function in [np.cos, np.sin]])
    hamiltonian = static + np.einsum('pk,pij->kij', functions, coefficients)
    energies, vectors = np.linalg.eigh(hamiltonian)
    residues = np.einsum('kia,kja->kaij', vectors, vectors.conj()).reshape(-1, len(static), len(static)) / count
    return spectral_green(nodes, energies.ravel(), residues)


def band_green_exact(nodes, static, coefficients):
    while len(coefficients) > 2 and la.norm(coefficients[-2:]) < 1e-13 * max(1,la.norm(coefficients)):
        coefficients = coefficients[:-2]
    dimension = len(static)
    harmonics = len(coefficients) // 2
    degree = 2 * harmonics
    polynomial = np.zeros((degree + 1, dimension, dimension), complex)
    for harmonic in range(1, harmonics + 1):
        cosine = coefficients[2 * harmonic - 2]
        sine = coefficients[2 * harmonic - 1]
        polynomial[harmonics + harmonic] = -(cosine - 1j * sine) / 2
        polynomial[harmonics - harmonic] = -(cosine + 1j * sine) / 2
    size = dimension * degree
    pencil = np.zeros((size,size),complex)
    pencil[:size-dimension,dimension:] = np.eye(size-dimension)
    metric = np.eye(size,dtype=complex)
    metric[-dimension:,-dimension:] = polynomial[-1]
    result = []
    for node in nodes:
        polynomial[harmonics] = node*np.eye(dimension)-static
        pencil[-dimension:] = -polynomial[:-1].transpose(1,0,2).reshape(dimension,size)
        roots,left,right = la.eig(pencil,metric,left=True,right=True,check_finite=False)
        selected = np.isfinite(roots)&(np.abs(roots)<1)
        roots = roots[selected]
        left = left[-dimension:,selected].T.conj()
        right = right[:dimension,selected].T
        powers = roots[:,None]**np.arange(degree)[None,:]
        derivative = np.einsum('rk,kij->rij',powers,polynomial[1:]*np.arange(1,degree+1)[:,None,None])
        normalization = np.einsum('ri,rij,rj->r',left,derivative,right)
        residues = np.einsum('ri,rj,r->rij',right,left,roots**(harmonics-1)/normalization)
        result.append(np.sum(residues,axis=0))
    return np.array(result)


def fit_band(nodes, values, static, covariance, harmonics=1, initial=None, seconds=20, seed=0, minimum_imag=.3, quadrature=128, method='lm', exact=False):
    started = time.monotonic()
    dimension = len(static)
    basis = hermitian_basis(dimension)
    selected = np.flatnonzero((nodes.imag >= minimum_imag) & (nodes.imag < 6))
    if len(selected) < 10:
        selected = np.arange(len(nodes))
    selected = selected[np.unique(np.round(np.linspace(0, len(selected)-1,min(18,len(selected)))).astype(int))]
    nodes = nodes[selected]
    values = values[selected]
    count = quadrature
    phase = 2*np.pi*np.arange(count)/count
    functions = np.array([function(order * phase) for order in range(1,harmonics+1) for function in [np.cos,np.sin]])
    weight = np.maximum(1,np.abs(nodes)) ** 2
    if initial is None:
        rng = np.random.default_rng(seed)
        eigenvalues,vectors = la.eigh(covariance)
        root = (vectors*np.sqrt(np.maximum(eigenvalues,0)))@vectors.conj().T
        trial = hermitian(rng.normal(size=(dimension,dimension))+1j*rng.normal(size=(dimension,dimension)))
        sine = (root@trial+trial@root)*.15/la.norm(trial)
        eigenvalues,vectors = la.eigh(2*covariance-sine@sine)
        cosine = (vectors*np.sqrt(np.maximum(eigenvalues,0)))@vectors.conj().T
        initial = np.array([cosine,sine]+[np.zeros_like(cosine)]*(2*harmonics-2))
    parameters = np.einsum('pij,hij->hp',basis.conj(),initial).real.ravel()
    cache = {}
    best = {'error':np.inf,'parameters':parameters.copy()}
    def objective(parameters, derivative=False):
        if time.monotonic()-started > seconds:
            raise TimeoutError
        if 'parameters' not in cache or not np.array_equal(parameters,cache['parameters']):
            coefficients = np.einsum('hp,pij->hij',parameters.reshape(2*harmonics,-1),basis)
            hamiltonian = static + np.einsum('hk,hij->kij',functions,coefficients)
            resolvents = np.linalg.inv(nodes[:,None,None,None]*np.eye(dimension)-hamiltonian)
            fitted = band_green_exact(nodes,static,coefficients) if exact else np.mean(resolvents,axis=1)
            covariance_fit = np.einsum('hij,hjk->ik',coefficients,coefficients)*.5
            residual = np.r_[((fitted-values)*weight[:,None,None]).ravel(), ((covariance_fit-covariance)*.5).ravel()]
            cache['parameters'] = parameters.copy()
            cache['residual'] = np.r_[residual.real,residual.imag]*1e3
            cache['resolvents'] = resolvents
            cache['coefficients'] = coefficients
            cache.pop('jacobian',None)
            error = la.norm(cache['residual'])/1e3
            if error < best['error']:
                best['error'] = error
                best['parameters'] = parameters.copy()
            if error < 1e-13:
                raise TimeoutError
        if derivative and 'jacobian' not in cache:
            resolvents = cache['resolvents']
            coefficients = cache['coefficients']
            derivative_green = np.einsum('zkia,pab,zkbj,hk->zhpij',resolvents,basis,resolvents,functions,optimize=True)/count
            derivative_green *= weight[:,None,None,None,None]
            derivative_covariance = (np.einsum('hij,pjk->hpik',coefficients,basis)+np.einsum('pij,hjk->hpik',basis,coefficients))*.25
            jacobian = np.r_[derivative_green.transpose(0,3,4,1,2).reshape(-1,len(parameters)),derivative_covariance.transpose(2,3,0,1).reshape(-1,len(parameters))]
            cache['jacobian'] = np.r_[jacobian.real,jacobian.imag]*1e3
        return cache['jacobian'] if derivative else cache['residual']
    try:
        solution = least_squares(objective,parameters,jac=lambda parameters: objective(parameters,True),method=method,x_scale='jac' if method=='lm' else 1.,max_nfev=2000,ftol=1e-13,xtol=1e-13,gtol=1e-10)
        parameters = solution.x
        error = la.norm(solution.fun)/1e3
    except TimeoutError:
        parameters = best['parameters']
        error = best['error']
    coefficients = np.einsum('hp,pij->hij',parameters.reshape(2*harmonics,-1),basis)
    return coefficients,error,time.monotonic()-started


def try_band_model(nodes, values, moments, points, bound, reference, seconds=50, residual=None):
    started = time.monotonic()
    dimension = values.shape[-1]
    static = hermitian(moments[1])
    covariance = hermitian(moments[2]-static@static)
    noise = 10*dimension*bound if residual is None else min(10*dimension*bound,20*residual)
    tolerance = max(noise,2e-13*max(1,np.max(norm_rows(values))))
    def remaining():
        return max(0,seconds-(time.monotonic()-started))
    def validate(coefficients):
        phase = np.linspace(0,2*np.pi,129)[:-1]
        functions = np.array([function(order*phase) for order in range(1,len(coefficients)//2+1) for function in [np.cos,np.sin]])
        energies = np.linalg.eigvalsh(static+np.einsum('hk,hij->kij',functions,coefficients))
        if np.max(np.abs(energies)) > 1.025:
            return None,np.inf
        fitted = band_green_exact(nodes,static,coefficients)
        error = np.max(norm_rows(fitted-values))
        if not np.isfinite(error) or error > tolerance:
            return None,error
        prediction = band_green_exact(points,static,coefficients)
        if not np.all(np.isfinite(prediction)):
            return None,error
        disagreement = la.norm(prediction-reference)/max(la.norm(prediction),1e-15)
        if disagreement > .3:
            return None,error
        minimum = np.min(np.linalg.eigvalsh(hermitian(1j*prediction)))
        if minimum < -1e-9:
            return None,error
        return prediction,error
    coefficients = None
    for stage in range(3):
        if remaining() < 1:
            break
        harmonics = 1 if stage==0 else 2
        initial = None if stage in [0,2] else np.r_[coefficients,np.zeros_like(coefficients)]
        allowance = min(remaining(),8 if stage==0 else (remaining()*.7 if stage==1 else remaining()))
        coefficients,error,elapsed = fit_band(nodes,values,static,covariance,harmonics,initial,seconds=allowance,seed=stage,method='trf' if dimension==4 and stage==0 else 'lm')
        if error < 2e-7:
            prediction,validation_error = validate(coefficients)
            if prediction is not None:
                return prediction
            if remaining() > 2 and validation_error < .01:
                count = int(min(1024,max(256,2**np.ceil(np.log2(15/max(np.min(nodes.imag),.001))))))
                refined,refined_error,elapsed = fit_band(nodes,values,static,covariance,harmonics,coefficients,seconds=min(12,remaining()),minimum_imag=np.min(nodes.imag),quadrature=count,exact=True)
                prediction,validation_error = validate(refined)
                if prediction is not None:
                    return prediction
    return None


def run():
    from research import generated,metrics
    for kind in ['scalarband','band','band2']:
        for seed in [1,2,3]:
            case = generated(kind,seed,dimension=2+seed%3,error=0)
            center = np.mean(case['support'])
            scale = np.diff(case['support'])[0]/2
            static = (case['moments'][1]-center*np.eye(len(case['bare'])))/scale
            covariance = (case['moments'][2]-case['moments'][1]@case['moments'][1])/scale**2
            for harmonics in [1,2] if kind!='scalarband' else [1]:
                initial = None
                if harmonics==2:
                    initial = np.r_[coefficients,np.zeros_like(coefficients)]
                coefficients,error,elapsed = fit_band((1j*case['iw']-center)/scale,case['data']*scale,static,covariance,harmonics,initial,seconds=10)
                prediction = band_green((case['omega']+1j*case['eta']-center)/scale,static,coefficients)/scale
                actual_error = la.norm(band_green((1j*case['iw']-center)/scale,static,coefficients)-case['data']*scale)
                print('BANDRESULT',kind,seed,harmonics,error,actual_error,metrics(prediction,case),elapsed,flush=True)


if __name__=='__main__':
    run()
