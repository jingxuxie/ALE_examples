import itertools
import json

import numpy as np


def patterns():
    factors = np.load('integer1.npz')
    result = []
    for name in ['A', 'B']:
        factor = factors[name]
        for permutation in itertools.permutations(range(2)):
            for signs in itertools.product([-1, 1], repeat=2):
                changed = factor[:, permutation, :] * np.array(signs)[None, :, None]
                for axes in itertools.permutations(range(3)):
                    vector = changed.transpose(axes).ravel().tolist()
                    packed = 0
                    for value in vector[:6]:
                        packed = packed * 11 + value + 5
                    result.append({'name': name, 'axes': axes, 'permutation': permutation,
                                   'signs': signs, 'packed': packed, 'values': vector})
    json.dump(result, open('patterns.json', 'w'))
    return result


if __name__ == '__main__':
    result = patterns()
    with open('patterns.txt', 'w') as output:
        output.write('\n'.join(str(value) for value in sorted({entry['packed'] for entry in result})))
