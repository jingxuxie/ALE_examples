import math
import subprocess
import os
from pathlib import Path

import numpy as np
from scipy import sparse

from physics import circle_constants


def contractions(coefficients, boundary):
    terms = {}
    for (degree_first, transfer_first), value_first in coefficients.items():
        for (degree_second, transfer_second), value_second in coefficients.items():
            for lines in range(2, min(degree_first, degree_second) + 1):
                degree = degree_first + degree_second - 2 * lines
                transfer = transfer_first + transfer_second
                if degree == 0 and transfer != 0:
                    continue
                factor = math.comb(degree_first, lines) * math.comb(degree_second, lines) * math.factorial(lines)
                momentum = abs(transfer_first - transfer_second) / 2
                residue = lines % 2 if boundary == 'antiperiodic' else 0
                lower = int(math.floor((momentum - residue) / 2) * 2 + residue)
                upper = lower + 2
                for loop_momentum, weight in [(abs(lower), (upper - momentum) / 2),
                                               (abs(upper), (momentum - lower) / 2)]:
                    if weight <= 0:
                        continue
                    key = (degree, transfer, lines, loop_momentum)
                    terms[key] = terms.get(key, 0.0) + value_first * value_second * factor * weight
    return terms


class SpectralTail:
    def __init__(self, case, terms, directory, maximum=None):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.maximum = maximum or 160 * case['mass']
        self.mass = case['mass']
        self.difference = circle_constants(case['mass'], case['length'], case['boundary'])[0]
        keys = sorted({(key[2], key[3]) for key in terms})
        config = directory / 'spectral.txt'
        prefix = directory / 'spectral'
        config.write_text(f"{case['length']} {case['mass']} {int(case['boundary'] == 'antiperiodic')} "
                          f"{self.maximum} {len(keys)}\n" + ''.join(f'{lines} {transfer}\n' for lines, transfer in keys))
        subprocess.run([str(os.environ.get('SPECTRAL_EXE', Path(__file__).with_name('spectral'))),
                        str(config), str(prefix)], check=True)
        self.data = {}
        self.count_events = 0
        for lines, transfer in keys:
            filename = Path(str(prefix) + f'_k{lines}_q{transfer}.bin')
            with filename.open('rb') as handle:
                count = int(np.fromfile(handle, dtype=np.int64, count=1)[0])
                energies = np.fromfile(handle, dtype=np.float64, count=count)
                weights = np.fromfile(handle, dtype=np.float64, count=count)
            filename.unlink()
            permutation = np.argsort(energies)
            energies, weights = energies[permutation], weights[permutation]
            cumulative = []
            for power in range(1, 7):
                remaining = np.cumsum((weights / energies ** power)[::-1])[::-1]
                cumulative.append(np.r_[remaining, 0.0] + self.continuum_remainder(lines, power))
            self.data[(lines, transfer)] = (energies, np.array(cumulative))
            self.count_events += count

    def continuum_remainder(self, lines, power):
        points, weights = np.polynomial.legendre.leggauss(64)
        coordinate = (points + 1) / 2
        energy = self.maximum / coordinate
        logarithm = np.log(energy / self.mass)
        density_two = 1 / (2 * np.pi * energy ** 2)
        density_three = 3 * logarithm / (4 * np.pi ** 2 * energy ** 2)
        density_four = (3 * logarithm ** 2 / (4 * np.pi ** 3) - 1 / (16 * np.pi)) / energy ** 2
        density = {2: density_two,
                   3: density_three + 3 * self.difference * density_two,
                   4: density_four + 4 * self.difference * density_three +
                      6 * self.difference ** 2 * density_two}[lines]
        return np.sum(weights * self.maximum / (2 * coordinate ** 2) * density / energy ** power)

    def moments(self, lines, momentum, threshold):
        energies, cumulative = self.data[(lines, momentum)]
        positions = np.searchsorted(energies, threshold + 1e-8, side='right')
        return cumulative[:, positions]

    def coefficient(self, lines, momentum, cutoff, spectator, eigenvalue=0.0, smoothing=0.0):
        threshold = cutoff - spectator
        if smoothing:
            moments = (self.moments(lines, momentum, threshold - smoothing) +
                       self.moments(lines, momentum, threshold + smoothing)) / 2
        else:
            moments = self.moments(lines, momentum, threshold)
        shift = spectator - eigenvalue
        answer = np.zeros_like(spectator, dtype=float)
        for power in range(5, -1, -1):
            answer = moments[power] - shift * answer
        return answer


def tail_matrix(sector, cutoff, terms, spectral, eigenvalue=0.0, variant='spectator'):
    dimension = len(sector['energy'])
    result = sparse.csr_matrix((dimension, dimension))
    grouped = {}
    for (degree, transfer, lines, momentum), coupling in terms.items():
        grouped.setdefault((degree, transfer), []).append((lines, momentum, coupling))
    for key, components in grouped.items():
        if variant == 'local':
            coefficient = 0.0
            for lines, momentum, coupling in components:
                coefficient -= coupling * float(spectral.coefficient(lines, momentum, cutoff, np.array(0.0), eigenvalue))
            result += coefficient * sector['operators'][key]
            continue
        operator = sector['operators'][key].tocoo()
        spectator = (sector['energy'][operator.row] + sector['energy'][operator.col]) / 2
        if variant == 'local':
            spectator = np.zeros_like(spectator)
        else:
            spectator = np.minimum(spectator, cutoff / 3)
        values = np.zeros_like(operator.data)
        for lines, momentum, coupling in components:
            coefficient = spectral.coefficient(lines, momentum, cutoff, spectator, eigenvalue)
            values -= coupling * coefficient
        result += sparse.coo_matrix((values * operator.data, (operator.row, operator.col)), shape=operator.shape).tocsr()
    return (result + result.T) * 0.5
