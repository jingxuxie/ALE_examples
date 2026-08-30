"""Private root-cause observables, not extra scoring targets."""

import numpy as np


def diagnostics(tensors, request, contractor):
    tensors = contractor.canonicalize(tensors)
    _, positions = contractor.hamiltonian_terms(request)
    length = len(tensors)
    right = [None] * (length + 1)
    right[length] = np.ones((1, 1))
    for site in range(length - 1, -1, -1):
        right[site] = np.einsum("apr,bps,rs->ab", tensors[site].conj(), tensors[site],
                                right[site + 1], optimize=True)
    environment = np.ones((1, 1))
    means, edges, correlations = [], [], []
    edge = np.diag([0.0] * (request["local_dim"] - 2) + [1.0, 1.0])
    for site, tensor in enumerate(tensors):
        position_environment = contractor.transfer(environment, tensor, positions[site])
        means.append(float(np.einsum("ab,ab->", position_environment, right[site + 1]).real))
        edge_environment = contractor.transfer(environment, tensor, edge)
        edges.append(float(np.einsum("ab,ab->", edge_environment, right[site + 1]).real))
        if site + 1 < length:
            neighbor = contractor.transfer(position_environment, tensors[site + 1], positions[site + 1])
            correlations.append(float(np.einsum("ab,ab->", neighbor, right[site + 2]).real))
        environment = contractor.transfer(environment, tensor)
    return {"site_phi": means, "site_top_two_population": edges,
            "neighbor_phi_phi": correlations, "max_cutoff_edge_population": max(edges)}
