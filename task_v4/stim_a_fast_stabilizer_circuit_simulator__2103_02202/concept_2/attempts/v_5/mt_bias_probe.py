import collections
from probe import COLUMNS, untemper


def main():
    rows = [sum(((column >> row) & 1) << fault for fault, column in enumerate(COLUMNS)) for row in range(192)]
    for transposed in [False, True]:
        vectors = rows if transposed else COLUMNS
        bits = 512 if transposed else 192
        for reversed_words in [False, True]:
            for gap in range(4):
                stream = []
                for vector in vectors:
                    words = [(vector >> shift) & 0xffffffff for shift in range(0, bits, 32)]
                    if reversed_words:
                        words.reverse()
                    stream.extend(untemper(word) for word in words)
                    stream.extend([None] * gap)
                counters = collections.defaultdict(collections.Counter)
                for index in range(len(stream) - 624):
                    if any(stream[position] is None for position in [index, index + 1, index + 397, index + 624]):
                        continue
                    joined = (stream[index] & 0x80000000) | (stream[index + 1] & 0x7fffffff)
                    difference = stream[index + 624] ^ stream[index + 397] ^ (joined >> 1) ^ (0x9908b0df if joined & 1 else 0)
                    counters[index % (bits // 32 + gap)][difference] += 1
                maximum = max((counter.most_common(1)[0][1] for counter in counters.values()), default=0)
                print('bias', transposed, reversed_words, gap, maximum, flush=True)


if __name__ == '__main__':
    main()
