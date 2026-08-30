import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import numpy as np
from scipy.linalg import eig
from scipy.optimize import minimize
from search import OUT, SIZE, SLICES, COUPLING, PROPAGATOR, BETA, evaluate, save

random = np.random.default_rng(835791)
started = time.time()
best = 10.0

def objective(flat):
    fields = flat.reshape(SLICES, SIZE)
    matrices = PROPAGATOR[None] * np.exp(COUPLING * fields[:, None, :])
    product = np.eye(SIZE)
    for matrix in matrices:
        product = matrix @ product
    eigenvalues, left, right = eig(product, left=True, right=True)
    radii = np.abs(eigenvalues)
    phases = np.angle(eigenvalues)
    fugacity = np.exp(BETA)
    scaled = fugacity * radii
    distances = np.abs(1 + fugacity * eigenvalues)**2 / (1 + scaled)**2
    distances[phases < -1e-8] += 10
    selected = np.argmin(distances)
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
    scale = scaled[selected]
    phase = phases[selected]
    radial = -2 * scale * (1 - scale) * (1 - np.cos(phase)) / (1 + scale)**3
    angular = -2 * scale * np.sin(phase) / (1 + scale)**2
    gradient = radial * derivative.real + angular * derivative.imag
    return distances[selected], gradient.ravel()

def polish(fields):
    current = evaluate(fields)[0]
    for iteration in range(150):
        neighbors = np.repeat(fields[None], 256, axis=0)
        neighbors.reshape(256, 256)[np.arange(256), np.arange(256)] *= -1
        values = evaluate(neighbors)
        selected = np.argmin(values)
        if values[selected] >= current - 1e-10:
            break
        fields = neighbors[selected].copy()
        current = values[selected]
        if current < -1e-5:
            save(fields)
            return fields, current
    return fields, current

def main():
    global best
    for restart in range(10000):
        if (OUT / 'witness.json').exists():
            return
        if restart % 3 == 0 and (OUT / 'phase_best.json').exists():
            initial = np.array(json.loads((OUT / 'phase_best.json').read_text())['fields'], dtype=float)
            initial *= random.choice([-1, 1], size=initial.shape, p=[0.08, 0.92])
        elif restart % 3 == 1:
            initial = np.array(json.loads((OUT / 'best.json').read_text())['fields'], dtype=float)
            initial *= random.choice([-1, 1], size=initial.shape, p=[0.08, 0.92])
        else:
            candidates = random.choice([-1, 1], size=(32, SLICES, SIZE))
            values = [objective(candidate.ravel())[0] for candidate in candidates]
            initial = candidates[np.argmin(values)].astype(float)
        result = minimize(objective, initial.ravel(), jac=True, bounds=[(-1, 1)] * 256,
                          method='L-BFGS-B', options={'maxiter': 400, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 30})
        fields = np.where(result.x.reshape(16, 16) > 0, 1, -1).astype(np.int8)
        distance = objective(fields.ravel())[0]
        if distance < best:
            best = distance
            save(fields, 'phase_best.json')
        print(f'{time.time()-started:.2f}s restart={restart} continuous={result.fun:.12g} rounded={distance:.12g} best={best:.12g} iterations={result.nit}', flush=True)
        if distance < 0.04:
            fields, ratio = polish(fields)
            print(f'polished ratio={ratio:.12g}', flush=True)
            if ratio < -1e-5:
                print('FOUND', flush=True)
                return

if __name__ == '__main__':
    main()
