import collections
import random
from probe import COLUMNS, MODEL, recurrence, untemper


def reverse_bits(value):
    return int(f'{value:032b}'[::-1], 2)


def main():
    rows = [sum(((column >> row) & 1) << fault for fault, column in enumerate(COLUMNS)) for row in range(192)]
    for transposed in [False, True]:
        vectors = rows if transposed else COLUMNS
        bits = 512 if transposed else 192
        for vector_reverse in [False, True]:
            for word_reverse in [False, True]:
                for transform in [lambda value: value, reverse_bits, lambda value: int.from_bytes(value.to_bytes(4, 'little'), 'big')]:
                    words = []
                    for vector in vectors[::(-1 if vector_reverse else 1)]:
                        parts = [(vector >> shift) & 0xffffffff for shift in range(0, bits, 32)]
                        words.extend(untemper(transform(part)) for part in parts[::(-1 if word_reverse else 1)])
                    matches, differences = recurrence(words)
                    if matches:
                        print('MT', transposed, vector_reverse, word_reverse, transform.__name__, len(matches), 'of', len(matches) + len(differences), matches[:20])
    generator = random.Random(173)
    values = [generator.getrandbits(32) for count in range(3072)]
    matches, differences = recurrence([untemper(value) for value in values])
    print('MT self test', len(matches), len(differences))
    bases = []
    for trial in range(5):
        order = list(range(512))
        if trial:
            generator.shuffle(order)
        basis = {}
        kernels = []
        for fault in order:
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
                kernels.append(support)
        print('basis', trial, 'rank', len(basis), 'weight range', min(value.bit_count() for value in kernels), max(value.bit_count() for value in kernels))
        bases.append(kernels)
    def syndrome(support):
        result = 0
        while support:
            index = (support & -support).bit_length() - 1
            result ^= COLUMNS[index]
            support &= support - 1
        return result
    kernel = bases[0][0]
    full = (1 << 512) - 1
    print('cyclic shifts', [shift for shift in range(1, 512) if not syndrome(((kernel << shift) | (kernel >> (512 - shift))) & full)])
    print('xor permutations', [shift for shift in range(1, 512) if not syndrome(sum(1 << (index ^ shift) for index in range(512) if (kernel >> index) & 1))])


if __name__ == '__main__':
    main()
