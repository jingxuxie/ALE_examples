import os
import time

import numpy as np

import core
from contractor import hamiltonian_terms


class Clock:
    def __init__(self, request, start_cpu, start_wall):
        self.cpu = start_cpu + request["budget_seconds"] - 0.45
        self.wall = start_wall + request.get("wall_seconds", 120.0) - 0.65

    def remaining(self):
        return min(self.cpu - time.process_time(), self.wall - time.monotonic())


def physical_action(operator, tensor):
    left, dimension, right = tensor.shape
    transformed = operator @ tensor.transpose(1, 0, 2).reshape(dimension, left * right)
    return transformed.reshape(dimension, left, right).transpose(1, 0, 2)


def left_step(environment, tensor, onsite, position, coupling):
    energy, edge = environment
    left, dimension, right = tensor.shape
    positioned = physical_action(position, tensor)
    acted = (energy @ tensor.reshape(left, dimension * right)).reshape(tensor.shape)
    acted += physical_action(onsite, tensor)
    acted -= coupling * (edge @ positioned.reshape(left, dimension * right)).reshape(tensor.shape)
    matrix = tensor.reshape(left * dimension, right)
    new_energy = matrix.conj().T @ acted.reshape(left * dimension, right)
    new_edge = matrix.conj().T @ positioned.reshape(left * dimension, right)
    return (new_energy + new_energy.conj().T) * 0.5, (new_edge + new_edge.conj().T) * 0.5


def right_step(environment, tensor, onsite, position, coupling):
    energy, edge = environment
    left, dimension, right = tensor.shape
    positioned = physical_action(position, tensor)
    acted = (tensor.reshape(left * dimension, right) @ energy).reshape(tensor.shape)
    acted += physical_action(onsite, tensor)
    acted -= coupling * (positioned.reshape(left * dimension, right) @ edge).reshape(tensor.shape)
    matrix = tensor.reshape(left, dimension * right)
    new_energy = acted.reshape(left, dimension * right) @ matrix.conj().T
    new_edge = positioned.reshape(left, dimension * right) @ matrix.conj().T
    return (new_energy + new_energy.conj().T) * 0.5, (new_edge + new_edge.conj().T) * 0.5


def charge_qr(matrix, row_charge=None, column_charge=None):
    if row_charge is None:
        orthogonal, triangular = np.linalg.qr(matrix, mode="reduced")
        return orthogonal, triangular, None
    blocks = []
    rank = 0
    for charge in (0, 1):
        rows = np.flatnonzero(row_charge == charge)
        columns = np.flatnonzero(column_charge == charge)
        if not len(rows) or not len(columns):
            continue
        orthogonal, triangular = np.linalg.qr(matrix[np.ix_(rows, columns)], mode="reduced")
        blocks.append((charge, rows, columns, orthogonal, triangular))
        rank += orthogonal.shape[1]
    left_result = np.zeros((matrix.shape[0], rank), dtype=matrix.dtype)
    right_result = np.zeros((rank, matrix.shape[1]), dtype=matrix.dtype)
    new_charge = np.empty(rank, dtype=int)
    offset = 0
    for charge, rows, columns, orthogonal, triangular in blocks:
        indices = np.arange(offset, offset + orthogonal.shape[1])
        left_result[np.ix_(rows, indices)] = orthogonal
        right_result[np.ix_(indices, columns)] = triangular
        new_charge[indices] = charge
        offset += len(indices)
    return left_result, right_result, new_charge


def site_action(left_environment, right_environment, onsite, position,
                left_coupling, right_coupling, shape, row_charge=None, column_charge=None):
    left_energy, left_position = left_environment
    right_energy, right_position = right_environment
    left, dimension, right = shape
    indices = None
    if row_charge is not None:
        indices = np.flatnonzero((row_charge[:, None] == column_charge[None, :]).ravel())

    def pack(tensor):
        vector = tensor.ravel()
        return vector if indices is None else vector[indices]

    def unpack(vector):
        if indices is None:
            return vector.reshape(shape)
        tensor = np.zeros(shape, dtype=vector.dtype)
        tensor.ravel()[indices] = vector
        return tensor

    def matvec(vector):
        tensor = unpack(vector)
        positioned = physical_action(position, tensor)
        image = (left_energy @ tensor.reshape(left, dimension * right)).reshape(shape)
        image += physical_action(onsite, tensor)
        image += (tensor.reshape(left * dimension, right) @ right_energy).reshape(shape)
        image -= left_coupling * (left_position @ positioned.reshape(left, dimension * right)).reshape(shape)
        image -= right_coupling * (positioned.reshape(left * dimension, right) @ right_position).reshape(shape)
        return pack(image)

    diagonal = (np.diag(left_energy)[:, None, None] + np.diag(onsite)[None, :, None]
                + np.diag(right_energy)[None, None, :]
                - left_coupling * np.diag(left_position)[:, None, None] * np.diag(position)[None, :, None]
                - right_coupling * np.diag(position)[None, :, None] * np.diag(right_position)[None, None, :])
    return matvec, pack(diagonal), pack, unpack


def site_update(tensors, charges, site, left_environment, right_environment,
                onsite, positions, couplings, direction, tolerance, clock):
    left, dimension, right = tensors[site].shape
    row_charge = column_charge = None
    if charges is not None:
        row_charge = (charges[site][:, None] ^ (np.arange(dimension)[None, :] % 2)).ravel()
        column_charge = charges[site + 1]
    matvec, diagonal, pack, unpack = site_action(
        left_environment, right_environment, onsite[site], positions[site],
        couplings[site - 1] if site else 0.0,
        couplings[site] if site + 1 < len(tensors) else 0.0,
        tensors[site].shape, row_charge, column_charge)
    vector, energy = core.lowest(matvec, diagonal, pack(tensors[site]), tolerance, 12, clock)
    tensor = unpack(vector)
    if direction == 1 and site + 1 < len(tensors):
        orthogonal, triangular, new_charge = charge_qr(
            tensor.reshape(left * dimension, right), row_charge, column_charge)
        tensors[site] = orthogonal.reshape(left, dimension, orthogonal.shape[1])
        tensors[site + 1] = np.tensordot(triangular, tensors[site + 1], axes=(1, 0))
        if charges is not None:
            charges[site + 1] = new_charge
    elif direction == -1 and site:
        row_charge = None if charges is None else charges[site]
        column_charge = None if charges is None else (
            (np.arange(dimension)[:, None] % 2) ^ charges[site + 1][None, :]).ravel()
        orthogonal, triangular, new_charge = charge_qr(
            tensor.reshape(left, dimension * right).T, column_charge, row_charge)
        tensors[site] = orthogonal.T.reshape(orthogonal.shape[1], dimension, right)
        tensors[site - 1] = np.tensordot(tensors[site - 1], triangular.T, axes=(2, 0))
        if charges is not None:
            charges[site] = new_charge
    else:
        tensors[site] = tensor
    return energy


def optimize(request, start_cpu=None, start_wall=None):
    start_cpu = time.process_time() if start_cpu is None else start_cpu
    start_wall = time.monotonic() if start_wall is None else start_wall
    clock = Clock(request, start_cpu, start_wall)
    onsite, positions = hamiltonian_terms(request)
    fields = request["field"]
    symmetric_onsite = [local + field * position for local, field, position in zip(onsite, fields, positions)]
    transforms = core.local_basis(symmetric_onsite, positions, True)
    onsite = [local - field * position for local, field, position in zip(symmetric_onsite, fields, positions)]
    initial_request = dict(request, field=[0.0] * request["n_sites"],
                           sector="even" if request["sector"] == "any" else request["sector"])
    couplings = request["coupling"]
    tensors, charges = core.initial_state(symmetric_onsite, positions, couplings, initial_request)
    core.right_canonical(tensors, charges)
    if request["sector"] == "any" and any(fields):
        charges = None
    length = len(tensors)
    empty = (np.zeros((1, 1)), np.zeros((1, 1)))
    rights = [None] * (length + 1)
    rights[length] = empty
    for site in range(length - 1, -1, -1):
        rights[site] = right_step(rights[site + 1], tensors[site], onsite[site], positions[site],
                                  couplings[site] if site + 1 < length else 0.0)
    energy = float("inf")
    for sweep, scheduled_cap in enumerate((4, 12, request["bond_cap"])):
        cap = min(request["bond_cap"], scheduled_cap)
        tolerance = 2e-5 if sweep == 0 else 2e-7
        max_steps = 36 if sweep == 0 else 18
        lefts = [empty]
        for site in range(length - 1):
            if clock.remaining() < 0.10:
                return core.restore_basis(tensors, transforms)
            energy, _ = core.pair_update(tensors, charges, site, lefts[site], rights[site + 2],
                                         onsite, positions, couplings, cap, 1, tolerance, max_steps, clock)
            lefts.append(left_step(lefts[site], tensors[site], onsite[site], positions[site],
                                   couplings[site - 1] if site else 0.0))
        for site in range(length - 2, -1, -1):
            if clock.remaining() < 0.10:
                return core.restore_basis(tensors, transforms)
            energy, _ = core.pair_update(tensors, charges, site, lefts[site], rights[site + 2],
                                         onsite, positions, couplings, cap, -1, tolerance, max_steps, clock)
            rights[site + 1] = right_step(rights[site + 2], tensors[site + 1], onsite[site + 1],
                                          positions[site + 1], couplings[site + 1] if site + 2 < length else 0.0)
        if os.environ.get("MPS_DEBUG"):
            print("pair", sweep, cap, energy, clock.remaining(), flush=True)
    previous = float("inf")
    tolerance = 1e-7
    for sweep in range(240):
        lefts = [empty]
        for site in range(length):
            if clock.remaining() < 0.08:
                return core.restore_basis(tensors, transforms)
            energy = site_update(tensors, charges, site, lefts[site], rights[site + 1],
                                  onsite, positions, couplings, 1, tolerance, clock)
            lefts.append(left_step(lefts[site], tensors[site], onsite[site], positions[site],
                                   couplings[site - 1] if site else 0.0))
        for site in range(length - 1, -1, -1):
            if clock.remaining() < 0.08:
                return core.restore_basis(tensors, transforms)
            energy = site_update(tensors, charges, site, lefts[site], rights[site + 1],
                                  onsite, positions, couplings, -1, tolerance, clock)
            rights[site] = right_step(rights[site + 1], tensors[site], onsite[site], positions[site],
                                      couplings[site] if site + 1 < length else 0.0)
        change = abs(previous - energy)
        if os.environ.get("MPS_DEBUG"):
            print("single", sweep, energy, change, clock.remaining(), flush=True)
        if sweep >= 4 and change < 5e-12:
            break
        tolerance = max(2e-11, min(1e-7, change / (10 * length)))
        previous = energy
    return core.restore_basis(tensors, transforms)
