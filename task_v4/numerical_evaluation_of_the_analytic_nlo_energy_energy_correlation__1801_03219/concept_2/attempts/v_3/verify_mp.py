import json
import sys
import time
from pathlib import Path

import mpmath as mp

from problem import ROOT
from grade_screen import measure


def integral(witness, precision):
    mp.mp.dps = precision
    data = json.loads((ROOT / 'kernel.json').read_text())
    edges = [mp.mpf(value) for value in data['edges']]
    coefficients = [[[mp.mpf(value) for value in family] for family in segment] for segment in data['coefficients']]
    bins = {'collinear': ('0.02', '0.32'), 'central': ('0.08', '0.92'), 'backward': ('0.60', '0.98')}
    lower, upper = map(mp.mpf, bins[witness['bin']])
    width = upper - lower
    colors = [mp.mpf(16) / 9, mp.mpf(4) / 9, mp.mpf(10) / 3]
    degree = len(coefficients[0][0]) + 1
    nodes, weights = mp.gauss_quadrature(degree + 1, 'legendre')
    polynomials = []
    for point in nodes:
        values = [mp.mpf(1), point]
        for order in range(2, degree + 1):
            values.append(((2 * order - 1) * point * values[-1] - (order - 1) * values[-2]) / order)
        polynomials.append(values)
    result = [mp.mpf(0)] * 3
    for segment in range(len(edges) - 1):
        left, right = max(lower, edges[segment]), min(upper, edges[segment + 1])
        if left >= right:
            continue
        middle = ((left + right) / 2 - lower) / width
        half = (right - left) / (2 * width)
        values = []
        for point in nodes:
            angular = middle + half * point
            source = lower + width * angular
            coordinate = (2 * source - edges[segment] - edges[segment + 1]) / (edges[segment + 1] - edges[segment])
            chebyshev = [mp.mpf(1), coordinate]
            for order in range(2, degree - 1):
                chebyshev.append(2 * coordinate * chebyshev[-1] - chebyshev[-2])
            detector = (1 + mp.mpf(witness['tilt']) / 16 * (2 * angular - 1)
                        + mp.mpf(witness['curvature']) / 16 * ((2 * angular - 1)**2 - mp.mpf(1) / 3)) / mp.mpf('1.5')
            values.append([2 * width * colors[channel] * detector * mp.fdot(coefficients[segment][channel], chebyshev) for channel in range(3)])
        legendre = [[mp.mpf(2 * order + 1) / 2 * mp.fsum(weights[index] * values[index][channel] * polynomials[index][order]
                                                       for index in range(len(nodes))) for order in range(degree + 1)] for channel in range(3)]
        for offset in range(12):
            frequency = witness['band_start'] + offset
            argument = 2 * mp.pi * frequency * half
            phase = mp.exp(2j * mp.pi * frequency * middle)
            transforms = [2 * mp.j**order * mp.sqrt(mp.pi / (2 * argument)) * mp.besselj(order + mp.mpf('.5'), argument) for order in range(degree + 1)]
            for channel in range(3):
                moment = half * phase * mp.fdot(legendre[channel], transforms)
                result[channel] += (witness['cosine'][offset] * moment.real + witness['sine'][offset] * moment.imag) / 10**10
    return result


if __name__ == '__main__':
    started = time.time()
    witness = json.loads(Path(sys.argv[1]).read_text())
    references = []
    for precision in (50, 80):
        values = integral(witness, precision)
        references.append(values)
        print('polynomial_reference', precision, [mp.nstr(value, precision) for value in values], time.time() - started, flush=True)
    print('precision_gaps', [mp.nstr(abs(first - second), 20) for first, second in zip(*references)], flush=True)
    report = measure(witness)
    print('binary64_gaps', [mp.nstr(abs(reference - family['reference']), 20) for reference, family in zip(references[-1], report['families'].values())], flush=True)
    print('screen', report['worst'], report['average'], flush=True)
