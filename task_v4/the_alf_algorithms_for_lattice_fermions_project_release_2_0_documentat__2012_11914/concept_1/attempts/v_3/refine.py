import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import numpy as np
from search import OUT, evaluate, save

random = np.random.default_rng(171218)
started = time.time()

def neighborhood(fields):
    neighbors = np.repeat(fields[None], 256 * 3 + 64, axis=0)
    flattened = neighbors.reshape(len(neighbors), 256)
    indices = np.arange(256)
    for length in range(1, 4):
        rows = indices + (length - 1) * 256
        for offset in range(length):
            columns = ((indices // 16 + offset) % 16) * 16 + indices % 16
            flattened[rows, columns] *= -1
    for site in range(16):
        for offset_index, offset in enumerate([-2, -1, 1, 2]):
            neighbors[768 + 4 * site + offset_index, :, site] = np.roll(fields[:, site], offset)
    return neighbors

def main():
    best = 10
    pool = []
    for restart in range(10000):
        if (OUT / 'witness.json').exists():
            return
        for filename in ['best.json', 'phase_best.json', 'refine_best.json']:
            if (OUT / filename).exists():
                fields = np.array(json.loads((OUT / filename).read_text())['fields'], dtype=np.int8)
                pool.append((evaluate(fields)[0], fields))
        pool.sort(key=lambda entry: entry[0])
        pool = pool[:16]
        parent = int(random.integers(0, min(8, len(pool))))
        fields = pool[parent][1].copy()
        if restart:
            for change in range(int(random.integers(1, 12))):
                site = int(random.integers(16))
                if random.random() < 0.6:
                    fields[:, site] = np.roll(fields[:, site], int(random.choice([-3, -2, -1, 1, 2, 3])))
                else:
                    start = int(random.integers(16))
                    length = int(random.integers(1, 6))
                    fields[(start + np.arange(length)) % 16, site] *= -1
        current = evaluate(fields)[0]
        for iteration in range(300):
            neighbors = neighborhood(fields)
            values = evaluate(neighbors)
            selected = np.argmin(values)
            if values[selected] >= current - 1e-10:
                break
            fields = neighbors[selected].copy()
            current = values[selected]
            if current < best:
                best = current
                save(fields, 'refine_best.json')
                print(f'{time.time()-started:.2f}s restart={restart} iteration={iteration} best={best:.12g}', flush=True)
            if current < -1e-5:
                save(fields)
                print('FOUND', flush=True)
                return
        if all(np.count_nonzero(fields != previous[1]) > 5 for previous in pool):
            pool.append((current, fields))
        print(f'local optimum restart={restart} value={current:.12g}', flush=True)

if __name__ == '__main__':
    main()
