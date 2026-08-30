import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import linprog

from problem import BINS, COLOR, FAMILIES, Kernel, basis, response, validate
from target import NODES, KWEIGHTS, GWEIGHTS, COMPANION_NODES, COMPANION_WEIGHTS
from local_api import measure

kernel = Kernel()
ref_nodes, ref_weights = np.polynomial.legendre.leggauss(96)


def matrix(witness, left, right, nodes, weights):
    half = (right - left) / 2
    points = (left + right) / 2 + half * nodes
    lower, upper = BINS[witness['bin']]
    envelope = 2 * (upper - lower) * kernel(lower + (upper - lower) * points) * COLOR
    return np.einsum('nc,nj,n->cj', envelope, basis(points, witness), half * weights * response(points, witness))


def checks(witness, leaf):
    left, right = leaf / 8, (leaf + 1) / 8
    parent_left, parent_right = (leaf // 2) / 4, (leaf // 2 + 1) / 4
    sibling_left, sibling_right = (leaf ^ 1) / 8, ((leaf ^ 1) + 1) / 8
    kronrod = matrix(witness, left, right, NODES, KWEIGHTS)
    embedded = kronrod - matrix(witness, left, right, NODES, GWEIGHTS)
    guard = kronrod - matrix(witness, left, right, COMPANION_NODES, COMPANION_WEIGHTS)
    inherited = kronrod + matrix(witness, sibling_left, sibling_right, NODES, KWEIGHTS) - matrix(witness, parent_left, parent_right, NODES, KWEIGHTS)
    true_error = kronrod - matrix(witness, left, right, ref_nodes, ref_weights)
    return np.concatenate((embedded, guard, inherited)), true_error


def quantize(witness, coefficients):
    integers = np.rint(coefficients / np.abs(coefficients).sum() * (10**10 - 48)).astype(np.int64)
    result = dict(witness, cosine=integers[:12].tolist(), sine=integers[12:].tolist())
    validate(result)
    return result


def run():
    started = time.time()
    best = 0
    candidates = []
    for bin_name in BINS:
        for band_start in (53, 49, 45, 41, 37):
            witness = dict(version=1, bin=bin_name, band_start=band_start, tilt=0, curvature=0)
            for leaf in range(8):
                constraints, errors = checks(witness, leaf)
                scales = np.linalg.norm(constraints, axis=1)
                null = null_space(constraints / scales[:, None], rcond=1e-13)
                direction = null @ (null.T @ errors[0])
                candidate = quantize(witness, direction)
                coefficients = np.array(candidate['cosine'] + candidate['sine']) / 1e10
                predicted = errors @ coefficients
                residual = constraints @ coefficients
                potential = min(np.abs(predicted))
                candidates.append((potential, candidate, leaf, np.max(np.abs(residual))))
    candidates.sort(key=lambda item: item[0], reverse=True)
    for potential, candidate, leaf, residual in candidates[:30]:
        result = measure(candidate, trace=True, kernel=kernel)
        margin = result['worst_screen_margin']
        summary = [(family, details['target']['panels'], details['screen_error'], details['target']['estimated_error'], details['screen_margin']) for family, details in result['families'].items()]
        print('screen', candidate['bin'], candidate['band_start'], leaf, potential, residual, margin, summary, flush=True)
        if margin > best:
            best = margin
            Path('witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
            Path('best_report.json').write_text(json.dumps(result, indent=2) + '\n')
    print('done', best, time.time() - started, flush=True)


if __name__ == '__main__':
    run()
