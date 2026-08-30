import json
import random
import time
from fractions import Fraction as F
import solve
from mpmath import mp


def mul(first, second):
    return list(reversed(solve.multiply(list(reversed(first)), list(reversed(second)))))


def add(first, second):
    result = [F(0)] * max(len(first), len(second))
    for index, value in enumerate(first):
        result[index] += value
    for index, value in enumerate(second):
        result[index] += value
    return result


def scale(polynomial, factor):
    return [value * factor for value in polynomial]


def decimal(value):
    value = F(value)
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    assert denominator == 1
    places = max(twos, fives)
    integer = value.numerator * 2 ** (places - twos) * 5 ** (places - fives)
    digits = str(abs(integer)).rjust(places + 1, '0')
    return ('-' if integer < 0 else '') + (digits[:-places] + '.' + digits[-places:] if places else digits)


def to_cheb(polynomial):
    powers = [[F(1)]]
    for degree in range(1, len(polynomial)):
        last = powers[-1]
        following = [F(0)] * (len(last) + 1)
        for index, value in enumerate(last):
            if index == 0:
                following[1] += value
            else:
                following[index - 1] += value / 2
                following[index + 1] += value / 2
        powers.append(following)
    result = [F(0)] * len(polynomial)
    for coefficient, power in zip(polynomial, powers):
        for index, value in enumerate(power):
            result[index] += coefficient * value
    return result


def make_block(roots, orders, positive_centers, rotation, anisotropy=F(1), offset='0', width='1', block_id='b0'):
    first = [F(1)]
    for root, order in zip(roots, orders):
        for repeat in range(order):
            first = mul(first, [-root, F(1)])
    second = [F(1)]
    for center, imaginary in positive_centers:
        second = mul(second, [center ** 2 + imaginary ** 2, -2 * center, F(1)])
    rotation_squared = mul(rotation, rotation)
    channels = [scale(add(first, mul(rotation_squared, second)), anisotropy ** 2),
                mul(rotation, add(first, scale(second, -1))),
                scale(add(mul(rotation_squared, first), second), 1 / anisotropy ** 2)]
    cheb = [to_cheb(channel) for channel in channels]
    rows = [[decimal(channel[index]) if index < len(channel) else '0' for channel in cheb]
            for index in range(max(map(len, cheb)))]
    block = {'id': block_id, 'kind': 'interval', 'origin': offset, 'scale': width,
             'matrix': rows, 'moments': []}
    return block


def add_moments(blocks, locations):
    mp.dps = 300
    rng = random.Random(1729)
    count = sum(map(len, locations))
    for block in blocks:
        block['moments'] = [[[str(rng.randint(-100, 100)) for channel in range(3)]
                             for degree in range(17)] for row in range(40)]
    target = [mp.mpf(0) for row in range(40)]
    truth = []
    weights = [mp.mpf('1e-12'), mp.mpf('1e11'), mp.mpf('.23456789'), mp.mpf('12345.6789')]
    for block, positions in zip(blocks, locations):
        matrix = solve.power_matrix(block['matrix'])
        for position in positions:
            position = mp.mpf(position.numerator) / position.denominator
            first, mixed, second = [solve.evaluate(channel, position) for channel in matrix]
            projector = [second / (first + second), -mixed / (first + second), first / (first + second)]
            weight = weights[len(truth) % len(weights)]
            truth.append((block['id'], position, projector, weight))
            values = solve.chebyshev_values(position, 16)
            for row, kernel in enumerate(block['moments']):
                target[row] += weight * mp.fsum(values[index] * (int(coefficient[0]) * projector[0]
                                   + 2 * int(coefficient[1]) * projector[1]
                                   + int(coefficient[2]) * projector[2])
                                   for index, coefficient in enumerate(kernel))
    return {'version': 1, 'blocks': blocks, 'rhs': [mp.nstr(value, 240) for value in target]}, truth


def check(case, truth):
    started = time.perf_counter()
    result = solve.solve(case)
    elapsed = time.perf_counter() - started
    assert len(result['atoms']) == len(truth), (len(result['atoms']), len(truth))
    blocks = {block['id']: block for block in case['blocks']}
    location_error = direction_error = weight_error = mp.mpf(0)
    for atom, (block_id, position, projector, weight) in zip(result['atoms'], truth):
        block = blocks[block_id]
        recovered_position = (mp.mpf(atom['x']) - mp.mpf(block['origin'])) / mp.mpf(block['scale'])
        location_error = max(location_error, abs(recovered_position - position))
        direction_error = max(direction_error, *(abs(mp.mpf(value) - reference) for value, reference in zip(atom['projector'], projector)))
        weight_error = max(weight_error, abs(mp.mpf(atom['weight']) / weight - 1))
    print('seconds',round(elapsed, 3), 'atoms', len(truth), 'errors',*[mp.nstr(error, 5) for error in [location_error, direction_error, weight_error]], flush=True)
    return elapsed


if __name__ == '__main__':
    roots = [F('-0.8000000001'), F('-0.8'), F('-0.0000000001'), F(0), F('.0000000001'), F('.9')]
    block = make_block(roots, [2] * 6, [(F('.42'), F('1e-30')), (F('.1'), F('1e-45'))],
                       [F('.7'), F('.25'), F('.11')])
    print('near-coincident and positive minima', flush=True)
    check(*add_moments([block], [roots]))
    print('degree64 high-order', flush=True)
    block = make_block(roots, [10] * 6, [(F('.42'), F('1e-30'))], [F('.7'), F('.25'), F('.11')])
    check(*add_moments([block], [roots]))
    print('multiscale', flush=True)
    block = make_block(roots, [2] * 6, [], [F('.7'), F('.25')], F('1e40'), '1e100', '1e-100')
    check(*add_moments([block], [roots]))
    print('32 coupled atoms', flush=True)
    roots = [F(-8 + index * 2, 10) for index in range(8)]
    blocks = [make_block(roots, [2] * 8, [], [F('.7'), F('.25')], block_id='b'+str(index)) for index in range(4)]
    check(*add_moments(blocks, [roots] * 4))
