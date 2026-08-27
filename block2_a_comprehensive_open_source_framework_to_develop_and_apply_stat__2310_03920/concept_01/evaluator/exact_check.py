import csv
import itertools
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import eigsh, expm_multiply
from make_cases import make_case, ROOT


def assemble(case, stage):
    size = case['n_sites']
    sector = case['sector']
    electrons = []
    for bits in range(1 << (2 * size)):
        number = bits.bit_count()
        spin = sum((1 if mode % 2 == 0 else -1) for mode in range(2 * size) if bits >> mode & 1)
        if sector['kind'] == 'parity':
            keep = number % 2 == sector['value']
        else:
            keep = number == sector['value'] and (sector['kind'] == 'number' or spin == sector['twosz'])
        if keep:
            electrons.append(bits)
    boson_states = list(itertools.product(*(range(mode['levels']) for mode in case['phonons'])))
    states = [(bits, bosons) for bits in electrons for bosons in boson_states]
    lookup = {state: index for index, state in enumerate(states)}
    diagonal = np.zeros(len(states))
    onebody = []
    pairs = []
    for edge in case['edges']:
        for left_spin in range(2):
            for right_spin in range(2):
                value = complex(*edge[stage][left_spin][right_spin])
                left = edge['sites'][0] * 2 + left_spin
                right = edge['sites'][1] * 2 + right_spin
                onebody.extend([([(left, True), (right, False)], value), ([(right, True), (left, False)], value.conjugate())])
    for pair in case['pairing']:
        left = pair['sites'][0] * 2 + pair['spins'][0]
        right = pair['sites'][1] * 2 + pair['spins'][1]
        value = complex(*pair[stage])
        pairs.extend([([(left, True), (right, True)], value), ([(right, False), (left, False)], value.conjugate())])
    coordinates = {name: [[], [], []] for name in ['hopping', 'pairing', 'phonon']}
    diagonal_observables = {name: [] for name in ['number', 'spin', 'charge', 'phonon']}
    for column, (bits, bosons) in enumerate(states):
        occupancy = [(bits >> (2 * site) & 1) + (bits >> (2 * site + 1) & 1) for site in range(size)]
        spin = sum((bits >> (2 * site) & 1) - (bits >> (2 * site + 1) & 1) for site in range(size)) / 2
        diagonal_observables['number'].append(sum(occupancy))
        diagonal_observables['spin'].append(spin)
        diagonal_observables['charge'].append(sum(occupancy[site] for site in case['region']))
        diagonal_observables['phonon'].append(sum(bosons))
        diagonal[column] = sum(case['onsite'][stage][site] * occupancy[site] + case['interaction'][site] * (occupancy[site] == 2)
                               + case['zeeman'][site] * ((bits >> (2 * site) & 1) - (bits >> (2 * site + 1) & 1)) / 2
                               for site in range(size))
        diagonal[column] += sum(edge['strength'] * occupancy[edge['sites'][0]] * occupancy[edge['sites'][1]] for edge in case['density_edges'])
        diagonal[column] += sum(mode['omega'] * count for mode, count in zip(case['phonons'], bosons))
        for name, terms in [('hopping', onebody), ('pairing', pairs)]:
            for operations, amplitude in terms:
                updated, factor = bits, complex(amplitude)
                for mode, creation in reversed(operations):
                    if bool(updated >> mode & 1) == creation:
                        factor = 0
                        break
                    factor *= (-1) ** ((updated & ((1 << mode) - 1)).bit_count())
                    updated ^= 1 << mode
                if factor:
                    row = lookup[(updated, bosons)]
                    coordinates[name][0].append(row)
                    coordinates[name][1].append(column)
                    coordinates[name][2].append(factor)
        for index, mode in enumerate(case['phonons']):
            for change in [-1, 1]:
                count = bosons[index]
                if not 0 <= count + change < mode['levels']:
                    continue
                new_bosons = list(bosons)
                new_bosons[index] += change
                amplitude = np.sqrt(count + (change == 1)) * mode['coupling'][stage] * (occupancy[mode['site']] - mode['offset'])
                coordinates['phonon'][0].append(lookup[(bits, tuple(new_bosons))])
                coordinates['phonon'][1].append(column)
                coordinates['phonon'][2].append(amplitude)
    matrices = {name: coo_matrix((entries[2], (entries[0], entries[1])), shape=(len(states), len(states)), dtype=complex).tocsr()
                for name, entries in coordinates.items()}
    hamiltonian = diags(diagonal) + sum(matrices.values())
    probes = {name: diags(values) for name, values in diagonal_observables.items()}
    charge = probes['charge']
    probes['current'] = 1j * (matrices['hopping'] @ charge - charge @ matrices['hopping'])
    probes['source'] = 1j * (matrices['pairing'] @ charge - charge @ matrices['pairing'])
    probes['energy'] = hamiltonian
    return hamiltonian, probes


def exact(case):
    initial, _ = assemble(case, 'before')
    final, probes = assemble(case, 'after')
    assert abs(initial - initial.conj().T).max() < 1e-12
    eigenvalues, eigenvectors = eigsh(initial, k=1, which='SA', tol=1e-12, v0=np.random.default_rng(91).normal(size=initial.shape[0]))
    state = eigenvectors[:, 0]
    previous, rows = 0, []
    for instant in case['times']:
        if instant > previous:
            state = expm_multiply(-1j * (instant - previous) * final, state)
        norm = np.vdot(state, state).real
        row = {'time': instant, 'norm': norm}
        row.update({name: float(np.vdot(state, operator @ state).real / norm) for name, operator in probes.items()})
        rows.append(row)
        previous = instant
    return float(eigenvalues[0]), rows


def main():
    results = []
    directory = ROOT / 'solution/independent_checks'
    directory.mkdir(exist_ok=True)
    for family in ['impurity', 'ladder', 'spin_orbit', 'paired', 'vibronic']:
        case = make_case(family, 4, True)
        case['id'] = family + '_exact'
        for mode in case['phonons']:
            mode['levels'] = 3
        path = directory / (family + '.json')
        path.write_text(json.dumps(case))
        energy, rows = exact(case)
        output = directory / family
        with (directory / (family + '.log')).open('w') as handle:
            subprocess.run(['bash', str(ROOT / 'solution/run.sh'), str(path), str(output), 'refined'], stdout=handle, stderr=subprocess.STDOUT, check=True, timeout=120)
        with (output / 'trajectory.csv').open() as handle:
            observed = list(csv.DictReader(handle))
        stats = json.loads((output / 'stats.json').read_text())
        errors = {name: max(abs(expected[name] - float(measured[name])) for expected, measured in zip(rows, observed)) for name in rows[0] if name != 'time'}
        errors['initial_energy'] = abs(energy - stats['initial_energy'])
        record = {'family': family, 'errors': errors, 'passed': max(errors.values()) < 2e-6}
        results.append(record)
        print(json.dumps(record), flush=True)
    (directory / 'summary.json').write_text(json.dumps(results, indent=2))
    assert all(record['passed'] for record in results)


if __name__ == '__main__':
    main()
