"""Independent, high-precision composite Gauss-Legendre references."""

import bisect
import json
import sys
from functools import lru_cache
from pathlib import Path

import mpmath as mp
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))
from problem import BINS, FAMILIES, Kernel


@lru_cache(maxsize=6)
def rule(order, precision):
    with mp.workdps(precision):
        nodes, weights = mp.gauss_quadrature(order, "legendre")
        return tuple(nodes), tuple(weights)


def mp_weight(position, witness):
    coordinate = 2 * position - 1
    response = (1 + mp.mpf(witness["tilt"]) / 16 * coordinate
                + mp.mpf(witness["curvature"]) / 16 * (coordinate**2 - mp.mpf(1) / 3)) / mp.mpf("1.5")
    phase = 2 * mp.pi * position
    step_cos, step_sin = mp.cos(phase), mp.sin(phase)
    current_cos, current_sin = mp.cos(witness["band_start"] * phase), mp.sin(witness["band_start"] * phase)
    total = mp.mpf(0)
    for cosine, sine in zip(witness["cosine"], witness["sine"]):
        total += cosine * current_cos + sine * current_sin
        current_cos, current_sin = current_cos * step_cos - current_sin * step_sin, current_sin * step_cos + current_cos * step_sin
    return response * total / 10**10


def clenshaw(coefficients, coordinate):
    previous = mp.mpf(0)
    current = mp.mpf(0)
    for coefficient in reversed(coefficients[1:]):
        previous, current = current, coefficient + 2 * coordinate * current - previous
    return coefficients[0] + coordinate * current - previous


def mp_integral(witness, degree=88, precision=80, order=36, panels=64, native=False):
    with mp.workdps(precision):
        left, right = [mp.mpf(str(value)) for value in BINS[witness["bin"]]]
        colors = [mp.mpf(16) / 9, mp.mpf(4) / 9, mp.mpf(10) / 3]
        if native:
            from native_kernel import _components
            edges = [mp.mpf(".02"), mp.mpf(".98")]
            coefficients = None
        else:
            with open(ROOT / "evaluator/hidden" / ("kernel_" + str(degree) + ".json"), encoding="utf-8") as stream:
                expansion = json.load(stream)
            edges = [mp.mpf(value) for value in expansion["edges"]]
            coefficients = [[[mp.mpf(value) for value in channel] for channel in panel] for panel in expansion["coefficients"]]
        breaks = sorted(set([mp.mpf(index) / panels for index in range(panels + 1)]
                            + [(edge - left) / (right - left) for edge in edges if left < edge < right]))
        nodes, weights = rule(order, precision)
        sums = [[] for _ in range(3)]
        absolute_sums = [[] for _ in range(3)]
        for lower, upper in zip(breaks[:-1], breaks[1:]):
            half = (upper - lower) / 2
            for node, quadrature_weight in zip(nodes, weights):
                position = (lower + upper) / 2 + half * node
                argument = left + (right - left) * position
                if native:
                    values = [4 * argument * (1 - argument) * value for value in _components(argument)]
                else:
                    index = min(bisect.bisect_right(edges, argument) - 1, len(edges) - 2)
                    coordinate = (2 * argument - edges[index] - edges[index + 1]) / (edges[index + 1] - edges[index])
                    values = [clenshaw(channel, coordinate) for channel in coefficients[index]]
                common = half * quadrature_weight * 2 * (right - left) * mp_weight(position, witness)
                for channel in range(3):
                    term = common * colors[channel] * values[channel]
                    sums[channel].append(term)
                    absolute_sums[channel].append(abs(term))
        return {"value": [mp.nstr(mp.fsum(terms), precision - 8) for terms in sums],
                "l1": [mp.nstr(mp.fsum(terms), precision - 8) for terms in absolute_sums],
                "degree": None if native else degree, "dps": precision,
                "order": order, "panels": panels, "nodes": len(sums[0]),
                "native": native}


def frozen_integral(witness, order, panels):
    kernel = Kernel()
    nodes, weights = np.polynomial.legendre.leggauss(order)
    points = ((np.arange(panels)[:, None] + (nodes[None, :] + 1) / 2) / panels).ravel()
    weights = np.tile(weights / (2 * panels), panels)
    return [float(np.dot(weights, kernel.integrand(witness, family)(points))) for family in FAMILIES]


def verify(witness):
    coarse = mp_integral(witness, degree=64, precision=50, order=24, panels=32)
    fine = mp_integral(witness, degree=88, precision=80, order=36, panels=64)
    frozen_coarse = frozen_integral(witness, 40, 64)
    frozen_fine = frozen_integral(witness, 56, 128)
    audits = []
    with mp.workdps(85):
        for channel in range(3):
            value = mp.mpf(fine["value"][channel])
            gap = abs(value - mp.mpf(coarse["value"][channel]))
            frozen_gap = abs(frozen_fine[channel] - frozen_coarse[channel])
            kernel_gap = abs(mp.mpf(frozen_fine[channel]) - value)
            uncertainty = max(mp.mpf("2e-11"), 100 * gap, 10 * frozen_gap, 10 * kernel_gap)
            l1_coarse = mp.mpf(coarse["l1"][channel])
            l1_fine = mp.mpf(fine["l1"][channel])
            l1_guard = max(l1_coarse, l1_fine) + 4 * abs(l1_coarse - l1_fine)
            resolved = gap <= mp.mpf("1e-18") * max(1, abs(value)) and frozen_gap <= 2e-10 and kernel_gap <= mp.mpf("2e-10")
            audits.append({"reference_value": str(value), "reference_refinement_gap": str(gap),
                           "frozen_refinement_gap": frozen_gap, "source_vs_frozen_gap": str(kernel_gap),
                           "uncertainty_allowance": str(uncertainty), "reference_l1_guard": str(l1_guard),
                           "resolved": bool(resolved)})
    return {"coarse": coarse, "fine": fine, "frozen_coarse": frozen_coarse,
            "frozen_fine": frozen_fine, "channels": audits}
