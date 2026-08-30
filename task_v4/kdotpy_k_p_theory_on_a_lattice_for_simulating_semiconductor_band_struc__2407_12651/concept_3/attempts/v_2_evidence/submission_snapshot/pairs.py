import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import warnings
from pathlib import Path
from itertools import combinations
from multiprocessing import Pool
import numpy as np
from optimize import Grid, optimize, certificate_margins, pack, unpack

warnings.filterwarnings('ignore')

def run_job(arguments):
    initial, support = arguments
    coefficients, stats = optimize(initial, support=support, mesh=25, gap=3.0001, iterations=70, verbose=False, certified=True)
    grid = Grid(41)
    energies = grid.evaluate(coefficients, False)
    stats = grid.stats(coefficients, energies)
    margins = certificate_margins(coefficients, stats['direct'], np.min(energies[:, :, 2]-energies[:, :, 1]))
    stats['wc'] += margins[0]-.006
    stats['gc'] += .009-margins[1]
    merit = stats['wc']+5*max(0., 3.0001-stats['gc'])
    return merit, coefficients, stats, support

if __name__ == '__main__':
    initial = pack(json.loads(Path('precise8.json').read_text()))
    fixed = [0, 1, 4, 12, 13, 14, 15]
    candidates = np.setdiff1d(np.arange(1, 30), fixed).tolist()
    jobs = [(initial, fixed+list(selected)) for selected in combinations(candidates, 2)]
    rng = np.random.default_rng(421)
    rng.shuffle(jobs)
    results = []
    with Pool(3) as pool:
        for result in pool.imap_unordered(run_job, jobs):
            results.append(result)
            results.sort(key=lambda item:item[0])
            if results[0] is result:
                Path('pair_best.json').write_text(json.dumps(unpack(result[1]), indent=2)+'\n')
                print('BEST', len(results), result[0], result[2], result[3], flush=True)
            if len(results)%20 == 0:
                print('COUNT', len(results), flush=True)
    for index, result in enumerate(results[:20]):
        Path(f'pair_{index}.json').write_text(json.dumps(unpack(result[1]), indent=2)+'\n')
    print([(item[0], item[3]) for item in results[:20]], flush=True)
