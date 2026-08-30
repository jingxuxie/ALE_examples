import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import sys
import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize
from search import OUT, KINETIC, save, evaluate

random = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 95813)
started = time.time()

class Objective:
    def __init__(self, beta, both=True, kinetic=None, coupling_scale=1.0):
        self.beta = beta
        self.fugacities = [np.exp(beta), np.exp(-beta)] if both else [np.exp(-beta)]
        kinetic = KINETIC if kinetic is None else kinetic
        self.sites = len(kinetic)
        self.coupling = np.arccosh(np.exp(beta / 8)) * coupling_scale
        self.propagator = expm(-beta / 16 * kinetic)

    def __call__(self, flat):
        fields = flat.reshape(16, self.sites)
        matrices = self.propagator[None] * np.exp(self.coupling * fields[:, None, :])
        product = np.eye(self.sites)
        prefixes = []
        for matrix in matrices:
            prefixes.append(product)
            product = matrix @ product
        eigenvalues, vectors = np.linalg.eig(product)
        inverse = np.linalg.inv(vectors)
        radii = np.abs(eigenvalues)
        ratio = 1.0
        coefficients = np.zeros(self.sites, dtype=complex)
        for fugacity in self.fugacities:
            factors = (1 + fugacity * eigenvalues) / (1 + fugacity * radii)
            ratio *= np.prod(factors).real
            coefficients += fugacity / (1 + fugacity * eigenvalues) - fugacity * radii / (eigenvalues * (1 + fugacity * radii))
        row = ((vectors * coefficients[None]) @ inverse).real
        gradient = np.empty((16, self.sites))
        for time_index in range(15, -1, -1):
            row = row @ matrices[time_index]
            gradient[time_index] = self.coupling * ratio * np.einsum('ij,ji->i', prefixes[time_index], row)
        return ratio, gradient.ravel()

def optimize(fields, beta, maxiter=500):
    return minimize(Objective(beta), fields.ravel(), jac=True, method='L-BFGS-B', bounds=[(-1, 1)] * 256,
                    options={'maxiter': maxiter, 'ftol': 2e-13, 'gtol': 1e-8, 'maxls': 30})

def main():
    best = 10
    best_threshold = 2.0
    archive = []
    for restart in range(10000):
        if (OUT / 'STOP_GRADIENT').exists() or (OUT / 'witness.json').exists():
            return
        if restart % 4 == 0 or not archive:
            filename = ['angle_best.json', 'phase_best.json', 'refine_best.json', 'best.json'][(restart // 4) % 4]
            fields = np.array(json.loads((OUT / filename).read_text())['fields'], dtype=float)
            fields *= random.choice([-1, 1], size=fields.shape, p=[0.15, 0.85])
        else:
            fields = archive[int(random.integers(min(8, len(archive))))][1].copy()
            for change in range(int(random.integers(1, 13))):
                site = int(random.integers(16))
                fields[:, site] = np.roll(fields[:, site], int(random.choice([-4, -3, -2, -1, 1, 2, 3, 4])))
            if random.random() < 0.3:
                fields *= random.choice([-1, 1], size=fields.shape, p=[0.1, 0.9])
        threshold = 2.0
        for beta in [1.5, 1.3, 1.15, 1.05, 0.95, 0.9, 0.85, 0.8, 0.775, 0.75]:
            result = optimize(fields, beta)
            fields = result.x.reshape(16, 16)
            rounded = np.where(fields > 0, 1, -1).astype(np.int8)
            ratio = Objective(beta)(rounded.ravel())[0]
            if ratio < -1e-7:
                threshold = beta
            if beta == 0.75:
                score = evaluate(rounded)[0]
                if score < best:
                    best = score
                    save(rounded, 'gradient_best_' + sys.argv[1] + '.json')
                    print(f'{time.time()-started:.2f}s restart={restart} best={best:.12g} continuous={result.fun:.12g}', flush=True)
                if score < -1e-5:
                    save(rounded)
                    print('FOUND', flush=True)
                    return
        if threshold < best_threshold:
            best_threshold = threshold
            print(f'{time.time()-started:.2f}s restart={restart} threshold={threshold} best_threshold={best_threshold}', flush=True)
        if all(np.count_nonzero(np.sign(fields) != np.sign(previous[1])) > 5 for previous in archive):
            archive.append((score, fields.copy()))
            archive.sort(key=lambda entry: entry[0])
            archive = archive[:32]
        if restart % 10 == 0:
            print(f'{time.time()-started:.2f}s restart={restart} threshold={threshold} final_beta={beta} final_ratio={ratio:.12g}', flush=True)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        fields = np.array(json.loads((OUT / 'angle_best.json').read_text())['fields'], dtype=float).ravel()
        objective = Objective(0.75)
        value, gradient = objective(fields)
        print('objective', value, evaluate(fields.reshape(16,16)))
        for index in [3, 24, 95, 173, 245]:
            varied = fields.copy()
            varied[index] += 1e-5
            print(index, gradient[index], (objective(varied)[0] - value) / 1e-5)
    else:
        main()
