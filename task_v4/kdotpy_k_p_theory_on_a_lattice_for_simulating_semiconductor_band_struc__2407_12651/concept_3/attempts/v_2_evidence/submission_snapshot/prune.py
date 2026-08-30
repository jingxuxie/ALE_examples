import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import warnings
import argparse
from pathlib import Path
import numpy as np
from multiprocessing import Pool
from optimize import optimize, pack, unpack

warnings.filterwarnings('ignore')

def run_job(arguments):
    initial, support, removed = arguments
    coefficients, stats = optimize(initial, support=support, mesh=19, gap=3.005, iterations=60, verbose=False)
    merit = stats['wc'] + 5*max(0., 2.996-stats['gc'])
    return merit, coefficients, stats, removed

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial', default='dense_new.json')
    parser.add_argument('--prefix', default='pruned_new')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    coefficients = pack(json.loads(Path(args.initial).read_text()))
    support = np.flatnonzero(np.abs(coefficients)>1e-7).tolist()
    with Pool(args.workers) as pool:
        while len(support)>9:
            jobs = [(coefficients, [index for index in support if index != removed], removed) for removed in support if removed != 0]
            results = sorted(pool.map(run_job, jobs), key=lambda result: result[0])
            merit, coefficients, stats, removed = results[0]
            support.remove(removed)
            Path(f'{args.prefix}{len(support)-1}.json').write_text(json.dumps(unpack(coefficients), indent=2)+'\n')
            print('channels', len(support)-1, 'removed', removed, 'stats', stats, 'support', support, flush=True)
            print('runners-up', [(round(item[0], 6), item[3]) for item in results[1:5]], flush=True)
