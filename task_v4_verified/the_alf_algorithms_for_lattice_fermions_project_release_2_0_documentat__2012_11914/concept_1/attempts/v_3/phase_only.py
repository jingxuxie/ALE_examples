import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import numpy as np
from scipy.linalg import eig
from scipy.optimize import minimize
from search import OUT, SIZE, SLICES, COUPLING, PROPAGATOR, evaluate, save
from phase_search import polish

random = np.random.default_rng(17832)
started = time.time()

def objective(flat):
    fields = flat.reshape(SLICES, SIZE)
    matrices = PROPAGATOR[None] * np.exp(COUPLING * fields[:, None, :])
    product = np.eye(SIZE)
    for matrix in matrices:
        product = matrix @ product
    eigenvalues, left, right = eig(product, left=True, right=True)
    phases = np.angle(eigenvalues)
    selected = np.argmax(phases)
    eigenvalue = eigenvalues[selected]
    row = left[:, selected].conj()
    vector = right[:, selected]
    normalization = (row @ vector) * eigenvalue
    prefixes = []
    for matrix in matrices:
        prefixes.append(vector)
        vector = matrix @ vector
    derivative = np.empty((SLICES, SIZE), dtype=complex)
    for time_index in range(SLICES - 1, -1, -1):
        row = row @ matrices[time_index]
        derivative[time_index] = COUPLING * row * prefixes[time_index] / normalization
    return -phases[selected], -derivative.imag.ravel()

def main():
    best = 0
    archive = []
    for restart in range(20000):
        if (OUT / 'witness.json').exists():
            return
        if restart % 5 == 0 or not archive:
            candidates = random.choice([-1, 1], size=(32, SLICES, SIZE))
            values = [objective(candidate.ravel())[0] for candidate in candidates]
            initial = candidates[np.argmin(values)].astype(float)
        else:
            if restart % 5 == 1:
                initial = np.array(json.loads((OUT / 'refine_best.json').read_text())['fields'], dtype=float)
            else:
                initial = archive[int(random.integers(min(8, len(archive))))][1].copy()
            for change in range(int(random.integers(1, 10))):
                site = int(random.integers(16))
                initial[:, site] = np.roll(initial[:, site], int(random.choice([-4, -3, -2, -1, 1, 2, 3, 4])))
            if random.random() < 0.25:
                initial *= random.choice([-1, 1], size=initial.shape, p=[0.15, 0.85])
        result = minimize(objective, initial.ravel(), jac=True, bounds=[(-1, 1)] * 256,
                          method='L-BFGS-B', options={'maxiter': 350, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 30})
        fields = np.where(result.x.reshape(16, 16) > 0, 1, -1).astype(np.int8)
        score = objective(fields.ravel())[0]
        if score < best:
            best = score
            save(fields, 'angle_best.json')
            print(f'{time.time()-started:.2f}s restart={restart} newbest={best:.12g}', flush=True)
        if all(np.count_nonzero(fields != previous[1]) > 5 for previous in archive):
            archive.append((score, fields.astype(float)))
            archive.sort(key=lambda entry: entry[0])
            archive = archive[:32]
        if score < -2.7:
            fields, ratio = polish(fields)
            print(f'polished ratio={ratio:.12g}', flush=True)
            if ratio < -1e-5:
                print('FOUND', flush=True)
                return
        if restart % 20 == 0:
            print(f'{time.time()-started:.2f}s restart={restart} score={score:.12g} continuous={result.fun:.12g}', flush=True)

if __name__ == '__main__':
    main()
