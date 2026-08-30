import json
import sys
from mpmath import mp


def evaluate(rows, position):
    previous, current = mp.mpf(1), position
    result = [mp.mpf(value) for value in rows[0]]
    for degree, row in enumerate(rows[1:], 1):
        for channel, value in enumerate(row):
            result[channel] += mp.mpf(value) * current
        previous, current = current, 2 * position * current - previous
    return result


def validate(case, result):
    mp.dps = 400
    blocks = {block['id']: block for block in case['blocks']}
    measured = [mp.mpf(0) for value in case['rhs']]
    null_error = projector_error = mp.mpf(0)
    for atom in result['atoms']:
        block = blocks[atom['block']]
        position = (mp.mpf(atom['x']) - mp.mpf(block['origin'])) / mp.mpf(block['scale'])
        assert -1 <= position <= 1
        if block['kind'] == 'point':
            assert position == 0
        weight = mp.mpf(atom['weight'])
        assert weight > 0
        first, mixed, second = map(mp.mpf, atom['projector'])
        projector = mp.matrix([[first, mixed], [mixed, second]])
        projector_error = max(projector_error, abs(first + second - 1), mp.norm(projector * projector - projector))
        matrix_first, matrix_mixed, matrix_second = evaluate(block['matrix'], position)
        matrix = mp.matrix([[matrix_first, matrix_mixed], [matrix_mixed, matrix_second]])
        null_error = max(null_error, mp.norm(matrix * projector) / mp.norm(matrix))
        for row, kernel in enumerate(block['moments']):
            diagonal_first, off_diagonal, diagonal_second = evaluate(kernel, position)
            measured[row] += weight * (diagonal_first * first + 2 * off_diagonal * mixed + diagonal_second * second)
    residual = max(abs(value - mp.mpf(target)) / max(1, abs(mp.mpf(target)))
                   for value, target in zip(measured, case['rhs']))
    assert residual <= mp.mpf('1e-8'), residual
    assert null_error <= mp.mpf('2e-8'), null_error
    assert projector_error <= mp.mpf('1e-6'), projector_error
    print('atoms', len(result['atoms']), 'relative moment residual', mp.nstr(residual, 5),
          'null residual', mp.nstr(null_error, 5), 'projector error', mp.nstr(projector_error, 5))


if __name__ == '__main__':
    validate(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))
