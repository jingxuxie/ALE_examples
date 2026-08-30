import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import warnings
from pathlib import Path
import numpy as np
from itertools import combinations
from multiprocessing import Pool
from optimize import optimize, pack, unpack

warnings.filterwarnings('ignore')

def run_job(arguments):
    initial, support = arguments
    coefficients, stats = optimize(initial, support=support, mesh=19, gap=3.005, iterations=65, verbose=False)
    merit = stats['wc']+5*max(0., 2.996-stats['gc'])
    return merit, coefficients, stats, support

if __name__ == '__main__':
    coefficients = pack(json.loads(Path('dense_new.json').read_text()))
    candidates = [2, 3, 4, 10, 11, 14, 15, 19, 20, 21, 22]
    jobs = [(coefficients, [0, 1, 12, 13]+list(selected)) for selected in combinations(candidates, 5)]
    rng = np.random.default_rng(1298)
    rng.shuffle(jobs)
    results = []
    with Pool(3) as pool:
        for result in pool.imap_unordered(run_job, jobs):
            results.append(result)
            results.sort(key=lambda item:item[0])
            if results[0] is result:
                Path('enum_best.json').write_text(json.dumps(unpack(result[1]), indent=2)+'\n')
                print('BEST', len(results), result[0], result[2], result[3], flush=True)
            if len(results)%25 == 0:
                print('COUNT', len(results), flush=True)
    for index, result in enumerate(results[:30]):
        Path(f'enum_{index}.json').write_text(json.dumps(unpack(result[1]), indent=2)+'\n')
    print([(item[0], item[3]) for item in results[:30]], flush=True)
