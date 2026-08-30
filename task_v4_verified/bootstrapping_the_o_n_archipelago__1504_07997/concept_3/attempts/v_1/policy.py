import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import json
import math
import sys
import ctypes
for library in ('libopenblas.so.0', 'libblas.so.3', 'liblapack.so.3'):
    try:
        ctypes.CDLL('/usr/lib/x86_64-linux-gnu/openblas-pthread/' + library, mode=ctypes.RTLD_GLOBAL)
    except OSError:
        pass
import numpy as np
from scipy.linalg import cholesky, solve_triangular, cho_solve
from scipy.optimize import least_squares

TARGETS = ('delta0', 'log_gap', 'log_a0', 'theta0')
SCALES = np.array([.05, .35, .25, .15])
TIMES = np.array([.25, .4, .6, .8, 1., 1.25, 1.5, 1.75, 2., 2.25,
                  2.5, 2.75, 3., 3.25, 3.5, 3.75, 4., 4.25, 4.5, 4.75,
                  5., 5.25, 5.5, 5.75, 6.])

def noise_std(times):
    return 1.2e-5 + 2.5e-4 * np.exp(-1.1 * np.asarray(times))

def canonical(angle):
    return (angle + np.pi / 2) % np.pi - np.pi / 2

def uniform_laplace(times, lower, upper):
    return np.exp(-lower * times) * (-np.expm1(-(upper-lower)*times)) / ((upper-lower)*times)

def tail_moments(times):
    sums = times[:, None] + times[None, :]
    first = uniform_laplace(times, 3., 3.3)
    rest = uniform_laplace(times, 3., 8.)
    first_sum = uniform_laplace(sums, 3., 3.3)
    rest_sum = uniform_laplace(sums, 3., 8.)
    mean_atom = np.zeros(len(times))
    second_atom = np.zeros_like(sums)
    same_atom = np.zeros_like(sums)
    for count in range(4, 11):
        mean_atom += (first + (count-1)*rest) / count / 7
        same = 1.7 / (count*(.7*count+1)) * (first_sum+(count-1)*rest_sum)
        cross = .7 / (count*(.7*count+1)) * ((count-1)*(np.outer(first,rest)+np.outer(rest,first)) + (count-1)*(count-2)*np.outer(rest,rest))
        second_atom += (same+cross)/7
        same_atom += same/7
    nodes, weights = np.polynomial.legendre.leggauss(16)
    continuum_scale = .625 + .275 * nodes
    continuum = np.concatenate([np.exp(-3*times[None,:]) / (1+continuum_scale[:,None]*times[None,:])**shape for shape in (1,2,3)])
    weights = np.tile(weights/6, 3)
    mean_cont = weights @ continuum
    second_cont = (continuum.T*weights) @ continuum
    mean = .7*mean_atom + .3*mean_cont
    second = .4975*second_atom + .0975*second_cont + .2025*(np.outer(mean_atom,mean_cont)+np.outer(mean_cont,mean_atom))
    anis = .4975*.125*same_atom + .0975*(.64/24)*second_cont
    return mean, second, anis

class Tail:
    def __init__(self, mass=None):
        mean, second, anis = tail_moments(TIMES)
        mass_mean = ((2.-.4)/np.log(5)*5 + (10.-4)/np.log(2.5))/6
        mass_second = ((4.-.16)/(2*np.log(5))*5 + (100.-16)/(2*np.log(2.5)))/6
        self.mass_mean = mass_mean
        self.mass_variance = mass_second-mass_mean**2
        self.mean_shape = mean
        self.mean = .5 * mass_mean * mean
        self.trace = .25*mass_second*second - np.outer(.5*mass_mean*mean,.5*mass_mean*mean)
        self.anis = mass_second*anis
        if mass is not None:
            self.mass_mean = mass
            self.mean = .5*mass*mean
            self.trace = .25*mass**2*(second-np.outer(mean,mean)) + .25*self.mass_variance*np.outer(mean,mean)
            self.anis = mass**2*anis
        components = []
        for matrix in (self.trace, self.anis):
            eigenvalues, eigenvectors = np.linalg.eigh(matrix)
            keep = eigenvalues > eigenvalues[-1]*1e-14
            components.append(eigenvectors[:,keep]*np.sqrt(eigenvalues[keep]))
        self.trace_features, self.anis_features = components

    def features(self, indexes, angles):
        anis = self.anis_features[indexes]
        return np.column_stack([self.trace_features[indexes], anis*np.cos(2*angles[:,None]), anis*np.sin(2*angles[:,None])])

def predict(parameters, times, angles, jacobian=False):
    delta, log_gap, log_a0, theta0, log_a1, theta1 = parameters
    gap = np.exp(log_gap)
    cosine0 = np.cos(angles-theta0)
    cosine1 = np.cos(angles-theta1)
    weight0 = np.exp(log_a0-delta*times)
    weight1 = np.exp(log_a1-(delta+gap)*times)
    term0 = weight0*cosine0**2
    term1 = weight1*cosine1**2
    values = term0+term1
    if not jacobian:
        return values
    derivatives = np.column_stack([-times*values, -times*gap*term1, term0,
                                    weight0*np.sin(2*(angles-theta0)), term1,
                                    weight1*np.sin(2*(angles-theta1))])
    return values, derivatives

def initial_parameters(indexes, angles, values):
    matrices = []
    matrix_times = []
    for index in np.unique(indexes):
        selected = indexes == index
        if np.sum(selected) < 3 or TIMES[index] < 2:
            continue
        design = np.column_stack([np.cos(angles[selected])**2, np.sin(2*angles[selected]), np.sin(angles[selected])**2])
        if np.linalg.matrix_rank(design) < 3:
            continue
        entries = np.linalg.lstsq(design, values[selected], rcond=None)[0]
        matrices.append(np.array([[entries[0],entries[1]],[entries[1],entries[2]]]))
        matrix_times.append(TIMES[index])
    starts = []
    if len(matrices) >= 2:
        for earlier, later in [(0,1),(0,len(matrices)-1)]:
            try:
                root = cholesky(matrices[earlier], lower=True)
                inverse = np.linalg.inv(root)
                eigenvalues, eigenvectors = np.linalg.eigh(inverse@matrices[later]@inverse.T)
                exponents = -np.log(np.maximum(eigenvalues,1e-8))/(matrix_times[later]-matrix_times[earlier])
                order = np.argsort(exponents)
                vectors = root@eigenvectors[:,order]
                exponents = exponents[order]
                strengths = np.sum(vectors**2,axis=0)*np.exp(exponents*matrix_times[earlier])
                starts.append(np.array([exponents[0],np.log(max(.045,exponents[1]-exponents[0])),np.log(strengths[0]),np.arctan2(vectors[1,0],vectors[0,0]),np.log(strengths[1]),np.arctan2(vectors[1,1],vectors[0,1])]))
            except (ValueError, np.linalg.LinAlgError):
                pass
    return starts

class Policy:
    def __init__(self, initial_angles=3, adaptive_tail=True):
        self.tail = Tail()
        self.records = []
        self.parameters = None
        self.covariance = None
        self.initial_angles = initial_angles
        self.adaptive_tail = adaptive_tail

    def arrays(self):
        records = np.asarray(self.records)
        return records[:,0].astype(int), records[:,1], records[:,2]

    def fit(self):
        indexes, angles, values = self.arrays()
        times = TIMES[indexes]
        features = self.tail.features(indexes, angles)
        covariance = features@features.T + np.diag(noise_std(times)**2)
        root = cholesky(covariance, lower=True)
        whitening = solve_triangular(root,np.eye(len(times)),lower=True)
        observed = values-self.tail.mean[indexes]
        def residual(parameters):
            return whitening@(predict(parameters,times,angles)-observed)
        def jacobian(parameters):
            return whitening@predict(parameters,times,angles,True)[1]
        lower = np.array([.8,np.log(.045),np.log(.035),-10.,np.log(.4),-10.])
        upper = np.array([1.15,np.log(.85),np.log(1.5),10.,np.log(2.1),10.])
        starts = []
        if self.parameters is not None:
            starts.append(self.parameters)
        initial_count = len(self.initial_design())
        starts.extend(initial_parameters(indexes[:initial_count],angles[:initial_count],values[:initial_count]))
        if self.parameters is None:
            rng = np.random.default_rng(721)
            for restart in range(6):
                starts.append(np.array([.97,np.log(.085 if restart<2 else .58),np.log(.5),rng.uniform(-np.pi/2,np.pi/2),np.log(1.),rng.uniform(-np.pi/2,np.pi/2)]))
        best = None
        for initial in starts:
            initial = initial.copy()
            initial[3] = canonical(initial[3])
            initial[5] = canonical(initial[5])
            result = least_squares(residual,np.clip(initial,lower+1e-8,upper-1e-8),jac=jacobian,bounds=(lower,upper),max_nfev=200,ftol=1e-9,xtol=1e-9,gtol=1e-7)
            if best is None or result.cost < best.cost:
                best = result
        self.parameters = best.x
        singular_values, right_vectors = np.linalg.svd(best.jac,full_matrices=False)[1:]
        self.covariance = (right_vectors.T / np.maximum(singular_values,1e-8)**2)@right_vectors
        self.cost = 2*best.cost
        self.mass_estimate = self.tail.mass_mean + .5*self.tail.mass_variance*self.tail.mean_shape[indexes]@cho_solve((root,True),observed-predict(best.x,times,angles))
        return self.parameters

    def reweight_tail(self):
        if self.adaptive_tail:
            self.tail = Tail(mass=float(np.clip(self.mass_estimate,.35,10.)))
            self.fit()

    def initial_design(self):
        return [(index, angle) for index in (0,2,4,6,8,11,15,20) for angle in np.arange(self.initial_angles)*np.pi/self.initial_angles]

    def design(self, count):
        indexes, angles, values = self.arrays()
        sigma = noise_std(TIMES[indexes])
        features = self.tail.features(indexes,angles)
        jacobian = predict(self.parameters,TIMES[indexes],angles,True)[1]
        parameter_scale = np.array([.05,.35,.25,.15,.25,.15])
        design = np.column_stack([jacobian*parameter_scale,features])/sigma[:,None]
        precision = design.T@design
        precision[6:,6:] += np.eye(features.shape[1])
        precision[:6,:6] += np.eye(6)*1e-7
        covariance = np.linalg.inv(precision)
        candidate_angles = np.arange(24)*np.pi/24
        candidate_angles = np.concatenate([candidate_angles, [self.parameters[3]+offset for offset in (0,np.pi/4,np.pi/2,3*np.pi/4)], [self.parameters[5]+offset for offset in (0,np.pi/4,np.pi/2,3*np.pi/4)]])
        candidate_indexes = np.repeat(np.arange(len(TIMES)),len(candidate_angles))
        candidate_angles = np.tile(candidate_angles,len(TIMES))
        candidate_sigma = noise_std(TIMES[candidate_indexes])
        candidate_features = self.tail.features(candidate_indexes,candidate_angles)
        candidate_jacobian = predict(self.parameters,TIMES[candidate_indexes],candidate_angles,True)[1]
        candidates = np.column_stack([candidate_jacobian*parameter_scale,candidate_features])/candidate_sigma[:,None]
        queries = []
        for step in range(count):
            projection = candidates@covariance
            denominator = 1+np.sum(projection*candidates,axis=1)
            updated = np.diag(covariance)[:4]-projection[:,:4]**2/denominator[:,None]
            risk = np.sum(np.sqrt(np.maximum(updated,1e-15)),axis=1)
            choice = np.argmin(risk)
            covariance -= np.outer(projection[choice],projection[choice])/denominator[choice]
            queries.append((int(candidate_indexes[choice]),float(candidate_angles[choice])))
        return queries

    def answer(self):
        estimate = self.parameters[:4].copy()
        estimate[3] = canonical(estimate[3])
        radii = 1.1*1.645*np.sqrt(np.maximum(0,np.diag(self.covariance)[:4]))
        radii = np.clip(radii,1e-6,[.3,2.,2.,np.pi/2])
        return estimate, radii

    def run(self, measure):
        for index,angle in self.initial_design():
            value = measure(float(TIMES[index]),[math.cos(angle),math.sin(angle)])
            self.records.append((index,angle,value))
        self.fit()
        self.reweight_tail()
        remaining = 72-len(self.records)
        for count in (remaining//2, remaining-remaining//2):
            for index,angle in self.design(count):
                value = measure(float(TIMES[index]),[math.cos(angle),math.sin(angle)])
                self.records.append((index,angle,value))
            self.fit()
            self.reweight_tail()
        return self.answer()

def main():
    hello = json.loads(sys.stdin.readline())
    def measure(time,probe):
        print(json.dumps({'type':'measure','t':time,'u':probe}),flush=True)
        response = json.loads(sys.stdin.readline())
        return float(response['y'])
    estimate,radii = Policy().run(measure)
    print(json.dumps({'type':'answer','estimate':dict(zip(TARGETS,estimate.tolist())),
                      'radius90':dict(zip(TARGETS,radii.tolist()))},allow_nan=False),flush=True)

if __name__ == '__main__':
    main()
