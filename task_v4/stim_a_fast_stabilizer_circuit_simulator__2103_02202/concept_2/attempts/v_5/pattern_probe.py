import json
import random
from pathlib import Path
from probe import COLUMNS, MODEL


def save(support):
    if not 1 <= len(support) <= 36:
        return
    syndrome = 0
    observable = 0
    for fault in support:
        syndrome ^= COLUMNS[fault]
        observable ^= MODEL['observable'][fault]
    if not syndrome and observable:
        print('FOUND', support, flush=True)
        Path('pattern_best.json').write_text(json.dumps({'faults': sorted(support)}))
        raise SystemExit


def main():
    for start in range(512):
        for stride in range(1, 512):
            syndrome = 0
            support = []
            for count in range(min(36, 512 // (stride & -stride))):
                fault = (start + count * stride) % 512
                support.append(fault)
                syndrome ^= COLUMNS[fault]
                if not syndrome:
                    save(support)
    print('arithmetic supports complete', flush=True)
    minimum = 513
    for stride in [1, 3, 5, 7, 9, 11, 13, 15, 17, 31, 33, 63, 65, 127, 129, 255, 257]:
        for start in range(0, 512, 8):
            basis = {}
            for offset in range(224):
                fault = (start + offset * stride) % 512
                value = COLUMNS[fault]
                support = 1 << fault
                while value:
                    pivot = value.bit_length() - 1
                    if pivot not in basis:
                        basis[pivot] = value, support
                        break
                    value ^= basis[pivot][0]
                    support ^= basis[pivot][1]
                if not value:
                    weight = support.bit_count()
                    if weight < minimum:
                        minimum = weight
                        print('structured basis minimum', minimum, stride, start, flush=True)
                    if weight <= 36:
                        save([index for index in range(512) if (support >> index) & 1])
    print('structured bases complete', minimum, flush=True)


if __name__ == '__main__':
    main()
