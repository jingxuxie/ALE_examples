import time
from probe import COLUMNS, MODEL


def complexity(bits):
    connection = 1
    backup = 1
    length = 0
    displacement = 1
    history = 0
    for index, bit in enumerate(bits):
        history = (history << 1) | bit
        if (connection & history).bit_count() & 1:
            previous = connection
            connection ^= backup << displacement
            if 2 * length <= index:
                length = index + 1 - length
                backup = previous
                displacement = 1
            else:
                displacement += 1
        else:
            displacement += 1
    return length, connection.bit_count()


def main():
    started = time.monotonic()
    for transposed in [False, True]:
        for reverse_bits in [False, True]:
            for include_observable in [False, True]:
                if transposed and include_observable:
                    continue
                if transposed:
                    sequence = [((COLUMNS[fault] >> row) & 1) for row in range(192) for fault in range(512)[::(-1 if reverse_bits else 1)]]
                else:
                    sequence = []
                    for fault, column in enumerate(COLUMNS):
                        sequence.extend((column >> row) & 1 for row in range(192)[::(-1 if reverse_bits else 1)])
                        if include_observable:
                            sequence.append(MODEL['observable'][fault])
                for tail in [False, True]:
                    chosen = sequence[-45000:] if tail else sequence[:45000]
                    print('bit complexity', transposed, reverse_bits, include_observable, tail, complexity(chosen), time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
