import argparse
import json
import multiprocessing as multiprocessing
import time
from pathlib import Path

import numpy as np

from search import assess, save, evaluate


def batch_complement(polynomials, modes):
    padded = np.pad(polynomials, ((0, 0), (0, modes - 1)))
    logarithm = np.log(1 - np.abs(np.fft.ifft(padded, norm='forward')) ** 2)
    fourier = np.fft.fft(logarithm, norm='forward')
    fourier[:, 0] *= 0.5
    fourier[:, modes // 2 + 1:] = 0
    completed = np.fft.fft(np.exp(np.fft.ifft(fourier, norm='forward')), norm='forward')
    return completed[:, :polynomials.shape[1]]


def batch_assess(polynomials, modes, gauge):
    if gauge:
        phase_gauge = np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(polynomials.shape[1])))
        polynomials = np.array([polynomial.copy() for polynomial in polynomials])
        for polynomial in polynomials:
            polynomial *= phase_gauge
    complements = batch_complement(polynomials, modes)
    state = np.stack((polynomials, complements), axis=1)
    theta = np.zeros(polynomials.shape)
    phi = np.zeros(polynomials.shape)
    margins = np.full(len(polynomials), np.inf)
    for degree in reversed(range(polynomials.shape[1])):
        leading, other = state[:, 0, degree], state[:, 1, degree]
        product = leading * np.conj(other)
        margins = np.minimum(margins, np.minimum(abs(other), abs(product)))
        theta[:, degree] = np.arctan2(abs(other), abs(leading))
        phi[:, degree] = np.where(np.isclose(abs(other), 0, atol=1e-10) | np.isclose(product, 0, atol=1e-10), 0, np.angle(product))
        if degree == 0:
            lambd = np.where(np.isclose(other, 0, atol=1e-10), 0, np.angle(other))
        else:
            cosine = np.cos(theta[:, degree])
            sine = np.sin(theta[:, degree])
            phase = np.exp(1j * phi[:, degree])
            rotation = np.empty((len(polynomials), 2, 2), dtype=complex)
            rotation[:, 0, 0] = phase * cosine
            rotation[:, 0, 1] = phase * sine
            rotation[:, 1, 0] = sine
            rotation[:, 1, 1] = -cosine
            state = np.matmul(rotation.conj().transpose(0, 2, 1), state)
            state = np.stack((state[:, 0, 1:degree + 1], state[:, 1, :degree]), axis=1)
    top = (np.exp(1j * (phi[:, 0] + lambd)) * np.cos(theta[:, 0]))[:, None]
    bottom = (np.exp(1j * lambd) * np.sin(theta[:, 0]))[:, None]
    for index in range(1, polynomials.shape[1]):
        upper = np.pad(top, ((0, 0), (1, 0)))
        lower = np.pad(bottom, ((0, 0), (0, 1)))
        cosine = np.cos(theta[:, index])[:, None]
        sine = np.sin(theta[:, index])[:, None]
        top = np.exp(1j * phi[:, index])[:, None] * (cosine * upper + sine * lower)
        bottom = sine * upper - cosine * lower
    target = np.concatenate((polynomials, complements), axis=1)
    actual = np.concatenate((top, bottom), axis=1)
    overlap = np.sum(np.conj(target) * actual, axis=1)
    phase = overlap / abs(overlap)
    errors = np.linalg.norm(actual - phase[:, None] * target, axis=1)
    return errors, margins


def generate(rng, count, style):
    if style == 10:
        precision = 2.0 ** rng.integers(3, 12, count)
        leading_ratio = np.round(rng.uniform(13.60, 13.682, count) * precision) / precision
        next_ratio = np.round(rng.uniform(3.05, 3.5, count) * precision) / precision
        magnitudes = np.ones((count, 13))
        magnitudes[:, 11] = leading_ratio
        magnitudes[:, 10] = next_ratio
        shape_energy = np.sum(magnitudes ** 2, axis=1)
        ratios = 2.0 ** rng.integers(-6, 7, count)
        units = 1 + 1j * ratios * rng.choice([-1, 1], count)
        axes = rng.random(count) < 0.3
        units[axes] = 1
        units *= (1j) ** rng.integers(0, 4, count)
        energy = 0.08 + 10 ** rng.uniform(-8, -2, count)
        amplitude = np.sqrt(energy / (shape_energy * abs(units) ** 2))
        exponent = np.ceil(-np.log2(amplitude)) + rng.integers(3, 16, count)
        lattice = 2.0 ** (-exponent)
        amplitude = np.ceil(amplitude / lattice) * lattice
        directions = 1j * rng.choice([-1, 1], (count, 13))
        directions[:, 11] = 1
        directions[:, 10] = 1j
        directions[:, 12] = 1j
        polynomial = amplitude[:, None] * magnitudes * directions * units[:, None]
        energy = np.sum(abs(polynomial) ** 2, axis=1)
        rms = np.sqrt(energy / 13)
        valid = ((energy >= 0.08) & (energy <= 0.30)
                 & (np.min(abs(polynomial), axis=1) >= 0.25 * rms)
                 & (abs(np.sum(polynomial ** 2, axis=1)) <= 0.8 * energy)
                 & (np.sum(abs(polynomial), axis=1) < 0.799))
        return polynomial[valid]
    weights = np.full((count, 13), 0.0625000001 / 13)
    global_phase = rng.uniform(-np.pi, np.pi, (count, 1))
    phase = global_phase + np.pi / 2 + rng.integers(0, 2, (count, 13)) * np.pi
    phase[:, 11] = global_phase[:, 0]
    if style == 0:
        weights[:, 11] = rng.uniform(0.899, 0.9, count)
        weights[:, 10] += 1 - np.sum(weights, axis=1)
        phase[:, 10] = global_phase[:, 0] + np.pi / 2
        phase[:, 12] = global_phase[:, 0] + np.pi / 2
        energy = rng.uniform(0.0800000001, 0.082, count)
    elif style == 1:
        weights[:, 11] = rng.uniform(0.865, 0.8999, count)
        weights[:, 10] += 1 - np.sum(weights, axis=1)
        phase[:, 10] = global_phase[:, 0] + np.pi / 2
        phase[:, 12] = global_phase[:, 0] + np.pi / 2
        phase += rng.uniform(-0.1, 0.1, (count, 1)) * np.arange(13)
        energy = rng.uniform(0.0800000001, 0.16, count)
    elif style == 2:
        weights[:, 11] = rng.uniform(0.87, 0.8999, count)
        weights[:, :11] += rng.dirichlet(np.full(11, 0.3), count) * (1 - np.sum(weights, axis=1))[:, None]
        phase += rng.normal(0, 0.05, phase.shape)
        energy = rng.uniform(0.0800000001, 0.30, count)
    elif style == 3:
        weights[:, 11] = rng.uniform(0.85, 0.8999, count)
        weights[:, 0] += 1 - np.sum(weights, axis=1)
        phase += rng.normal(0, 0.05, phase.shape)
        energy = rng.uniform(0.0800000001, 0.30, count)
    elif style == 4:
        weights[:, 11] = rng.uniform(0.899, 0.9, count)
        weights[:, 10] += 1 - np.sum(weights, axis=1)
        phase[:, 10] = global_phase[:, 0] + np.pi / 2
        phase[:, 12] = global_phase[:, 0] + np.pi / 2
        energy = rng.uniform(0.0800000001, 0.30, count)
    elif style == 5:
        weights[:, 11] = rng.uniform(0.895, 0.9, count)
        weights[:, 10] += 1 - np.sum(weights, axis=1)
        phase[:, 10] = global_phase[:, 0] + np.pi / 2
        phase[:, 12] = global_phase[:, 0] + np.pi / 2
        phase += rng.normal(0, 0.02, phase.shape)
        energy = rng.uniform(0.0800000001, 0.081, count)
    else:
        phase[:, 0] = global_phase[:, 0] + rng.uniform(-np.pi, np.pi, count)
        phase[:, 12] = global_phase[:, 0] + rng.uniform(-np.pi, np.pi, count)
        phase[:, 10] = global_phase[:, 0] + np.pi / 2
        share = np.ones(count)
        if style == 8:
            phase[:, 10] += rng.uniform(-0.4, 0.4, count)
        if style == 9:
            share = rng.uniform(0.05, 0.95, count)
            phase[:, 0] = global_phase[:, 0] + np.pi / 2 + rng.uniform(-0.25, 0.25, count)
            phase[:, 10] += rng.uniform(-0.2, 0.2, count)
        unit_squared = np.exp(2j * (phase - global_phase))
        extra_direction = share * unit_squared[:, 10] + (1 - share) * unit_squared[:, 0]
        floor = weights[0, 0]
        fixed = floor * (np.sum(unit_squared, axis=1) - unit_squared[:, 11])
        constant = (1 - 12 * floor) * extra_direction + fixed
        direction = 1 - extra_direction
        cross = np.real(np.conj(direction) * constant)
        quadratic = abs(direction) ** 2
        maximum = (-cross + np.sqrt(cross ** 2 - quadratic * (abs(constant) ** 2 - 0.64))) / quadratic
        weights[:, 11] = maximum - rng.uniform(1e-6, 1e-3, count)
        extra = 1 - np.sum(weights, axis=1)
        weights[:, 10] += share * extra
        weights[:, 0] += (1 - share) * extra
        energy = rng.uniform(0.0800000001, 0.30 if style in (7, 9) else 0.10, count)
    polynomial = np.sqrt(energy[:, None] * weights) * np.exp(1j * phase)
    complex_enough = abs(np.sum(polynomial ** 2, axis=1)) <= 0.8 * np.sum(abs(polynomial) ** 2, axis=1)
    contractive = np.sum(abs(polynomial), axis=1) < 0.799
    if not np.all(contractive):
        contractive = np.max(abs(np.fft.fft(polynomial, 1024)), axis=1) < 0.795
    return polynomial[complex_enough & contractive]


def work(task):
    seed, count, style, cutoff = task
    rng = np.random.default_rng(seed)
    polynomials = generate(rng, count, style)
    original_count = len(polynomials)
    score = np.full(len(polynomials), np.inf)
    minimum_margin = np.full(len(polynomials), np.inf)
    records = []
    for modes, gauge in [(8192, 0), (8192, 1), (16384, 0), (16384, 1), (4096, 0), (4096, 1)]:
        if not len(polynomials):
            break
        errors, margins = batch_assess(polynomials, modes, gauge)
        score = np.minimum(score, errors)
        minimum_margin = np.minimum(minimum_margin, margins)
        keep = (score > cutoff) & (minimum_margin >= 1e-8)
        polynomials = polynomials[keep]
        score = score[keep]
        minimum_margin = minimum_margin[keep]
    indices = np.argsort(score)[-3:][::-1]
    return original_count, [(float(score[index]), polynomials[index], float(minimum_margin[index])) for index in indices]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batches', type=int, default=1000)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--style', type=int, default=-1)
    parser.add_argument('--seed', type=int, default=9881)
    args = parser.parse_args()
    best = 0
    if Path('counterexample.json').exists():
        polynomial = np.array([complex(*value) for value in json.loads(Path('counterexample.json').read_text())['P']])
        best = min(assess(polynomial, modes, gauge)[0] for modes in (4096, 8192, 16384) for gauge in (0, 1))
    started = time.monotonic()
    total = 0
    with multiprocessing.Pool(args.workers) as pool:
        for group in range(0, args.batches, args.workers * 4):
            tasks = [(args.seed + index, args.batch_size, index % 4 + 6 if args.style == -2 else index % 6 if args.style < 0 else args.style, best * 0.85)
                     for index in range(group, min(group + args.workers * 4, args.batches))]
            for valid, candidates in pool.imap_unordered(work, tasks):
                total += valid
                for approximate, polynomial, margin in candidates:
                    results = [assess(polynomial, modes, gauge) for modes in (4096, 8192, 16384) for gauge in (0, 1)]
                    score = min(record[0] for record in results)
                    if score <= best or min(record[1] for record in results) < 1e-8:
                        continue
                    best = score
                    residual = save(polynomial, 'counterexample.json')
                    print(json.dumps({'count': total, 'best': best, 'approximate': approximate, 'energy': float(np.vdot(polynomial, polynomial).real), 'errors': [record[0] for record in results], 'margin': min(record[1] for record in results), 'certificate': residual, 'elapsed': time.monotonic() - started}), flush=True)
                    if best >= 0.05 and residual <= 1e-12:
                        print(json.dumps(evaluate(Path.cwd()), indent=2), flush=True)
                        return
            if group % 80 == 0:
                print('progress', group, total, best, time.monotonic() - started, flush=True)
    print('done', total, best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
