import json
import random
import time
from fractions import Fraction as F
from mpmath import mp
import solve
import stress


def clustered_diagonal():
    roots = [F(5000000000 + index, 10**10) for index in range(32)]
    channels = []
    for parity in (0, 1):
        polynomial = [F(1)]
        for root in roots[parity::2]:
            polynomial = stress.mul(polynomial, [root ** 2, -2 * root, F(1)])
        channels.append(stress.to_cheb(polynomial))
    rows = [[stress.decimal(channels[0][index]), '0', stress.decimal(channels[1][index])]
            for index in range(len(channels[0]))]
    rng = random.Random(31)
    moments = [[[str(rng.randint(-100, 100)) for channel in range(3)] for degree in range(17)]
               for row in range(40)]
    block = {'id': 'cluster', 'kind': 'interval', 'origin': '0', 'scale': '1',
             'matrix': rows, 'moments': moments}
    mp.dps = 800
    target = [mp.mpf(0) for row in moments]
    truth = []
    weights = [mp.mpf('1e-12'), mp.mpf('1e11'), mp.mpf('.23456789'), mp.mpf('12345.6789')]
    for index, root in enumerate(roots):
        position = mp.mpf(root.numerator) / root.denominator
        projector = [mp.mpf(index % 2 == 0), mp.mpf(0), mp.mpf(index % 2 == 1)]
        weight = weights[index % len(weights)]
        truth.append(('cluster', position, projector, weight))
        values = solve.chebyshev_values(position, 16)
        for row, kernel in enumerate(moments):
            target[row] += weight * mp.fsum(values[degree] * int(coefficient[2 * (index % 2)])
                                           for degree, coefficient in enumerate(kernel))
    case = {'version': 1, 'blocks': [block], 'rhs': [mp.nstr(value, 240) for value in target]}
    return case, truth


if __name__ == '__main__':
    case, truth = clustered_diagonal()
    print('32 atoms clustered within 3.1e-9', flush=True)
    stress.check(case, truth)
    print('working precision', mp.dps, flush=True)
