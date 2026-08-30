import os
import time

import numpy as np

from contractor import hamiltonian_terms
from optimizer import Clock, initial_state, local_basis, restore_basis, right_canonical
from fast import left_step, right_step, center_energy, site_update, reduced_pair, extrapolate
from variational import allocate_pair


def optimize(request, start_cpu=None, start_wall=None):
    start_cpu = time.process_time() if start_cpu is None else start_cpu
    start_wall = time.monotonic() if start_wall is None else start_wall
    clock = Clock(request, start_cpu, start_wall)
    onsite, positions = hamiltonian_terms(request)
    transforms = local_basis(onsite, positions, True)
    couplings = request['coupling']
    tensors, charges = initial_state(onsite, positions, couplings, request)
    right_canonical(tensors, charges)
    length = len(tensors)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    right_environments = [None] * (length + 1)
    right_environments[length] = empty
    for site in range(length - 1, -1, -1):
        right_environments[site] = right_step(right_environments[site + 1], tensors[site],
            onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
    best_tensors = [tensor.copy() for tensor in tensors]
    best_energy = right_environments[0][0][0, 0]
    previous_energy = best_energy
    extrapolation = 1.0
    allocate_next = False
    allocation_round = 0
    allocation_done = False
    stable = 0
    site_steps = 4

    def finish(site, left_environment, right_environment):
        energy = center_energy(tensors[site], left_environment, right_environment,
            onsite[site], positions[site], couplings[site - 1] if site else 0.0,
            couplings[site] if site + 1 < length else 0.0)
        return restore_basis(best_tensors if best_energy < energy else tensors, transforms)

    for sweep in range(1000):
        previous_tensors = [tensor.copy() for tensor in tensors] if sweep >= 6 else None
        cap = min(request['bond_cap'], 4 if sweep == 0 else 8 if sweep == 1 else request['bond_cap'])
        noise = [0.1, 0.03, 0.01, 0.003, 0.001, 0.0001][min(sweep, 5)] if sweep < 6 else 0.0
        tolerance = 1e-6 if sweep < 3 else 1e-9
        pair = sweep == 3 or allocate_next
        allocate_next = False
        left_environments = [empty]
        if pair:
            previous_counts = [int(np.sum(charge)) for charge in charges]
            context = ((left_environments, right_environments)
                       if allocation_round >= 1 and request['budget_seconds'] > 8 else None)
            for site in range(length - 1):
                if clock.remaining() < 0.10:
                    return finish(site, left_environments[site], right_environments[site + 1])
                if sweep == 3:
                    reduced_pair(tensors, charges, site, left_environments[site], right_environments[site + 2],
                        onsite, positions, couplings, 1, cap, tolerance, 24, clock)
                else:
                    allocate_pair(tensors, charges, site, left_environments[site], right_environments[site + 2],
                        onsite, positions, couplings, cap, clock, context)
                left_environments.append(left_step(left_environments[site], tensors[site],
                    onsite[site], positions[site], couplings[site - 1] if site else 0.0))
            if sweep == 3:
                for site in range(length - 2, -1, -1):
                    if clock.remaining() < 0.10:
                        return finish(site + 1, left_environments[site + 1], right_environments[site + 2])
                    reduced_pair(tensors, charges, site, left_environments[site], right_environments[site + 2],
                        onsite, positions, couplings, -1, cap, tolerance, 24, clock)
                    right_environments[site + 1] = right_step(right_environments[site + 2], tensors[site + 1],
                        onsite[site + 1], positions[site + 1], couplings[site + 1] if site + 2 < length else 0.0)
            else:
                for site in range(length - 1, -1, -1):
                    if clock.remaining() < 0.08:
                        return finish(site, left_environments[site], right_environments[site + 1])
                    site_update(tensors, charges, site, left_environments[site], right_environments[site + 1],
                        onsite, positions, couplings, -1, cap, 0.0, tolerance, 6, clock)
                    right_environments[site] = right_step(right_environments[site + 1], tensors[site],
                        onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
            energy = center_energy(tensors[0], empty, right_environments[1], onsite[0], positions[0], 0.0, couplings[0])
            if sweep != 3:
                allocation_round += 1
                allocation_done = (previous_counts == [int(np.sum(charge)) for charge in charges]
                                   and abs(previous_energy - energy) < 1e-9
                                   and (context is not None or request['budget_seconds'] <= 8))
        else:
            for site in range(length):
                if clock.remaining() < 0.08:
                    return finish(site, left_environments[site], right_environments[site + 1])
                site_update(tensors, charges, site, left_environments[site], right_environments[site + 1],
                    onsite, positions, couplings, 1, cap, noise, tolerance, site_steps, clock)
                left_environments.append(left_step(left_environments[site], tensors[site],
                    onsite[site], positions[site], couplings[site - 1] if site else 0.0))
            for site in range(length - 1, -1, -1):
                if clock.remaining() < 0.08:
                    return finish(site, left_environments[site], right_environments[site + 1])
                energy = site_update(tensors, charges, site, left_environments[site], right_environments[site + 1],
                    onsite, positions, couplings, -1, cap, noise, tolerance, site_steps, clock)
                right_environments[site] = right_step(right_environments[site + 1], tensors[site],
                    onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
            if previous_tensors is not None and clock.remaining() > 0.4:
                trial, trial_charges = extrapolate(tensors, previous_tensors, charges, extrapolation)
                if trial is not None:
                    trial_environments = [None] * (length + 1)
                    trial_environments[length] = empty
                    for site in range(length - 1, -1, -1):
                        trial_environments[site] = right_step(trial_environments[site + 1], trial[site],
                            onsite[site], positions[site], couplings[site] if site + 1 < length else 0.0)
                    trial_energy = trial_environments[0][0][0, 0]
                    previous_change = previous_energy - energy
                    trial_change = trial_energy - energy
                    curvature = trial_change + extrapolation * previous_change
                    next_extrapolation = None
                    if curvature > 1e-13:
                        next_extrapolation = np.clip((extrapolation ** 2 * previous_change - trial_change) / (2 * curvature), 0.1, 12.0)
                    if trial_energy < energy:
                        tensors, charges, right_environments, energy = trial, trial_charges, trial_environments, trial_energy
                        extrapolation = min(extrapolation * 1.15, 12.0)
                    else:
                        extrapolation = max(extrapolation * 0.5, 0.1)
                    if next_extrapolation is not None:
                        extrapolation = float(next_extrapolation)
        if os.environ.get('MPS_DEBUG'):
            print(sweep, 'pair' if pair else 'site', energy, clock.remaining(),
                  [int(np.sum(charge)) for charge in charges[1:-1]], flush=True)
        if energy < best_energy:
            best_energy = energy
            best_tensors = [tensor.copy() for tensor in tensors]
        stable = stable + 1 if abs(previous_energy - energy) < 2e-12 else 0
        if sweep >= 8 and not pair:
            if allocation_done and stable >= 2:
                break
            ready = abs(previous_energy - energy) < 5e-9 if allocation_round == 0 else stable >= 2
            if ready and allocation_round < 8 and clock.remaining() > 0.5:
                allocate_next = True
        previous_energy = energy
    return restore_basis(best_tensors, transforms)
