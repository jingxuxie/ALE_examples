import numpy as np


def integrals(case, stage):
    sites = case['n_sites']
    one_body = np.diag(case['onsite'][stage]).astype(float)
    two_body = np.zeros((sites,) * 4)
    for site, strength in enumerate(case['interaction']):
        two_body[site, site, site, site] = strength / 2
    for edge in case['edges']:
        left, right = edge['sites']
        amplitude = (edge[stage][0][0][0] + edge[stage][1][1][0]) / 2
        one_body[left, right] += amplitude
        one_body[right, left] += amplitude
    return one_body, two_body
