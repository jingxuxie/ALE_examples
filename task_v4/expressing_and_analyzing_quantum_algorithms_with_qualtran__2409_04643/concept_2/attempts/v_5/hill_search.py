import argparse
import json
import multiprocessing
import time
from pathlib import Path

import numpy as np

from batch_search import batch_complement
from search import assess, fast_error, qsp_phase_factors, phase_guard_margin, save, evaluate


def exact_candidates(task):
    polynomials, cutoff = task
    scores = np.full(len(polynomials), np.inf)
    records = np.empty((len(polynomials), 0))
    minimum_margins = np.full(len(polynomials), np.inf)
    for modes, gauge in [(8192, 0), (8192, 1), (16384, 0), (16384, 1), (4096, 0), (4096, 1)]:
        if not len(polynomials):
            return []
        transformed = polynomials.copy()
        if gauge:
            phase = np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(13)))
            for row in transformed:
                row *= phase
        complements = batch_complement(transformed, modes)
        current = np.zeros(len(polynomials))
        for index, (polynomial, complement) in enumerate(zip(transformed, complements)):
            angles = qsp_phase_factors(polynomial, complement)
            current[index] = fast_error(polynomial, complement, angles)
            minimum_margins[index] = min(minimum_margins[index], phase_guard_margin(polynomial, complement, angles[0], angles[1]))
        scores = np.minimum(scores, current)
        records = np.concatenate((records, current[:, None]), axis=1)
        keep = (scores > cutoff) & (minimum_margins >= 1e-8)
        polynomials = polynomials[keep]
        scores = scores[keep]
        records = records[keep]
        minimum_margins = minimum_margins[keep]
    selected = np.argsort(scores)[-8:][::-1]
    return [(float(scores[index]), polynomials[index], records[index], float(minimum_margins[index])) for index in selected]


def neighbors(center, radius, rng):
    polynomials = np.tile(center, (116, 1))
    bits = polynomials.view(np.int64)
    for component in range(26):
        bits[2 * component, component] += radius
        bits[2 * component + 1, component] -= radius
    for index in range(52, len(polynomials)):
        count = rng.integers(2, 6)
        columns = rng.choice(26, count, replace=False)
        bits[index, columns] += rng.choice([-radius, radius], count)
    energies = np.sum(abs(polynomials) ** 2, axis=1)
    rms = np.sqrt(energies / 13)
    valid = ((energies >= 0.08) & (energies <= 0.30)
             & (np.min(abs(polynomials), axis=1) >= 0.25 * rms)
             & (abs(np.sum(polynomials ** 2, axis=1)) <= 0.8 * energies))
    return polynomials[valid]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--seed', type=int, default=908761)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    center = np.array([complex(*value) for value in json.loads(Path('counterexample.json').read_text())['P']])
    center_score = min(assess(center, modes, gauge)[0] for modes in (4096, 8192, 16384) for gauge in (0, 1))
    best = center_score
    best_polynomial = center.copy()
    radius_index = 0
    radii = [1, 2, 4, 8, 16, 32, 64, 128, 256, 1024]
    started = time.monotonic()
    iteration = 0
    total = 0
    archive = [(best, center.copy())]
    with multiprocessing.Pool(args.workers) as pool:
        while time.monotonic() - started < args.seconds:
            candidates = neighbors(center, radii[radius_index], rng)
            total += len(candidates)
            cutoff = center_score + 1e-10
            tasks = [(chunk, cutoff) for chunk in np.array_split(candidates, args.workers) if len(chunk)]
            results = [record for group in pool.map(exact_candidates, tasks) for record in group]
            results.sort(key=lambda record: record[0], reverse=True)
            if results:
                center_score, center, errors, margin = results[0]
                for score, polynomial, _, _ in results[:4]:
                    if score >= best * 0.93:
                        archive.append((score, polynomial.copy()))
                archive.sort(key=lambda record: record[0], reverse=True)
                archive = archive[:40]
                if center_score > best:
                    checked = [assess(center, modes, gauge) for modes in (4096, 8192, 16384) for gauge in (0, 1)]
                    center_score = min(record[0] for record in checked)
                    if center_score > best:
                        best = center_score
                        best_polynomial = center.copy()
                        residual = save(center, 'counterexample.json')
                        print(json.dumps({'iteration': iteration, 'count': total, 'radius': radii[radius_index], 'best': best, 'errors': [record[0] for record in checked], 'margin': min(record[1] for record in checked), 'certificate': residual, 'elapsed': time.monotonic() - started}), flush=True)
                        if best >= 0.05 and residual <= 1e-12:
                            print(json.dumps(evaluate(Path.cwd()), indent=2), flush=True)
                            return
                radius_index = 0
            else:
                radius_index += 1
                if radius_index >= len(radii):
                    center = (best_polynomial if rng.random() < 0.5 else archive[rng.integers(len(archive))][1]).copy()
                    bits = center.view(np.int64)
                    columns = rng.choice(26, rng.integers(1, 6), replace=False)
                    bits[columns] += rng.integers(-4096, 4097, len(columns), dtype=np.int64)
                    center_score = min(assess(center, modes, gauge)[0] for modes in (4096, 8192, 16384) for gauge in (0, 1))
                    radius_index = 0
            iteration += 1
            if iteration % 20 == 0:
                print('progress', iteration, total, best, center_score, radii[radius_index], time.monotonic() - started, flush=True)
    print('done', iteration, total, best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
