import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
from pathlib import Path
import numpy as np
from scipy.linalg import expm

OUT = Path(__file__).resolve().parent
RNG = np.random.default_rng(637824)
SIZE = 16
SLICES = 16
BETA = 0.75
COUPLING = np.arccosh(np.exp(BETA / SLICES * 2))
KINETIC = np.zeros((SIZE, SIZE))
for horizontal in range(4):
    for vertical in range(4):
        source = 4 * horizontal + vertical
        for delta_horizontal, delta_vertical in [(1, 0), (0, 1)]:
            target = 4 * ((horizontal + delta_horizontal) % 4) + (vertical + delta_vertical) % 4
            KINETIC[source, target] = KINETIC[target, source] = -1
PROPAGATOR = expm(-BETA / SLICES * KINETIC)

def products(fields):
    fields = np.asarray(fields).reshape(-1, SLICES, SIZE)
    product = np.broadcast_to(np.eye(SIZE), (len(fields), SIZE, SIZE)).copy()
    for time_index in range(SLICES):
        product = PROPAGATOR @ (np.exp(COUPLING * fields[:, time_index, :, None]) * product)
    return product

def evaluate(fields, mode='ratio'):
    product = products(fields)
    eigenvalues = np.linalg.eigvals(product)
    radii = np.abs(eigenvalues)
    if mode == 'phase':
        return -np.max(np.abs(np.angle(eigenvalues)), axis=1)
    determinants = []
    lognorm = np.zeros(len(product))
    sign = np.ones(len(product))
    for fugacity in [np.exp(BETA), np.exp(-BETA)]:
        sign_part, log_part = np.linalg.slogdet(np.eye(SIZE) + fugacity * product)
        sign *= sign_part
        lognorm += log_part - np.sum(np.log1p(fugacity * radii), axis=1)
    return sign * np.exp(lognorm)

def save(fields, filename='witness.json'):
    (OUT / filename).write_text(json.dumps({'fields': fields.astype(int).tolist()}) + '\n')

def main():
    started = time.time()
    best = 10
    for restart in range(10000):
        candidates = RNG.choice([-1, 1], size=(256, SLICES, SIZE)).astype(np.int8)
        values = evaluate(candidates)
        selected = np.argmin(values)
        fields = candidates[selected].copy()
        current = values[selected]
        for iteration in range(300):
            neighbors = np.repeat(fields[None], 256, axis=0)
            neighbors.reshape(256, 256)[np.arange(256), np.arange(256)] *= -1
            values = evaluate(neighbors)
            selected = np.argmin(values)
            if values[selected] >= current - 1e-10:
                break
            fields = neighbors[selected].copy()
            current = values[selected]
            if current < best:
                best = current
                save(fields, 'best.json')
                print(f'{time.time()-started:.2f}s restart={restart} iteration={iteration} best={best:.12g}', flush=True)
            if current < -1e-5:
                save(fields)
                print('FOUND', flush=True)
                return
        print(f'local optimum restart={restart} value={current:.12g}', flush=True)

if __name__ == '__main__':
    main()
