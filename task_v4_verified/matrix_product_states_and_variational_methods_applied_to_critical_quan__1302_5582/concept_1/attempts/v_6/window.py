import numpy as np

from fast import left_step, right_step, site_update, center_energy
from optimizer import qr_factor


def optimize_window(tensors, charges, site, environments, onsite, positions, couplings, cap, clock):
    left_environments, right_environments = environments
    start = max(0, site - 1)
    stop = min(len(tensors) - 1, site + 2)
    dimension = tensors[site].shape[1]
    physical = np.arange(dimension) % 2
    for current in range(site + 1, start, -1):
        left, _, right = tensors[current].shape
        columns = (physical[:, None] ^ charges[current + 1][None, :]).ravel()
        orthogonal, transport, new_charge = qr_factor(tensors[current].reshape(left, dimension * right).T,
                                                     columns, charges[current])
        tensors[current] = orthogonal.T.reshape(len(new_charge), dimension, right)
        tensors[current - 1] = np.tensordot(tensors[current - 1], transport.T, axes=(2, 0))
        charges[current] = new_charge
    right_blocks = {stop + 1: right_environments[stop + 1]}
    for current in range(stop, start, -1):
        right_blocks[current] = right_step(right_blocks[current + 1], tensors[current],
            onsite[current], positions[current], couplings[current] if current + 1 < len(tensors) else 0.0)
    for iteration in range(2):
        if clock.remaining() < 0.13:
            break
        left_blocks = {start: left_environments[start]}
        for current in range(start, stop):
            site_update(tensors, charges, current, left_blocks[current], right_blocks[current + 1],
                onsite, positions, couplings, 1, cap, 0.0, 1e-9, 8, clock)
            left_blocks[current + 1] = left_step(left_blocks[current], tensors[current],
                onsite[current], positions[current], couplings[current - 1] if current else 0.0)
        for current in range(stop, start, -1):
            site_update(tensors, charges, current, left_blocks[current], right_blocks[current + 1],
                onsite, positions, couplings, -1, cap, 0.0, 1e-9, 8, clock)
            right_blocks[current] = right_step(right_blocks[current + 1], tensors[current],
                onsite[current], positions[current], couplings[current] if current + 1 < len(tensors) else 0.0)
    for current in range(start, site + 1):
        left, _, right = tensors[current].shape
        rows = (charges[current][:, None] ^ physical[None, :]).ravel()
        orthogonal, transport, new_charge = qr_factor(tensors[current].reshape(left * dimension, right),
                                                     rows, charges[current + 1])
        tensors[current] = orthogonal.reshape(left, dimension, len(new_charge))
        tensors[current + 1] = np.tensordot(transport, tensors[current + 1], axes=(1, 0))
        charges[current + 1] = new_charge
    left_block = left_environments[start]
    for current in range(start, site + 1):
        left_block = left_step(left_block, tensors[current], onsite[current], positions[current],
                              couplings[current - 1] if current else 0.0)
    right_block = right_environments[stop + 1]
    for current in range(stop, site + 1, -1):
        right_block = right_step(right_block, tensors[current], onsite[current], positions[current],
                                couplings[current] if current + 1 < len(tensors) else 0.0)
    return center_energy(tensors[site + 1], left_block, right_block, onsite[site + 1], positions[site + 1],
                         couplings[site], couplings[site + 1] if site + 2 < len(tensors) else 0.0)
