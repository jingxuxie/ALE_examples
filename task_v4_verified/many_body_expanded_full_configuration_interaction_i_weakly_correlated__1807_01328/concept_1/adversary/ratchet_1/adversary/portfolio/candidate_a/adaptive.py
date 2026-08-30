import numpy as np

from acquisition import UNKNOWN, prior
from experiment import MASKS, ORDERS, SUBSETS


def quiet_core(terms):
    strengths = np.array([sum(abs(terms[mask]) for mask in MASKS[3] if not mask & (1 << orbital)) for orbital in range(8)])
    omitted = int(np.argmin(strengths))
    included = np.array([mask for mask in MASKS[3] if not mask & (1 << omitted)])
    ratio = float(strengths[omitted] / max(sum(abs(terms[MASKS[3]])), 1e-12))
    return omitted if ratio < .15 and np.max(abs(terms[included])) < 1.5e-6 else None


def adaptive_covariance(terms, omitted):
    original = prior(terms, fifth_weight=2)
    pair_strength = SUBSETS[UNKNOWN][:, MASKS[2]] @ abs(terms[MASKS[2]])
    activity = SUBSETS[UNKNOWN][:, MASKS[1]] @ abs(terms[MASKS[1]])
    pair_metric = pair_strength ** 2 / np.maximum(activity, 1e-10)
    old = (UNKNOWN & (1 << omitted)) == 0
    reference = max(np.median(pair_metric[old & (ORDERS[UNKNOWN] == 4)]), 1e-9)
    scales = np.sqrt(np.diag(original)).copy()
    scales[old] = 3e-6 * np.maximum(pair_metric[old], reference * .001) / reference
    scales[old] *= .03 ** (ORDERS[UNKNOWN[old]] - 4)
    return np.diag(scales ** 2 + 1e-20)
