import argparse
import heapq
import json
import multiprocessing
import time
from pathlib import Path

import numpy as np

from hill_search import exact_candidates, neighbors
from search import assess, save, evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=180)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    rng = np.random.default_rng(7543901)
    polynomial = np.array([complex(*value) for value in json.loads(Path('counterexample.json').read_text())['P']])
    best = min(assess(polynomial, modes, gauge)[0] for modes in (4096, 8192, 16384) for gauge in (0, 1))
    best_polynomial = polynomial.copy()
    queue = [(-best, 0, polynomial)]
    known = {polynomial.tobytes()}
    sequence = 0
    iteration = 0
    radius = 1
    started = time.monotonic()
    with multiprocessing.Pool(args.workers) as pool:
        while time.monotonic() - started < args.seconds:
            if not queue:
                radius = min(1024, 2 * radius)
                queue = [(-best, sequence + 1, best_polynomial.copy())]
                sequence += 1
            _, _, center = heapq.heappop(queue)
            generated = neighbors(center, radius, rng)
            candidates = []
            for candidate in generated:
                key = candidate.tobytes()
                if key not in known:
                    known.add(key)
                    candidates.append(candidate)
            if not candidates:
                continue
            tasks = [(chunk, best * 0.7) for chunk in np.array_split(candidates, args.workers) if len(chunk)]
            records = [record for chunk in pool.map(exact_candidates, tasks) for record in chunk]
            for score, candidate, errors, margin in records:
                priority = score + 0.25 * (np.mean(np.minimum(errors, 2 * best)) - score)
                sequence += 1
                heapq.heappush(queue, (-priority, sequence, candidate))
                if score <= best:
                    continue
                checked = [assess(candidate, modes, gauge) for modes in (4096, 8192, 16384) for gauge in (0, 1)]
                score = min(record[0] for record in checked)
                if score <= best:
                    continue
                best = score
                best_polynomial = candidate.copy()
                residual = save(candidate, 'counterexample.json')
                print(json.dumps({'iteration': iteration, 'known': len(known), 'best': best, 'errors': [record[0] for record in checked], 'margin': min(record[1] for record in checked), 'certificate': residual, 'elapsed': time.monotonic() - started}), flush=True)
                if best >= 0.05 and residual <= 1e-12:
                    print(json.dumps(evaluate(Path.cwd()), indent=2), flush=True)
                    return
            if len(queue) > 10000:
                queue = heapq.nsmallest(5000, queue)
                heapq.heapify(queue)
            iteration += 1
            if iteration % 20 == 0:
                print('progress', iteration, len(known), len(queue), best, time.monotonic() - started, flush=True)
    print('done', iteration, len(known), best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
