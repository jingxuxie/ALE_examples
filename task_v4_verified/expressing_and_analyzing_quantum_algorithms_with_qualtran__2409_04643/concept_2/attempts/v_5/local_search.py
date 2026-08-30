import argparse
import json
import multiprocessing
import time
from pathlib import Path

import numpy as np

from batch_search import batch_assess
from search import assess, save, evaluate


def mutate(rng, base, count, style):
    polynomials = np.tile(base, (count, 1))
    if style == 0:
        bits = polynomials.view(np.int64)
        bits += rng.integers(-8, 9, bits.shape, dtype=np.int64)
    elif style == 1:
        bits = polynomials.view(np.int64)
        columns = rng.integers(0, 26, count)
        bits[np.arange(count), columns] += rng.integers(-1024, 1025, count, dtype=np.int64)
    elif style == 2:
        noise = rng.normal(size=polynomials.shape) + 1j * rng.normal(size=polynomials.shape)
        polynomials += noise * abs(base) * 10 ** rng.uniform(-15, -11, (count, 1))
    elif style == 3:
        polynomials *= np.exp(1j * rng.uniform(-np.pi, np.pi, (count, 1)))
    elif style == 4:
        phase = rng.uniform(-0.03, 0.03, (count, 1)) * np.arange(13)
        phase += rng.uniform(-np.pi, np.pi, (count, 1))
        polynomials *= np.exp(1j * phase)
    elif style == 5:
        energy = np.sum(abs(base) ** 2)
        scale = np.sqrt(rng.uniform(0.080000001, 0.09, (count, 1)) / energy)
        polynomials *= scale
    else:
        phase = rng.normal(0, 0.015, polynomials.shape)
        phase += rng.uniform(-np.pi, np.pi, (count, 1))
        polynomials *= np.exp(1j * phase)
    energies = np.sum(abs(polynomials) ** 2, axis=1)
    rms = np.sqrt(energies / 13)
    valid = ((energies >= 0.08) & (energies <= 0.30)
             & (np.min(abs(polynomials), axis=1) >= 0.25 * rms)
             & (abs(np.sum(polynomials ** 2, axis=1)) <= 0.8 * energies))
    return polynomials[valid]


def work(task):
    seed, base, count, style, cutoff = task
    rng = np.random.default_rng(seed)
    polynomials = mutate(rng, base, count, style)
    total = len(polynomials)
    score = np.full(total, np.inf)
    margins = np.full(total, np.inf)
    for modes, gauge in [(8192, 0), (8192, 1), (16384, 0), (16384, 1), (4096, 0), (4096, 1)]:
        if not len(polynomials):
            break
        errors, current_margins = batch_assess(polynomials, modes, gauge)
        score = np.minimum(score, errors)
        margins = np.minimum(margins, current_margins)
        keep = (score > cutoff) & (margins >= 1e-8)
        polynomials = polynomials[keep]
        score = score[keep]
        margins = margins[keep]
    selected = np.argsort(score)[-4:][::-1]
    return total, style, [(float(score[index]), polynomials[index]) for index in selected]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--seed', type=int, default=19019)
    parser.add_argument('--style', type=int, default=-1)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    base = np.array([complex(*value) for value in json.loads(Path('counterexample.json').read_text())['P']])
    best = min(assess(base, modes, gauge)[0] for modes in (4096, 8192, 16384) for gauge in (0, 1))
    archive = [(best, base.copy())]
    started = time.monotonic()
    total = 0
    iteration = 0
    with multiprocessing.Pool(args.workers) as pool:
        while time.monotonic() - started < args.seconds:
            tasks = []
            for offset in range(args.workers * 4):
                center = archive[0][1] if rng.random() < 0.75 else archive[rng.integers(len(archive))][1]
                style = (iteration + offset) % 7 if args.style < 0 else args.style
                tasks.append((int(rng.integers(2**31)), center, args.batch_size, style, best * 0.85))
            for valid, style, candidates in pool.imap_unordered(work, tasks):
                total += valid
                for approximate, polynomial in candidates:
                    results = [assess(polynomial, modes, gauge) for modes in (4096, 8192, 16384) for gauge in (0, 1)]
                    score = min(record[0] for record in results)
                    if min(record[1] for record in results) < 1e-8:
                        continue
                    if score > best * 0.9:
                        archive.append((score, polynomial.copy()))
                        archive.sort(key=lambda record: record[0], reverse=True)
                        archive = archive[:20]
                    if score <= best:
                        continue
                    best = score
                    residual = save(polynomial, 'counterexample.json')
                    print(json.dumps({'count': total, 'style': style, 'best': best, 'approximate': approximate, 'errors': [record[0] for record in results], 'margin': min(record[1] for record in results), 'certificate': residual, 'elapsed': time.monotonic() - started}), flush=True)
                    if best >= 0.05 and residual <= 1e-12:
                        print(json.dumps(evaluate(Path.cwd()), indent=2), flush=True)
                        return
            iteration += len(tasks)
            if iteration % 80 == 0:
                print('progress', iteration, total, best, time.monotonic() - started, flush=True)
    print('done', total, best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
