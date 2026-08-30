import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize, Bounds, LinearConstraint
from scipy.special import expit, logsumexp
from exact import SPINS, LOWER, BOUND, energies, evaluate, save

class Problem:
    def __init__(self, witness):
        self.witness = witness
        self.spins = SPINS[::2, witness['order']].copy()
        self.energy = energies(witness['bonds'])[::2].copy()
        distance = (16-SPINS[::2] @ witness['pattern'])/2
        self.sector = ((distance <= witness['radius']) | (distance >= 16-witness['radius'])).astype(float)
        self.last = None
        self.calls = 0
        self.start = time.time()

    def calc(self, parameters):
        if self.last is not None and np.array_equal(parameters, self.last):
            return self.result
        self.last = parameters.copy()
        self.calls += 1
        weights = np.zeros((16, 16))
        weights[LOWER] = parameters[:120]-parameters[120:240]
        beta = parameters[-1]
        logits = self.spins @ weights.T
        logq = -np.logaddexp(0, -self.spins*logits).sum(axis=1)
        proposal = 2*np.exp(logq)
        score = (self.spins+1)/2-expit(logits)
        potential = beta*self.energy
        target = np.exp(-potential-logsumexp(-potential))
        reward = potential+logq
        centered = reward-proposal @ reward
        meanq = proposal @ self.energy
        meanp = target @ self.energy
        energyvar = target @ (self.energy-meanp)**2
        variance = proposal @ centered**2
        entropy = -proposal @ logq
        kl = proposal @ reward+logsumexp(-potential)+np.log(2.)
        error = beta*(meanq-meanp)
        qmass = proposal @ self.sector
        pmass = target @ self.sector

        def derivative(factor, betaderivative):
            matrix = (score*(proposal*factor)[:, None]).T @ self.spins
            lower = matrix[LOWER]
            return np.r_[lower, -lower, betaderivative]

        varjac = derivative(centered**2+2*centered, 2*(proposal*centered) @ self.energy)
        hjac = derivative(-logq, 0.)
        kljac = derivative(centered, meanq-meanp)
        ejac = derivative(potential, meanq-meanp+beta*energyvar)
        qjac = derivative(self.sector, 0.)
        pjac = np.zeros(241)
        pjac[-1] = -(target*self.sector) @ (self.energy-meanp)
        constraint = np.array([entropy-3.001, kl-.401, .319-error, .319+error, .000999-qmass, pmass-.3501])
        cjac = np.array([hjac, kljac, -ejac, ejac, -qjac, pjac])
        self.result = variance, varjac, constraint, cjac
        self.metrics = dict(variance=variance, entropy=entropy, kl=kl, energy_error=abs(error)/16,
                            qmass=qmass, pmass=pmass, gradient=np.abs(kljac[:120]).max(), beta=beta)
        self.weights = weights
        return self.result

    def objective(self, parameters):
        result = self.calc(parameters)
        return result[0], result[1]

    def constraints(self, parameters):
        return self.calc(parameters)[2]

    def jacobian(self, parameters):
        return self.calc(parameters)[3]

def run(witness, output, maxiter=400, ftol=1e-10):
    problem = Problem(witness)
    lower = np.array(witness['weights'])[LOWER]
    initial = np.r_[np.maximum(lower, 0), np.maximum(-lower, 0), witness['beta']]
    matrix = np.zeros((15, 241))
    for row in range(1, 16):
        indices = np.flatnonzero(LOWER[0] == row)
        matrix[row-1, indices] = 1
        matrix[row-1, indices+120] = 1
    linear = LinearConstraint(matrix, -np.inf, BOUND-1e-10)
    bounds = Bounds(np.r_[np.zeros(240), 1.], np.r_[np.full(240, BOUND), 3.])
    iteration = [0]
    def callback(parameters):
        iteration[0] += 1
        problem.calc(parameters)
        if iteration[0] % 10 == 0:
            print(iteration[0], 'seconds', round(time.time()-problem.start, 2), problem.metrics, flush=True)
            current = dict(witness, weights=problem.weights.tolist(), beta=float(parameters[-1]))
            save(current, output)
    result = minimize(problem.objective, initial, method='SLSQP', jac=True, bounds=bounds,
                      constraints=[linear, {'type':'ineq', 'fun':problem.constraints, 'jac':problem.jacobian}],
                      callback=callback, options=dict(maxiter=maxiter, ftol=ftol, disp=True))
    problem.calc(result.x)
    current = dict(witness, weights=problem.weights.tolist(), beta=float(result.x[-1]))
    save(current, output)
    print(json.dumps(evaluate(current, find_sector=True), indent=2), flush=True)
    return current

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', default='optimized.json')
    parser.add_argument('--maxiter', type=int, default=400)
    args = parser.parse_args()
    run(json.loads(Path(args.source).read_text()), args.output, args.maxiter)
