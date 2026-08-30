import argparse
import heapq
import time

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import splu

from optimize import Inverse, OUTPUT, binary, save_best, response, discrepancies
from discrete import feasible


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=20000)
    arguments = parser.parse_args()
    inverse = Inverse(stride=1, conditions=[0])
    base = inverse.bases[0]
    rows, columns = np.nonzero(base)
    diagonal = rows == columns
    pairing = (rows < 144) != (columns < 144)
    base_values = base[rows, columns]
    right = np.eye(288, dtype=complex)[:, inverse.probes]
    target = inverse.target[0, :, 30]
    scales = inverse.scales[0, :, 0]
    best_error = float('inf')
    pool = []
    seen = set()
    start = time.time()
    for seed in range(arguments.start, arguments.end):
        if (OUTPUT / 'STOP').exists():
            break
        random = np.random.default_rng(seed)
        chosen = np.zeros(64)
        chosen[random.choice(64, 24, replace=False)] = 1
        while not feasible(inverse, chosen):
            chosen[:] = 0
            chosen[random.choice(64, 24, replace=False)] = 1
        ordered = binary(np.random.default_rng(seed).random(64))
        legacy = np.zeros(64)
        legacy[np.random.RandomState(seed).choice(64, 24, replace=False)] = 1
        for method, pattern in enumerate([chosen, ordered, legacy]):
            key = np.packbits(pattern.astype(np.uint8)).tobytes()
            if key in seen:
                continue
            seen.add(key)
            normal = np.zeros(144)
            normal[inverse.indices] = pattern
            amplitude = 1 - normal
            values = base_values.copy()
            values[pairing] *= amplitude[rows[pairing] % 144] * amplitude[columns[pairing] % 144]
            values[diagonal] += 6 * np.concatenate([normal, -normal])
            values = -values
            values[diagonal] += 0.02j
            matrix = csc_matrix((values, (rows, columns)), shape=(288, 288))
            solution = splu(matrix).solve(right)
            observed = -np.imag(solution[inverse.probes, np.arange(8)]) / np.pi
            error = np.sqrt(np.mean(((observed - target) / scales) ** 2))
            item = (-error, seed, method, pattern)
            if len(pool) < 100:
                heapq.heappush(pool, item)
            elif error < -pool[0][0]:
                heapq.heapreplace(pool, item)
            if error < best_error:
                best_error = error
                print('SCREEN', seed, method, error, 'time', round(time.time() - start, 1), flush=True)
                save_best(inverse, pattern)
            if error < 1e-8 and feasible(inverse, pattern):
                report = discrepancies(inverse.config, response(inverse.config, pattern), inverse.full_target)
                print('MATCH', report, flush=True)
                if report['core_score'] > 0.96 and report['worst_family_score'] > 0.94:
                    save_best(inverse, pattern)
                    (OUTPUT / 'STOP').touch()
                    return
        if seed % 1000 == 0:
            print('PROGRESS', seed, 'time', round(time.time() - start, 1), 'best', best_error, flush=True)
    for index, (negative_error, seed, method, pattern) in enumerate(sorted(pool, key=lambda item: -item[0])):
        if feasible(inverse, pattern):
            error = inverse.error(pattern)
            np.savez(OUTPUT / f'screen_{arguments.start}_{index}.npz', pattern=pattern, error=error, zero_error=-negative_error)
            save_best(inverse, pattern)
    print('FINISHED', time.time() - start, flush=True)


if __name__ == '__main__':
    main()
