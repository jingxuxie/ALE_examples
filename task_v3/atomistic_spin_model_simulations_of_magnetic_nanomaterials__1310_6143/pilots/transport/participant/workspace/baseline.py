import json
import math
import sys


def cross(left, right):
    return [left[1]*right[2]-left[2]*right[1], left[2]*right[0]-left[0]*right[2], left[0]*right[1]-left[1]*right[0]]


def solve(case):
    num_cells = sum(map(len, case['stacks']))
    num_sublattices = case['num_sublattices']
    atoms = case['atoms']
    materials = [case['materials'][atom['material']] for atom in atoms]
    members = [[] for unused in range(num_cells)]
    for atom_index, atom in enumerate(atoms):
        members[atom['cell']].append(atom_index)
    total_moments = [sum(materials[index]['moment_muB'] for index in selected) for selected in members]
    magnetization = [[sum(materials[index]['moment_muB']*atoms[index]['spin'][axis] for index in selected)/total_moments[cell] for axis in range(3)] for cell, selected in enumerate(members)]
    def mean_parameter(name):
        return [sum(materials[index][name] for index in selected)/len(selected) for selected in members]
    geometry = case['cell_length_m']/case['cell_area_m2']
    ordinary = [value*geometry for value in mean_parameter('rho_ohm_m')]
    spin_resistance = [value*geometry for value in mean_parameter('rho_spin_ohm_m')]
    alpha, eta, beta = mean_parameter('alpha'), mean_parameter('eta'), mean_parameter('beta')
    cell_resistance = ordinary[:]
    cell_field = [[0.0]*3 for unused in members]
    channel_current = [[0.0]*num_sublattices for unused in members]
    stack_resistance, stack_current = [], []
    for stack in case['stacks']:
        ordered = stack[::case['direction']]
        for previous, cell in zip(ordered[:-1], ordered[1:]):
            polarization = magnetization[previous]
            current_magnetization = magnetization[cell]
            alignment = sum(left*right for left, right in zip(polarization, current_magnetization))
            cell_resistance[cell] += 0.5*spin_resistance[cell]*(1.0-alignment)
            crossed = cross(current_magnetization, polarization)
            cell_field[cell] = [(eta[cell]-alpha[cell]*beta[cell])*crossed[axis]+(beta[cell]+alpha[cell]*eta[cell])*polarization[axis] for axis in range(3)]
        resistance = sum(cell_resistance[cell] for cell in stack)
        current = case['voltage_V']/resistance
        stack_resistance.append(resistance)
        stack_current.append(current)
        for cell in stack:
            factor = 35486911.9121*current/total_moments[cell]
            cell_field[cell] = [value*factor for value in cell_field[cell]]
            for index in members[cell]:
                channel_current[cell][materials[index]['sublattice']] += current/len(members[cell])
    atom_field, derivative = [], []
    for atom, material in zip(atoms, materials):
        field = cell_field[atom['cell']]
        atom_field.append(field)
        first_cross = cross(atom['spin'], field)
        second_cross = cross(atom['spin'], first_cross)
        damping = material['alpha']
        factor = -1.760859e11/(1.0+damping*damping)
        derivative.append([factor*(first_cross[axis]+damping*second_cross[axis]) for axis in range(3)])
    resistance = 1.0/sum(1.0/value for value in stack_resistance)
    return {'total_resistance_ohm': resistance, 'total_current_A': math.fsum(stack_current), 'stack_resistance_ohm': stack_resistance, 'stack_current_A': stack_current, 'cell_resistance_ohm': cell_resistance, 'channel_current_A': channel_current, 'atom_field_T': atom_field, 'atom_dspin_dt': derivative}


if __name__ == '__main__':
    with open(sys.argv[1]) as source:
        case = json.load(source)
    with open(sys.argv[2], 'w') as destination:
        json.dump(solve(case), destination, allow_nan=False)
