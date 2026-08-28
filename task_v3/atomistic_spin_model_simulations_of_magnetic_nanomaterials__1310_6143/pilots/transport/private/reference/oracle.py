import numpy as np


def solve(case):
    num_cells = sum(map(len, case['stacks']))
    num_sublattices = case['num_sublattices']
    atoms = case['atoms']
    atom_cells = np.array([atom['cell'] for atom in atoms], dtype=int)
    materials = [case['materials'][atom['material']] for atom in atoms]
    sublattices = np.array([material['sublattice'] for material in materials], dtype=int)
    channels = atom_cells*num_sublattices+sublattices
    spins = np.array([atom['spin'] for atom in atoms], dtype=float)
    moments = np.array([material['moment_muB'] for material in materials])
    atom_damping = np.array([material['alpha'] for material in materials])
    channel_count = num_cells*num_sublattices
    counts = np.bincount(channels, minlength=channel_count).reshape(num_cells, num_sublattices)
    occupied = counts > 0
    safe_counts = np.maximum(counts, 1)
    cell_counts = counts.sum(axis=1)
    total_moments = np.bincount(channels, weights=moments, minlength=channel_count).reshape(num_cells, num_sublattices)
    magnetization = np.zeros((channel_count, 3))
    np.add.at(magnetization, channels, moments[:, None]*spins)
    magnetization = magnetization.reshape(num_cells, num_sublattices, 3)/np.maximum(total_moments, 1e-300)[:, :, None]
    def means(name):
        return np.bincount(channels, weights=[material[name] for material in materials], minlength=channel_count).reshape(num_cells, num_sublattices)/safe_counts
    geometry = case['cell_length_m']/case['cell_area_m2']*cell_counts[:, None]/safe_counts
    ordinary = means('rho_ohm_m')*geometry
    spin_resistance = means('rho_spin_ohm_m')*geometry
    alpha, eta, beta = means('alpha'), means('eta'), means('beta')
    cell_resistance = np.zeros(num_cells)
    channel_current = np.zeros((num_cells, num_sublattices))
    channel_field = np.zeros((num_cells, num_sublattices, 3))
    effective_resistance = ordinary.copy()
    stack_resistance, stack_current = [], []
    for stack in case['stacks']:
        ordered = stack[::case['direction']]
        polarization = magnetization[ordered[0]].copy()
        for position, cell in enumerate(ordered):
            present = occupied[cell]
            if position:
                reduced = magnetization[cell]
                effective_resistance[cell] += 0.5*spin_resistance[cell]*(1.0-np.sum(reduced*polarization, axis=1))
                channel_field[cell] = (eta[cell]-alpha[cell]*beta[cell])[:, None]*np.cross(reduced, polarization)+(beta[cell]+alpha[cell]*eta[cell])[:, None]*polarization
                channel_field[cell, ~present] = 0.0
                polarization[present] = reduced[present]
            conductance = np.zeros(num_sublattices)
            conductance[present] = 1.0/effective_resistance[cell, present]
            cell_resistance[cell] = 1.0/conductance.sum()
        resistance = cell_resistance[stack].sum()
        current = case['voltage_V']/resistance
        stack_resistance.append(resistance)
        stack_current.append(current)
        for cell in stack:
            present = occupied[cell]
            channel_current[cell, present] = current*cell_resistance[cell]/effective_resistance[cell, present]
            channel_field[cell, present] *= (35486911.9121*channel_current[cell, present]/total_moments[cell, present])[:, None]
    atom_field = channel_field[atom_cells, sublattices]
    first_cross = np.cross(spins, atom_field)
    derivative = -1.760859e11/(1.0+atom_damping[:, None]**2)*(first_cross+atom_damping[:, None]*np.cross(spins, first_cross))
    resistance = 1.0/np.sum(1.0/np.array(stack_resistance))
    return {'total_resistance_ohm': np.array(resistance), 'total_current_A': np.array(sum(stack_current)), 'stack_resistance_ohm': np.array(stack_resistance), 'stack_current_A': np.array(stack_current), 'cell_resistance_ohm': cell_resistance, 'channel_current_A': channel_current, 'atom_field_T': atom_field, 'atom_dspin_dt': derivative}
