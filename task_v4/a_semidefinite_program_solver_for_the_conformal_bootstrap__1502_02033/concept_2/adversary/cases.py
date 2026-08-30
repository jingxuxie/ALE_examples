"""Private controlled families, not participant search hints or solutions."""

import importlib.util
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


guard = load("evaluator/_frozen_guard.py", "private_control_guard")
sys.modules.setdefault("guard", guard)
baseline = load("participant/workspace/baseline_search.py", "private_control_baseline")
checker = load("evaluator/exact_checker.py", "private_control_checker")


def floating(document):
    return np.asarray(document["coefficients"], dtype=float) / document["denominator"]


def narrow_quadratic():
    coefficients = np.zeros((3, 4, 4))
    center = Fraction(257, 512)
    coordinate = 2.0 * float(center) - 1.0
    coefficients[0, 0, 0] = 0.25 + coordinate**2 / 2.0 - 2e-7
    coefficients[1, 0, 0] = -coordinate
    coefficients[2, 0, 0] = 0.25
    coefficients[0, 1, 1] = 0.1
    coefficients[0, 2, 2] = 0.2
    coefficients[:, 3, 3] = -np.trace(coefficients, axis1=1, axis2=2)
    coefficients[0, 3, 3] += 1.0
    rotation = baseline.ROTATION_NUMERATORS.astype(float) / 5.0
    return np.array([rotation @ matrix @ rotation.T for matrix in coefficients]), center


def rank_deficient_psd():
    from numpy.polynomial import chebyshev as cheb

    first = np.array([-0.125, 0.25])
    second = np.array([0.25, 0.125])
    coefficients = np.zeros((3, 4, 4))
    coefficients[:, 0, 0] = cheb.chebmul(first, first)
    coefficients[:, 1, 1] = cheb.chebmul(second, second)
    coefficients[:, 0, 1] = cheb.chebmul(first, second)
    coefficients[:, 1, 0] = coefficients[:, 0, 1]
    coefficients[0, 2, 2] = 0.25
    coefficients[:, 3, 3] = -np.trace(coefficients, axis1=1, axis2=2)
    coefficients[0, 3, 3] += 1.0
    return coefficients


def eligible_candidate(seed=1729, order=4, depth=3e-7, gap=2e-6):
    for offset in range(20):
        document = baseline.make_candidate(seed + offset * 997, order=order, depth=depth, gap=gap)
        try:
            checked = checker.check_document(document)
        except checker.InvalidSubmission:
            continue
        return document, checked
    raise RuntimeError("control generator failed to produce an eligible candidate")
