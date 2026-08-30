import collections
from probe import COLUMNS

MASK64 = (1 << 64) - 1


def undo_right(value, shift, mask=MASK64):
    result = value
    for iteration in range(64 // shift + 1):
        result = value ^ ((result >> shift) & mask)
    return result


def undo_left(value, shift, mask):
    result = value
    for iteration in range(64 // shift + 1):
        result = value ^ ((result << shift) & mask)
    return result & MASK64


def mt64_untemper(value):
    value = undo_right(value, 43)
    value = undo_left(value, 37, 0xfff7eee000000000)
    value = undo_left(value, 17, 0x71d67fffeda60000)
    return undo_right(value, 29, 0x5555555555555555)


def splitmix_inverse(value):
    value = undo_right(value, 31)
    value = (value * pow(0x94d049bb133111eb, -1, 1 << 64)) & MASK64
    value = undo_right(value, 27)
    value = (value * pow(0xbf58476d1ce4e5b9, -1, 1 << 64)) & MASK64
    return undo_right(value, 30)


def main():
    rows = [sum(((column >> row) & 1) << fault for fault, column in enumerate(COLUMNS)) for row in range(192)]
    for transposed in [False, True]:
        vectors = rows if transposed else COLUMNS
        bits = 512 if transposed else 192
        for reversed_words in [False, True]:
            raw = [[(column >> shift) & MASK64 for shift in range(0, bits, 64)] for column in vectors]
            if reversed_words:
                raw = [parts[::-1] for parts in raw]
            parts_count = bits // 64
            for byte_swap in [False, True]:
                values = [[int.from_bytes(value.to_bytes(8, 'little'), 'big') for value in parts] for parts in raw] if byte_swap else raw
                words = [[mt64_untemper(value) for value in parts] for parts in values]
                stream = sum(words, [])
                matches = []
                for index in range(len(stream) - 312):
                    joined = (stream[index] & 0xffffffff80000000) | (stream[index + 1] & 0x7fffffff)
                    predicted = stream[index + 156] ^ (joined >> 1) ^ (0xb5026f5aa96619e9 if joined & 1 else 0)
                    if predicted == stream[index + 312]:
                        matches.append(index)
                print('MT64 ordered', transposed, reversed_words, byte_swap, len(matches), flush=True)
                twists = [[(((parts[index] & 0xffffffff80000000) | (parts[index + 1] & 0x7fffffff)) >> 1) ^ (0xb5026f5aa96619e9 if parts[index + 1] & 1 else 0) for index in range(parts_count - 1)] for parts in words]
                sources = [(parts[offset] | (parts[offset + 1] << 64), fault, offset) for fault, parts in enumerate(twists) for offset in range(parts_count - 2)]
                middles = [(parts[offset] | (parts[offset + 1] << 64), fault, offset) for fault, parts in enumerate(words) for offset in range(parts_count - 1)]
                targets = {key: (fault, offset) for key, fault, offset in middles}
                lookup = targets.get
                matches = []
                for source_key, source, source_offset in sources:
                    for middle_key, middle, middle_offset in middles:
                        result = lookup(source_key ^ middle_key)
                        if result is not None:
                            matches.append((source, source_offset, middle, middle_offset, *result))
                print('MT64 segments', transposed, reversed_words, byte_swap, len(matches), matches[:10], flush=True)
                inverses = [[splitmix_inverse(value) for value in parts] for parts in values]
                deltas = collections.Counter((parts[offset + 1] - parts[offset]) & MASK64 for parts in inverses for offset in range(parts_count - 1))
                print('splitmix deltas', deltas.most_common(2), flush=True)


if __name__ == '__main__':
    main()
