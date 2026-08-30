import json
from pathlib import Path

import numpy as np

from problem import BINS, COLOR, FAMILIES, basis, response, Kernel
from target import integrate

kernel = Kernel()
grid_cache = {}


def grid(witness, order, panels):
    key = witness['bin'], witness['band_start'], witness['tilt'], witness['curvature'], order, panels
    if key not in grid_cache:
        lower, upper = BINS[witness['bin']]
        boundaries = np.r_[np.linspace(0, 1, panels + 1), (kernel.edges - lower) / (upper - lower)]
        boundaries = np.unique(boundaries[(boundaries >= 0) & (boundaries <= 1)])
        nodes, weights = np.polynomial.legendre.leggauss(order)
        halves = np.diff(boundaries) / 2
        middles = (boundaries[:-1] + boundaries[1:]) / 2
        points = (middles[:, None] + halves[:, None] * nodes).ravel()
        weights = (halves[:, None] * weights).ravel()
        envelope = 2 * (upper - lower) * kernel(lower + (upper - lower) * points) * COLOR * response(points, witness)[:, None]
        grid_cache[key] = basis(points, witness), (weights[:, None] * envelope).T
    return grid_cache[key]


def measure(witness, trace=False):
    coefficients = np.array(witness['cosine'] + witness['sine']) / 1e10
    references = []
    for order, panels in ((24, 32), (36, 64), (40, 64), (56, 128)):
        basis_matrix, envelope_weights = grid(witness, order, panels)
        values = basis_matrix @ coefficients
        references.append((envelope_weights @ values, abs(envelope_weights) @ abs(values)))
    uncertainty = np.maximum(2e-11, 10 * abs(references[2][0] - references[3][0]))
    l1 = np.maximum(references[0][1], references[1][1]) + 4 * abs(references[0][1] - references[1][1])
    families = {}
    for channel, family in enumerate(FAMILIES):
        target = integrate(kernel.integrand(witness, family), trace=trace)
        error = max(0, abs(target['value'] - references[3][0][channel]) - uncertainty[channel])
        required = max(20 * target['tolerance'], 50 * target['estimated_error'], 1e-5 * l1[channel])
        families[family] = dict(target=target, reference=float(references[3][0][channel]), error=float(error), l1=float(l1[channel]),
                                margin=float(error / required), frozen_gap=float(abs(references[2][0][channel] - references[3][0][channel])),
                                coarse_l1=float(references[0][1][channel]), fine_l1=float(references[1][1][channel]))
    margins = [family['margin'] for family in families.values()]
    return dict(families=families, worst=min(margins), average=sum(margins) / 3)


if __name__ == '__main__':
    import sys
    result = measure(json.loads(Path(sys.argv[1]).read_text()), trace=True)
    print(json.dumps(result, indent=2))
