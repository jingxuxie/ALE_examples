"""Sparse finite Wannier cuts and multilead Fisher--Lee scattering."""

import numpy as np
from scipy import linalg, sparse
from scipy.sparse.linalg import splu

from leads import Lead


def _cell_edges(cells, translations):
    cells = np.asarray(cells, dtype=np.int64)
    minimum = cells.min(axis=0)
    extent = cells.max(axis=0) - minimum + 1
    strides = np.array([extent[1] * extent[2], extent[2], 1], dtype=np.int64)
    keys = (cells - minimum) @ strides
    order = np.argsort(keys)
    sorted_keys = keys[order]
    rows = []
    columns = []
    hopping = []
    for index, translation in enumerate(translations):
        targets = cells + translation - minimum
        inside = np.all((targets >= 0) & (targets < extent), axis=1)
        source = np.flatnonzero(inside)
        target_keys = targets[inside] @ strides
        positions = np.searchsorted(sorted_keys, target_keys)
        valid = positions < len(cells)
        valid[valid] &= sorted_keys[positions[valid]] == target_keys[valid]
        rows.append(source[valid])
        columns.append(order[positions[valid]])
        hopping.append(np.full(np.count_nonzero(valid), index, dtype=np.int32))
    return np.concatenate(rows), np.concatenate(columns), np.concatenate(hopping)


def device_hamiltonian(case):
    blocks = case["h_matrices"]
    orbital_count = blocks.shape[1]
    cells = case["cells"]
    rows, columns, hopping = _cell_edges(cells, case["h_R"])
    order = np.argsort(rows * len(cells) + columns)
    counts = np.bincount(rows, minlength=len(cells))
    pointer = np.concatenate(([0], np.cumsum(counts))).astype(np.int32)
    size = len(cells) * orbital_count
    matrix = sparse.bsr_matrix(
        (blocks[hopping[order]], columns[order].astype(np.int32), pointer),
        shape=(size, size),
    ).tocsc()
    matrix.eliminate_zeros()
    matrix.setdiag(matrix.diagonal() + case["potential"].reshape(-1))
    matrix.sort_indices()
    return matrix


def prepare_leads(case):
    blocks = {
        tuple(translation): block
        for translation, block in zip(case["h_R"], case["h_matrices"])
    }
    orbital_count = case["h_matrices"].shape[1]
    cell_lookup = {tuple(tag): index for index, tag in enumerate(case["cells"])}
    leads = []
    interfaces = []
    for lead_index in range(int(case["lead_count"])):
        tags = case[f"lead_cells_{lead_index}"]
        period = case[f"lead_period_{lead_index}"]
        size = len(tags) * orbital_count
        onsite = np.zeros((size, size), dtype=complex)
        coupling = np.zeros_like(onsite)
        for row, tag_row in enumerate(tags):
            row_slice = slice(row * orbital_count, (row + 1) * orbital_count)
            for column, tag_column in enumerate(tags):
                column_slice = slice(column * orbital_count, (column + 1) * orbital_count)
                translation = tag_column - tag_row
                onsite[row_slice, column_slice] = blocks.get(tuple(translation), 0.0)
                coupling[row_slice, column_slice] = blocks.get(tuple(translation - period), 0.0)
        onsite.flat[::size + 1] += float(case[f"lead_shift_{lead_index}"])
        leads.append(Lead(onsite, coupling))
        cell_indices = np.array([cell_lookup[tuple(tag)] for tag in tags])
        interfaces.append(
            (cell_indices[:, None] * orbital_count + np.arange(orbital_count)).reshape(-1)
        )
    return leads, interfaces


def solve_transport(case):
    energies = case["energies"]
    lead_count = int(case["lead_count"])
    leads, interfaces = prepare_leads(case)
    maximum = max(lead.size for lead in leads)
    energy_count = len(energies)
    result = {
        "mode_counts": np.zeros((energy_count, lead_count), dtype=np.int64),
        "transmission": np.zeros((energy_count, lead_count, lead_count)),
        "channels": np.zeros((energy_count, lead_count, lead_count, maximum)),
        "partition_noise": np.zeros((energy_count, lead_count, lead_count)),
        "lb_conductance": np.zeros((energy_count, lead_count, lead_count)),
    }
    for index, lead in enumerate(leads):
        result[f"sigma_{index}"] = np.empty((energy_count, lead.size, lead.size), complex)
    hamiltonian = device_hamiltonian(case)
    size = hamiltonian.shape[0]
    contact_rows = []
    contact_columns = []
    for lead, interface in zip(leads, interfaces):
        active = interface[lead.active]
        contact_rows.append(np.repeat(active, len(active)))
        contact_columns.append(np.tile(active, len(active)))
    all_rows = np.concatenate(contact_rows)
    all_columns = np.concatenate(contact_columns)
    for energy_index, energy in enumerate(energies):
        injections = []
        selfenergies = []
        counts = []
        for lead_index, lead in enumerate(leads):
            sigma, injection, count = lead.evaluate(float(energy))
            result[f"sigma_{lead_index}"][energy_index] = sigma
            injections.append(injection)
            counts.append(count)
            selfenergies.append(sigma[np.ix_(lead.active, lead.active)].reshape(-1))
        counts = np.asarray(counts, dtype=np.int64)
        result["mode_counts"][energy_index] = counts
        if not np.sum(counts):
            continue
        contacts = sparse.coo_matrix(
            (np.concatenate(selfenergies), (all_rows, all_columns)), shape=(size, size)
        ).tocsc()
        operator = -hamiltonian - contacts
        operator.setdiag(operator.diagonal() + energy)
        operator.eliminate_zeros()
        factor = splu(operator, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.01)
        offsets = np.concatenate(([0], np.cumsum(counts)))
        channel_count = offsets[-1]
        scattering = np.empty((channel_count, channel_count), complex)
        batch_size = min(32, channel_count)
        for start in range(0, channel_count, batch_size):
            stop = min(channel_count, start + batch_size)
            sources = np.zeros((size, stop - start), dtype=complex, order="F")
            for lead_index, interface in enumerate(interfaces):
                lower = max(start, offsets[lead_index])
                upper = min(stop, offsets[lead_index + 1])
                if lower < upper:
                    sources[interface, lower - start:upper - start] = injections[lead_index][
                        :, lower - offsets[lead_index]:upper - offsets[lead_index]
                    ]
            response = factor.solve(sources)
            for lead_index, interface in enumerate(interfaces):
                scattering[offsets[lead_index]:offsets[lead_index + 1], start:stop] = (
                    -1j * injections[lead_index].conj().T @ response[interface]
                )
        scattering.flat[::channel_count + 1] += 1.0
        transmission = result["transmission"][energy_index]
        for outgoing in range(lead_count):
            for incoming in range(lead_count):
                if outgoing == incoming:
                    continue
                block = scattering[
                    offsets[outgoing]:offsets[outgoing + 1],
                    offsets[incoming]:offsets[incoming + 1],
                ]
                eigenvalues = np.clip(linalg.svdvals(block, check_finite=False) ** 2, 0.0, 1.0)
                result["channels"][energy_index, outgoing, incoming, :len(eigenvalues)] = eigenvalues
                transmission[outgoing, incoming] = np.sum(eigenvalues)
                result["partition_noise"][energy_index, outgoing, incoming] = np.sum(
                    eigenvalues * (1.0 - eigenvalues)
                )
        transmission.flat[::lead_count + 1] = np.maximum(0.0, counts - transmission.sum(axis=0))
        result["lb_conductance"][energy_index] = np.diag(counts) - transmission
        del factor, operator, response, sources, contacts
    return result
