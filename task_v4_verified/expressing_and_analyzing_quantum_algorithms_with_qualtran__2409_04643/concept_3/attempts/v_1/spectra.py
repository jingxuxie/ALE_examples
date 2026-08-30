import json
import os

import numpy as np

from analyze import anf, basis


def walsh(values):
    spectrum = np.array(values, dtype=np.int64)
    width = len(spectrum).bit_length() - 1
    for bit in range(width):
        blocks = spectrum.reshape(-1, 2, 1 << bit)
        left, right = blocks[:, 0, :].copy(), blocks[:, 1, :].copy()
        blocks[:, 0, :] = left + right
        blocks[:, 1, :] = left - right
    return spectrum


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances']:
        width, count = instance['n'], instance['m']
        table = np.array(instance['table'])
        parity = np.array([value.bit_count() % 2 for value in range(1 << max(width, count))])
        records = []
        print('\n', instance['id'])
        for combination in range(1, 1 << count):
            spectrum = walsh(1 - 2 * parity[table & combination])
            mask = np.argmax(abs(spectrum))
            records.append((int(abs(spectrum[mask])), combination, int(mask), int(spectrum[mask]), int(spectrum[0])))
        print('best Walsh', sorted(records, reverse=True)[:20])
        print('single outputs', [entry for entry in records if entry[1].bit_count() == 1])
