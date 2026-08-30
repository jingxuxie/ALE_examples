import json
import os

import numpy as np

from analyze import anf, basis


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances']:
        width, count = instance['n'], instance['m']
        table = np.array(instance['table'])
        addresses = np.arange(len(table))
        records = []
        print('\n', instance['id'], 'linear', [int(table[1 << bit] ^ table[0]) for bit in range(width)])
        for difference in range(1, len(table)):
            derivative = table ^ table[addresses ^ difference]
            counts = np.bincount(derivative, minlength=1 << count)
            records.append((int(max(counts)), int(np.count_nonzero(counts)), difference, int(np.argmax(counts))))
        print('best DDT', sorted(records, reverse=True)[:20])
        print('single differences', [entry for entry in records if entry[2].bit_count() == 1])
