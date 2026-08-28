import math

from scipy import sparse


def correction(case, sector, cutoff, method):
    if method == 'raw':
        return sparse.csr_matrix((len(sector['energy']), len(sector['energy'])))
    mean_quartic = sum(term['value'] for term in case['couplings']
                       if term['degree'] == 4 and term.get('transfer', 0) == 0)
    shift = -mean_quartic**2 / (2 * math.pi * cutoff**2)
    if method == 'scalar_twice':
        shift *= 2
    return shift * sector['operators'][(0, 0)]
