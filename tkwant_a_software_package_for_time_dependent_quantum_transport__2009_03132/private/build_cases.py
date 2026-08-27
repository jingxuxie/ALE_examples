import json
from pathlib import Path
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def encode(value):
    array = np.asarray(value)
    return {'real': array.real.tolist(), 'imag': array.imag.tolist()}


def chain(size, onsite=0, hopping=-1):
    matrix = np.eye(size, dtype=complex) * onsite
    for site in range(size - 1):
        matrix[site, site + 1] = hopping
        matrix[site + 1, site] = complex(hopping).conjugate()
    return matrix


def lead(size, sites, mu=-0.55, temperature=0.07, hopping=-1, onsite=0, coupling=-1, cell=None, hop=None):
    width = len(sites)
    cell = np.eye(width) * onsite if cell is None else cell
    hop = np.eye(width) * hopping if hop is None else hop
    contact = np.zeros((size, width), dtype=complex)
    for channel, site in enumerate(sites):
        contact[site, channel] = coupling
    return dict(cell=encode(cell), hop=encode(hop), contact=encode(contact), mu=mu, temperature=temperature)


def drive(kind, amplitude, duration, entries=None, profile='pulse', **extra):
    result = dict(kind=kind, amplitude=amplitude, duration=duration, profile=profile, **extra)
    if entries is not None:
        result['entries'] = [[row, column, complex(value).real, complex(value).imag] for row, column, value in entries]
    return result


def case(name, family, hamiltonian, leads, drives, bonds, tmax, bound_mu=-0.55, bound_temperature=0.07):
    return dict(id=name, family=family, hamiltonian=encode(hamiltonian), leads=leads, drives=drives,
                current_bonds=bonds, times=np.linspace(0, tmax, 41).tolist(),
                bound_mu=bound_mu, bound_temperature=bound_temperature)


def fabry(hidden):
    size = 22 if hidden else 15
    matrix = chain(size)
    matrix[3, 3] = 2.3 if hidden else 1.7
    matrix[-4, -4] = 2.0 if hidden else 1.7
    for site in range(4, size - 4):
        matrix[site, site] = -0.19
    reservoirs = [lead(size, [0], temperature=0 if hidden else 0.07), lead(size, [size - 1], temperature=0 if hidden else 0.07)]
    drives = [drive('contact_phase', .46 if hidden else .3, 7.5, profile='voltage_phase', lead=0)]
    return case('fp_holdout' if hidden else 'fp_development', 'cavity_voltage', matrix, reservoirs, drives, [[size - 2, size - 3], [5, 4]], 70 if hidden else 38)


def dark(hidden):
    wire = 9 if hidden else 7
    size = wire + 2
    matrix = np.zeros((size, size), dtype=complex)
    matrix[:wire, :wire] = chain(wire)
    middle = wire // 2
    matrix[wire, wire] = matrix[wire + 1, wire + 1] = -0.21
    matrix[wire, wire + 1] = matrix[wire + 1, wire] = -.48
    for site in [wire, wire + 1]:
        matrix[middle, site] = matrix[site, middle] = -.74
    drives = [drive('add', .9 if hidden else .6, 11, [(wire, wire, 1), (wire + 1, wire + 1, -.7)])]
    reservoirs = [lead(size, [0], mu=.4), lead(size, [wire - 1], mu=-.5 if hidden else .4)]
    return case('dark_holdout' if hidden else 'sidebranch_development', 'discrete_release', matrix, reservoirs, drives, [[middle + 1, middle], [wire, middle]], 48 if hidden else 28, bound_mu=.52, bound_temperature=.045)


def ring(hidden):
    size = 12 if hidden else 8
    phase = .61 if hidden else .35
    matrix = chain(size, onsite=.13)
    matrix[0, size - 1] = -np.exp(1j * phase)
    matrix[size - 1, 0] = -np.exp(-1j * phase)
    reservoirs = [lead(size, [0], mu=.45, coupling=-.7), lead(size, [size // 2], mu=-.4, coupling=-.8)]
    if hidden:
        reservoirs.append(lead(size, [size - 3], mu=.05, hopping=-.75, onsite=.16, coupling=-.44))
    drives = [drive('phase', .72, 8.0, [(0, size - 1, matrix[0, size - 1])]),
              drive('add', .27, 6.0, [(site, site, 1) for site in range(1, size // 2)], profile='ramp')]
    return case('ring_holdout' if hidden else 'ring_development', 'flux_nonequilibrium', matrix, reservoirs, drives, [[1, 0], [size - 1, 0], [size // 2, size // 2 - 1]], 42 if hidden else 26)


def spin(hidden):
    length = 9 if hidden else 6
    size = 2 * length
    identity = np.eye(2)
    pauli_x = np.array([[0, 1], [1, 0]])
    pauli_y = np.array([[0, -1j], [1j, 0]])
    pauli_z = np.diag([1, -1])
    matrix = np.zeros((size, size), dtype=complex)
    hopping = -.82 * identity + .26j * pauli_y + (.09j * pauli_z if hidden else 0)
    for site in range(length):
        matrix[2 * site:2 * site + 2, 2 * site:2 * site + 2] = .13 * pauli_z + .11 * pauli_x
        if site:
            matrix[2 * site:2 * site + 2, 2 * site - 2:2 * site] = hopping
            matrix[2 * site - 2:2 * site, 2 * site:2 * site + 2] = hopping.conj().T
    cell = .17 * pauli_x + .09 * pauli_z
    reservoirs = [lead(size, [0, 1], mu=.32, cell=cell, coupling=-.78), lead(size, [size - 2, size - 1], mu=-.23 if hidden else .32, cell=cell, coupling=-.78)]
    gate = []
    transverse = []
    for site in range(2, length - 1):
        gate.extend([(2 * site, 2 * site, 1), (2 * site + 1, 2 * site + 1, -1)])
        transverse.append((2 * site, 2 * site + 1, 1j))
    drives = [drive('add', .49, 8, gate), drive('add', .38, 5.0, transverse, profile='ac', omega=.91)]
    return case('spin_holdout' if hidden else 'spin_development', 'spin_noncommuting', matrix, reservoirs, drives, [[size - 2, size - 4], [size - 1, size - 3], [size - 3, size - 4]], 40 if hidden else 24)


def honeycomb(hidden):
    width, height = (5, 3) if hidden else (4, 3)
    size = 2 * width * height
    matrix = np.zeros((size, size), dtype=complex)
    def site(horizontal, vertical, sublattice):
        return 2 * (horizontal * height + vertical) + sublattice
    for horizontal in range(width):
        for vertical in range(height):
            origin = site(horizontal, vertical, 0)
            for destination in [(horizontal, vertical), (horizontal - 1, vertical), (horizontal, vertical - 1)]:
                other_x, other_y = destination
                if other_x >= 0 and other_y >= 0:
                    neighbor = site(other_x, other_y, 1)
                    matrix[origin, neighbor] = matrix[neighbor, origin] = -1
            if hidden:
                matrix[origin, origin] = .06 * np.sin(1.4 * horizontal + .7 * vertical)
    left = [site(0, vertical, 0) for vertical in range(height)]
    right = [site(width - 1, vertical, 1) for vertical in range(height)]
    cell = chain(height, onsite=-.18, hopping=-.32)
    reservoirs = [lead(size, left, mu=-1.1, cell=cell, coupling=-.65), lead(size, right, mu=-.87 if hidden else -1.1, cell=cell, coupling=-.65)]
    gate = [(site(horizontal, vertical, sublattice), site(horizontal, vertical, sublattice), 1)
            for horizontal in range(1, width - 1) for vertical in range(height // 2, height) for sublattice in range(2)]
    bonds = [[site(width - 1, vertical, 0), site(width - 2, vertical, 1)] for vertical in range(height)]
    return case('honeycomb_holdout' if hidden else 'flake_development', 'honeycomb_multichannel', matrix, reservoirs, [drive('add', .36, 16, gate)], bonds, 36 if hidden else 22, bound_mu=-1.1)


def dimer(hidden):
    size = 6 if hidden else 4
    matrix = chain(size, onsite=.09, hopping=-.72)
    matrix[size // 2, size // 2] = -1.3 if hidden else -.6
    cell = np.array([[0, -.62], [-.62, 0]])
    hop = np.array([[0, -1.08], [0, 0]])
    contacts = []
    for index, site in enumerate([0, size - 1]):
        contact = np.zeros((size, 2), dtype=complex)
        contact[site, 0] = -.66
        if hidden:
            contact[site, 1] = .13j * (-1) ** index
        contacts.append(dict(cell=encode(cell), hop=encode(hop), contact=encode(contact), mu=.17 if index == 0 else -.12, temperature=.055))
    drives = [drive('add', .83, 9, [(size // 2, size // 2, 1)]), drive('contact_phase', .21, 7, profile='voltage_phase', lead=1)]
    return case('dimer_holdout' if hidden else 'dimer_development', 'gapped_reservoir', matrix, contacts, drives, [[size // 2, size // 2 - 1]], 44 if hidden else 26, bound_mu=.24, bound_temperature=.055)


def main():
    concept = ROOT / 'concept_01'
    generators = [fabry, dark, ring, spin, honeycomb, dimer]
    for hidden in [False, True]:
        cases = [generator(hidden) for generator in generators]
        path = concept / ('evaluator/hidden/cases.json' if hidden else 'participant/v_01/input/development.json')
        path.write_text(json.dumps({'cases': cases}, indent=2))
    equilibrium = fabry(False)
    equilibrium['id'] = 'stationary_control'
    equilibrium['drives'] = []
    equilibrium['times'] = np.linspace(0, 25, 26).tolist()
    short = spin(False)
    short['id'] = 'scaling_short'
    short['times'] = np.linspace(0, 12, 21).tolist()
    long = spin(False)
    long['id'] = 'scaling_long'
    long['times'] = np.linspace(0, 48, 41).tolist()
    (concept / 'participant/v_01/input/controls.json').write_text(json.dumps({'cases': [equilibrium, short, long]}, indent=2))


if __name__ == '__main__':
    main()
