"""Exact finite-cut assembly and sparse Fisher--Lee scattering."""

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from scipy.sparse.linalg import splu

from leads import PeriodicLead


def hopping_dictionary(case):
    blocks = {}
    for translation, matrix in zip(case["h_R"], case["h_matrices"]):
        key = tuple(translation)
        if key in blocks:
            blocks[key] = blocks[key] + matrix
        else:
            blocks[key] = matrix
    return blocks


def make_leads(case, blocks):
    orbital_count = case["h_matrices"].shape[1]
    cell_indices = {tuple(tag): index for index, tag in enumerate(case["cells"])}
    leads, interfaces = [], []
    for lead_index in range(int(case["lead_count"])):
        tags = case[f"lead_cells_{lead_index}"]
        period = case[f"lead_period_{lead_index}"]
        shape = (len(tags), orbital_count, len(tags), orbital_count)
        onsite, coupling = np.zeros(shape, complex), np.zeros(shape, complex)
        for row, row_tag in enumerate(tags):
            for column, column_tag in enumerate(tags):
                onsite_block = blocks.get(tuple(column_tag - row_tag))
                coupling_block = blocks.get(tuple(column_tag - row_tag - period))
                if onsite_block is not None:
                    onsite[row, :, column, :] = onsite_block
                if coupling_block is not None:
                    coupling[row, :, column, :] = coupling_block
        size = len(tags) * orbital_count
        onsite, coupling = onsite.reshape(size, size), coupling.reshape(size, size)
        onsite.flat[::size + 1] += float(case[f"lead_shift_{lead_index}"])
        lead = PeriodicLead(onsite, coupling)
        interface = np.asarray([cell_indices[tuple(tag)] for tag in tags])
        interface = (interface[:, None] * orbital_count + np.arange(orbital_count)).ravel()
        leads.append(lead)
        interfaces.append(interface[lead.active])
    return leads, interfaces


def device_operator(case, blocks, interfaces):
    """Assemble every nonzero hopping, reserving dense contact subblocks."""
    cells = case["cells"]
    cell_count = len(cells)
    orbital_count = case["h_matrices"].shape[1]
    size = cell_count * orbital_count
    padding = np.max(np.abs(case["h_R"]), axis=0)
    extents = np.ptp(cells, axis=0) + 2 * padding + 1
    strides = np.array([extents[1] * extents[2], extents[2], 1], dtype=np.int64)
    keys = (cells - cells.min(axis=0) + padding) @ strides
    order = np.argsort(keys)
    sorted_keys = keys[order]
    row_counts = np.ones((cell_count, orbital_count), dtype=np.int64)
    connections = []
    for translation, block in blocks.items():
        targets = keys + np.asarray(translation) @ strides
        positions = np.searchsorted(sorted_keys, targets)
        positions = np.minimum(positions, cell_count - 1)
        sources = np.flatnonzero(sorted_keys[positions] == targets)
        destinations = order[positions[sources]]
        row_counts[sources] += np.count_nonzero(block, axis=1)
        connections.append((sources, destinations, block))
    row_counts = row_counts.ravel()
    for interface in interfaces:
        row_counts[interface] += len(interface)
    indptr = np.empty(size + 1, dtype=np.int64)
    indptr[0] = 0
    np.cumsum(row_counts, out=indptr[1:])
    if indptr[-1] < np.iinfo(np.int32).max:
        indptr = indptr.astype(np.int32)
    values = np.empty(indptr[-1], dtype=complex)
    columns = np.empty(indptr[-1], dtype=np.int32)
    cursor = indptr[:-1].copy()
    values[cursor] = -case["potential"].ravel()
    columns[cursor] = np.arange(size)
    cursor += 1
    for sources, destinations, block in connections:
        for orbital in range(orbital_count):
            nonzero = np.flatnonzero(block[orbital] != 0)
            rows = sources * orbital_count + orbital
            locations = cursor[rows, None] + np.arange(len(nonzero))
            values[locations] = -block[orbital, nonzero]
            columns[locations] = destinations[:, None] * orbital_count + nonzero
            cursor[rows] += len(nonzero)
    for interface in interfaces:
        locations = cursor[interface, None] + np.arange(len(interface))
        columns[locations] = interface[None, :]
        values[locations] = 0
        cursor[interface] += len(interface)
    operator = sp.csr_matrix((values, columns, indptr), shape=(size, size))
    operator.sum_duplicates()
    operator = operator.tocsc()
    operator.sort_indices()
    diagonal = np.empty(size, dtype=np.int64)
    for column in range(size):
        start, stop = operator.indptr[column:column + 2]
        diagonal[column] = start + np.searchsorted(operator.indices[start:stop], column)
    contacts = []
    for interface in interfaces:
        locations = np.empty((len(interface), len(interface)), dtype=np.int64)
        for index, column in enumerate(interface):
            start, stop = operator.indptr[column:column + 2]
            locations[:, index] = start + np.searchsorted(operator.indices[start:stop], interface)
        contacts.append(locations)
    return operator, diagonal, contacts


def solve_transport(case):
    blocks = hopping_dictionary(case)
    leads, interfaces = make_leads(case, blocks)
    operator, diagonal, contact_locations = device_operator(case, blocks, interfaces)
    base_values = operator.data.copy()
    lead_count = len(leads)
    energy_count = len(case["energies"])
    maximum_size = max(lead.size for lead in leads)
    shape = (energy_count, lead_count, lead_count)
    result = {
        "mode_counts": np.zeros((energy_count, lead_count), dtype=np.int64),
        "transmission": np.zeros(shape),
        "channels": np.zeros(shape + (maximum_size,)),
        "partition_noise": np.zeros(shape),
        "lb_conductance": np.zeros(shape),
    }
    for lead_index, lead in enumerate(leads):
        result[f"sigma_{lead_index}"] = np.zeros((energy_count, lead.size, lead.size), complex)

    for energy_index, energy in enumerate(case["energies"]):
        operator.data[:] = base_values
        operator.data[diagonal] += energy
        factors = []
        for lead_index, lead in enumerate(leads):
            sigma, factor, count = lead.selfenergy(float(energy))
            result[f"sigma_{lead_index}"][energy_index][np.ix_(lead.active, lead.active)] = sigma
            result["mode_counts"][energy_index, lead_index] = count
            operator.data[contact_locations[lead_index]] -= sigma
            factors.append(factor)

        counts = result["mode_counts"][energy_index]
        offsets = np.r_[0, np.cumsum(counts)]
        total_modes = int(offsets[-1])
        if not total_modes:
            continue
        factorization = splu(operator, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.01,
                             options={"SymmetricMode": True})
        scattering = np.eye(total_modes, dtype=complex)
        batch_size = 32
        for incoming, (interface, source_factor) in enumerate(zip(interfaces, factors)):
            for start in range(0, counts[incoming], batch_size):
                stop = min(start + batch_size, counts[incoming])
                source = np.zeros((operator.shape[0], stop - start), dtype=complex, order="F")
                source[interface] = source_factor[:, start:stop]
                solution = factorization.solve(source)
                columns = slice(offsets[incoming] + start, offsets[incoming] + stop)
                for outgoing, (target, target_factor) in enumerate(zip(interfaces, factors)):
                    rows = slice(offsets[outgoing], offsets[outgoing + 1])
                    scattering[rows, columns] -= 1j * target_factor.conj().T @ solution[target]
        del factorization
        for outgoing in range(lead_count):
            rows = slice(offsets[outgoing], offsets[outgoing + 1])
            for incoming in range(lead_count):
                columns = slice(offsets[incoming], offsets[incoming + 1])
                scattering_block = scattering[rows, columns]
                if outgoing == incoming:
                    transmission = float(np.sum(np.abs(scattering_block) ** 2))
                else:
                    eigenvalues = np.clip(la.svdvals(scattering_block, check_finite=False) ** 2, 0, 1)
                    result["channels"][energy_index, outgoing, incoming, :len(eigenvalues)] = eigenvalues
                    result["partition_noise"][energy_index, outgoing, incoming] = np.sum(
                        eigenvalues * (1 - eigenvalues))
                    transmission = float(np.sum(eigenvalues))
                result["transmission"][energy_index, outgoing, incoming] = transmission
        result["lb_conductance"][energy_index] = np.diag(counts) - result["transmission"][energy_index]
    return result
