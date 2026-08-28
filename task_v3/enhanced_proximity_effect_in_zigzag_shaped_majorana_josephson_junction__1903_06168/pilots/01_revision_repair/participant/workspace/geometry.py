import inspect

import numpy as np


def assemble(source, geometry):
    options = dict(
        geometry, shape='sawtooth', wraparound=geometry['infinite'],
        sc_leads=False, no_phs=False, rough_edge=None,
        phs_breaking_potential=False
    )
    if 'current' in inspect.signature(source.system).parameters:
        options.update(current=False, ns_junction=False)
    return source.system(**options)


def barrier_response(system, params, probes):
    with_barrier = system.hamiltonian_submatrix(params=params, sparse=True).tocsc()
    without_barrier = system.hamiltonian_submatrix(
        params=dict(params, V=0), sparse=True
    ).tocsc()
    difference = (with_barrier - without_barrier).diagonal().real
    nambu_signs = np.array([1, -1, 1, -1])
    response = difference.reshape(-1, 4) @ nambu_signs / (4 * params['V'])
    by_tag = {tuple(site.tag): float(value) for site, value in zip(system.sites, response)}
    return [by_tag.get(tuple(tag), 0.0) for tag in probes]
