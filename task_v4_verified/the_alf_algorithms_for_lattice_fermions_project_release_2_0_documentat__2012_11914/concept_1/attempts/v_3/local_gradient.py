import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
import json
import time
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective, optimize
from search import OUT, evaluate, save
from refine import neighborhood

random = np.random.default_rng(int(sys.argv[1]))
started = time.time()

def main():
    best = 10
    archive = []
    for restart in range(20000):
        if (OUT / 'witness.json').exists() or (OUT / 'STOP_LOCAL').exists():
            return
        if restart % 5 == 0 or not archive:
            fields = np.array(json.loads((OUT / 'structured_best.json').read_text())['fields'], dtype=float)
        else:
            fields = archive[int(random.integers(min(16, len(archive))))][1].copy()
        if restart:
            if random.random() < .5:
                for change in range(int(random.integers(1, 16))):
                    site = int(random.integers(16))
                    fields[:, site] = np.roll(fields[:, site], int(random.choice([-3,-2,-1,1,2,3])))
            else:
                fields *= random.choice([-1,1], size=fields.shape, p=[.15,.85])
        result = optimize(fields, .75, 600)
        fields = result.x.reshape(16,16)
        rounded = np.where(fields > 0, 1, -1).astype(np.int8)
        score = evaluate(rounded)[0]
        if score < best + .002:
            for iteration in range(100):
                neighbors = neighborhood(rounded)
                values = evaluate(neighbors)
                selected = np.argmin(values)
                if values[selected] >= score - 1e-10:
                    break
                rounded = neighbors[selected].copy()
                score = values[selected]
                if score < -1e-5:
                    break
        if score < best:
            best = score
            save(rounded, 'local_best_' + sys.argv[1] + '.json')
            print(f'{time.time()-started:.2f}s restart={restart} best={score:.12g} continuous={result.fun:.12g}', flush=True)
        if score < -1e-5:
            save(rounded)
            print('FOUND', flush=True)
            return
        if all(abs(score - previous[0]) > 1e-7 for previous in archive):
            archive.append((score, rounded.astype(float)))
            archive.sort(key=lambda entry: entry[0])
            archive = archive[:64]
        if restart % 20 == 0:
            print(f'{time.time()-started:.2f}s restart={restart} score={score:.12g} archive={len(archive)}', flush=True)

if __name__ == '__main__':
    main()
