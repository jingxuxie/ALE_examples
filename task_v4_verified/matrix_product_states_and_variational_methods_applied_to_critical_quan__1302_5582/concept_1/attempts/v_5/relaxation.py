import numpy as np
from optimizer import factor, right_canonical
from fast import right_step


def accelerate(tensors, previous, charges, environments, onsite, positions,
               couplings, previous_energy, energy, amount, clock):
    if any(tensor.shape != old.shape for tensor, old in zip(tensors, previous)):
        return tensors, charges, environments, energy, 1.0
    aligned = [tensor.copy() for tensor in tensors]
    for site in range(len(tensors)-1, 0, -1):
        left, dimension, right = aligned[site].shape
        overlap = aligned[site].reshape(left, dimension*right) @ previous[site].reshape(left, dimension*right).T
        vectors, _, covectors, _ = factor(overlap, charges[site], charges[site], left)
        rotation = vectors @ covectors
        aligned[site] = (rotation.T @ aligned[site].reshape(left, dimension*right)).reshape(left, dimension, right)
        aligned[site-1] = np.tensordot(aligned[site-1], rotation, axes=(2, 0))
    if np.sum(aligned[0]*previous[0]) < 0:
        aligned[0] *= -1
    changes = [current-old for current, old in zip(aligned, previous)]
    previous_change = previous_energy-energy
    best = tensors, charges, environments, energy
    next_amount = amount
    for iteration in range(2):
        trial = [current+amount*change for current, change in zip(aligned, changes)]
        trial_charges = [charge.copy() for charge in charges]
        right_canonical(trial, trial_charges)
        trial_environments = [None]*(len(tensors)+1)
        trial_environments[-1] = (np.zeros((1, 1)), np.zeros((1, 1)))
        for site in range(len(tensors)-1, -1, -1):
            trial_environments[site] = right_step(trial_environments[site+1], trial[site],
                onsite[site], positions[site], couplings[site] if site+1 < len(tensors) else 0.0)
        trial_energy = trial_environments[0][0][0, 0]
        change = trial_energy-energy
        if trial_energy < best[3]:
            best = trial, trial_charges, trial_environments, trial_energy
        curvature = change+amount*previous_change
        if curvature > 1e-14:
            optimum = (amount*amount*previous_change-change)/(2*curvature)
            next_amount = float(np.clip(optimum, .05, 30.0))
        else:
            next_amount = min(30.0, amount*3.0)
        if clock.remaining() < .2 or abs(next_amount-amount) < .15*amount:
            break
        amount = next_amount
    return (*best, next_amount)
