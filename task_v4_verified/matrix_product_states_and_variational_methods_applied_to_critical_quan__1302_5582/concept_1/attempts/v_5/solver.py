import os
import time
import numpy as np
from contractor import hamiltonian_terms
from optimizer import Clock, initial_state, local_basis, qr_factor, right_canonical, restore_basis
from fast import left_step, right_step, center_energy
from sweeps import site_update
from bondsearch import search
from relaxation import accelerate
import newpair


def transport_pair(tensors, charges, site, direction):
    first, second = tensors[site:site+2]
    left, dimension, middle = first.shape
    right = second.shape[2]
    if direction == 1:
        rows = (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        orthogonal, transport, new_charge = qr_factor(first.reshape(left*dimension, middle), rows, charges[site+1])
        rank = orthogonal.shape[1]
        tensors[site] = orthogonal.reshape(left, dimension, rank)
        tensors[site+1] = (transport @ second.reshape(middle, dimension*right)).reshape(rank, dimension, right)
    else:
        columns = ((np.arange(dimension)[:, None] % 2) ^ charges[site+2][None, :]).ravel()
        orthogonal, transport, new_charge = qr_factor(second.reshape(middle, dimension*right).T, columns, charges[site+1])
        rank = orthogonal.shape[1]
        tensors[site+1] = orthogonal.T.reshape(rank, dimension, right)
        tensors[site] = (first.reshape(left*dimension, middle) @ transport.T).reshape(left, dimension, rank)
    charges[site+1] = new_charge


def optimize(request, start_cpu=None, start_wall=None):
    start_cpu = time.process_time() if start_cpu is None else start_cpu
    start_wall = time.monotonic() if start_wall is None else start_wall
    clock = Clock(request, start_cpu, start_wall)
    short = request['budget_seconds'] <= 8
    onsite, positions = hamiltonian_terms(request)
    transforms = local_basis(onsite, positions, True)
    couplings = request['coupling']
    tensors, charges = initial_state(onsite, positions, couplings, request)
    right_canonical(tensors, charges)
    length = len(tensors)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    right_environments = [None]*length+[empty]
    for site in range(length-1, -1, -1):
        right_environments[site] = right_step(right_environments[site+1], tensors[site],
            onsite[site], positions[site], couplings[site] if site+1 < length else 0.0)
    previous_energy = float('inf')
    extrapolation = 1.0
    best_tensors = None
    best_energy = float('inf')
    stable = 0
    allocation_checks = 0
    allocation_start_energy = float('inf')
    pending_pair = False
    newpair.step_limit = 10 if short else 24
    debug = bool(os.environ.get('MPS_DEBUG'))

    def finish(site, left_environment, right_environment):
        energy = center_energy(tensors[site], left_environment, right_environment,
            onsite[site], positions[site], couplings[site-1] if site else 0.0,
            couplings[site] if site+1 < length else 0.0)
        selected = best_tensors if best_tensors is not None and best_energy < energy else tensors
        return restore_basis(selected, transforms)

    for sweep in range(1000):
        early_search = short and request['bond_cap'] < 20 and sweep == 8
        previous_tensors = [tensor.copy() for tensor in tensors] if sweep >= 4 else None
        cap = min(request['bond_cap'], 4 if sweep == 0 else (8 if sweep == 1 else request['bond_cap']))
        noise = [.1, .03, .01][sweep] if sweep < 3 else 0.0
        tolerance = 1e-5 if sweep < 3 else (1e-7 if sweep < 7 else 1e-10)
        if sweep == 3 or pending_pair or early_search:
            checking_allocation = pending_pair or early_search
            counts = [(len(charge), int(np.sum(charge))) for charge in charges]
            pending_pair = False
            left_environments = [empty]
            for site in range(length-1):
                if clock.remaining() < .08:
                    return finish(site, left_environments[site], right_environments[site+1])
                if early_search and 6 <= site < length-7:
                    transport_pair(tensors, charges, site, 1)
                else:
                    method = search if checking_allocation else newpair.update
                    method(tensors, charges, site, left_environments[site], right_environments[site+2],
                        onsite, positions, couplings, 1, cap, tolerance, 24, clock)
                left_environments.append(left_step(left_environments[site], tensors[site],
                    onsite[site], positions[site], couplings[site-1] if site else 0.0))
            for site in range(length-2, -1, -1):
                if clock.remaining() < .08:
                    return finish(site+1, left_environments[site+1], right_environments[site+2])
                if early_search and 6 <= site < length-7:
                    transport_pair(tensors, charges, site, -1)
                else:
                    method = search if checking_allocation else newpair.update
                    method(tensors, charges, site, left_environments[site], right_environments[site+2],
                        onsite, positions, couplings, -1, cap, tolerance, 24, clock)
                right_environments[site+1] = right_step(right_environments[site+2], tensors[site+1],
                    onsite[site+1], positions[site+1], couplings[site+1] if site+2 < length else 0.0)
            energy = center_energy(tensors[0], empty, right_environments[1], onsite[0], positions[0], 0.0, couplings[0])
            if debug:
                print('pair', sweep, energy, clock.remaining(), flush=True)
            if energy < best_energy:
                best_energy = energy
                best_tensors = [tensor.copy() for tensor in tensors]
            stable = 0
            if checking_allocation and not early_search and counts == [(len(charge), int(np.sum(charge))) for charge in charges]:
                return restore_basis(best_tensors, transforms)
            previous_energy = energy
            continue
        left_environments = [empty]
        for site in range(length):
            if clock.remaining() < .08:
                return finish(site, left_environments[site], right_environments[site+1])
            site_update(tensors, charges, site, left_environments[site], right_environments[site+1],
                onsite, positions, couplings, 1, cap, noise, tolerance, 4, clock)
            left_environments.append(left_step(left_environments[site], tensors[site],
                onsite[site], positions[site], couplings[site-1] if site else 0.0))
        for site in range(length-1, -1, -1):
            if clock.remaining() < .08:
                return finish(site, left_environments[site], right_environments[site+1])
            energy = site_update(tensors, charges, site, left_environments[site], right_environments[site+1],
                onsite, positions, couplings, -1, cap, noise, tolerance, 4, clock)
            right_environments[site] = right_step(right_environments[site+1], tensors[site],
                onsite[site], positions[site], couplings[site] if site+1 < length else 0.0)
        if previous_tensors is not None and clock.remaining() > .3:
            tensors, charges, right_environments, energy, extrapolation = accelerate(
                tensors, previous_tensors, charges, right_environments, onsite, positions,
                couplings, previous_energy, energy, extrapolation, clock)
        if debug:
            print(sweep, energy, clock.remaining(), extrapolation, flush=True)
        if energy < best_energy:
            best_energy = energy
            best_tensors = [tensor.copy() for tensor in tensors]
        threshold = 2e-11 if short else 2e-12
        stable = stable+1 if abs(previous_energy-energy) < threshold else 0
        if sweep > 6 and stable >= (2 if short else 3):
            if (allocation_checks < 4 and clock.remaining() > (.45 if short else 1.0)
                    and (allocation_checks == 0 or best_energy < allocation_start_energy-1e-10)):
                pending_pair = True
                allocation_checks += 1
                allocation_start_energy = best_energy
                stable = 0
                previous_energy = energy
                continue
            break
        previous_energy = energy
    return restore_basis(best_tensors if best_tensors is not None else tensors, transforms)
