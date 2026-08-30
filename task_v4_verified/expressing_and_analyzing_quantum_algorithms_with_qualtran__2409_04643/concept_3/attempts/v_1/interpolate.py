import json
import os
import random
import time

import numpy as np

from periodic import normalized


def evaluation_rows(width, degree):
    monomials = [mask for mask in range(1 << width) if mask.bit_count() <= degree]
    positions = {mask: 1 << index for index, mask in enumerate(monomials)}
    rows = []
    for address in range(1 << width):
        subset, row = address, 0
        while True:
            row |= positions.get(subset, 0)
            if not subset:
                break
            subset = (subset - 1) & address
        rows.append(row)
    return monomials, rows


def row_basis(rows):
    pivots = {}
    checks = []
    for index, row in enumerate(rows):
        combination = 1 << index
        while row:
            pivot = row.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = row, combination
                break
            old_row, old_combination = pivots[pivot]
            row ^= old_row
            combination ^= old_combination
        if not row:
            checks.append(combination)
    return pivots, checks


def decode_syndrome(checks, labels, count):
    syndrome = sum(((check & labels).bit_count() & 1) << bit for bit, check in enumerate(checks))
    if not syndrome:
        return 0
    columns = [sum(((check >> index) & 1) << bit for bit, check in enumerate(checks)) for index in range(count)]
    singles = {column: index for index, column in enumerate(columns)}
    if syndrome in singles:
        return 1 << singles[syndrome]
    pairs = {}
    for first in range(count):
        for second in range(first):
            value = columns[first] ^ columns[second]
            remaining = syndrome ^ value
            if not remaining:
                return (1 << first) ^ (1 << second)
            if remaining in singles:
                return (1 << first) ^ (1 << second) ^ (1 << singles[remaining])
            if remaining in pairs:
                old_first, old_second = divmod(pairs[remaining], count)
                return (1 << first) ^ (1 << second) ^ (1 << old_first) ^ (1 << old_second)
            pairs[value] = first * count + second
    return None


def interpolate(instance, degree, trials=12):
    width, count = instance['n'], instance['m']
    outputs, masks = normalized(instance)
    weights = outputs.sum(axis=0)
    labels = (2 * weights > count + 1).astype(int)
    confidence = abs(2 * weights - count - 1)
    monomials, all_rows = evaluation_rows(width, degree)
    generator = random.Random(761)
    best = int(weights.sum())
    started = time.time()
    print(instance['id'], 'degree', degree, 'dimension', len(monomials), 'zero', best, flush=True)
    for trial in range(trials):
        ordering = list(range(1 << width))
        generator.shuffle(ordering)
        ordering.sort(key=lambda address: -confidence[address])
        selected = ordering[:min(len(monomials) + 128, len(ordering))]
        pivots, checks = row_basis([all_rows[address] for address in selected])
        target = sum(int(labels[address]) << index for index, address in enumerate(selected))
        errors = decode_syndrome(checks, target, len(selected))
        print('trial', trial, 'rank', len(pivots), 'checks', len(checks), 'errors', None if errors is None else errors.bit_count(), 'seconds', time.time()-started, flush=True)
        if errors is None:
            continue
        target ^= errors
        solution = 0
        for pivot in sorted(pivots):
            row, combination = pivots[pivot]
            value = ((combination & target).bit_count() ^ (row & solution).bit_count()) & 1
            solution |= value << pivot
        decoded = np.array([(row & solution).bit_count() & 1 for row in all_rows], dtype=np.int64)
        cost = int((outputs ^ decoded).sum() + decoded.sum())
        print('cost', cost, 'label mismatch', int((decoded ^ labels).sum()), 'weight', decoded.sum(), flush=True)
        if cost < best:
            best = cost
            np.save(instance['id'] + '_interpolated.npy', decoded)
            json.dump({'degree': degree, 'monomials': [monomials[index] for index in range(len(monomials)) if solution >> index & 1], 'cost': cost}, open(instance['id'] + '_interpolated.json', 'w'))
            return decoded


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances'][:3]:
        interpolate(instance, instance['n'] - 7)
