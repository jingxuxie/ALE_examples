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
    initial, support, removed, added, mesh, gap = arguments
    coefficients, stats = optimize(initial, support=support, mesh=mesh, gap=gap, iterations=65, verbose=False)
    merit = stats['wc'] + 5*max(0., gap-.009-stats['gc'])
    return merit, coefficients, stats, removed, added

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial', default='refined8.json')
    parser.add_argument('--prefix', default='swap')
    parser.add_argument('--mesh', type=int, default=19)
    parser.add_argument('--gap', type=float, default=3.0055)
    parser.add_argument('--rounds', type=int, default=3)
    args = parser.parse_args()
    coefficients = pack(json.loads(Path(args.initial).read_text()))
    with Pool(3) as pool:
        for step in range(args.rounds):
            support = np.flatnonzero(coefficients).tolist()
            inactive = np.setdiff1d(np.arange(1, 30), support)
            jobs = [(coefficients, [index for index in support if index != removed]+[int(added)], removed, int(added), args.mesh, args.gap) for removed in support if removed != 0 for added in inactive]
            jobs += [(coefficients, support, 0, 0, args.mesh, args.gap)]
            results = []
            for result in pool.imap_unordered(run_job, jobs):
                results.append(result)
                if len(results)%25 == 0:
                    best = min(results, key=lambda item:item[0])
                    print(step, len(results), 'best', best[0], best[3:], flush=True)
            results.sort(key=lambda item:item[0])
            for index, result in enumerate(results[:15]):
                Path(f'{args.prefix}_{step}_{index}.json').write_text(json.dumps(unpack(result[1]), indent=2)+'\n')
            merit, coefficients, stats, removed, added = results[0]
            print('ROUND', step, 'stats', stats, 'removed', removed, 'added', added, flush=True)
            print('RUNNERS', [(round(item[0], 7), item[3:]) for item in results[1:15]], flush=True)
            if removed == 0:
                break
