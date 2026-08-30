import collections
import json
from pathlib import Path
from probe import COLUMNS, untemper


def main():
    best = 0
    for reversed_words in [False, True]:
        for byte_swap in [False, True]:
            words = [[(column >> shift) & 0xffffffff for shift in range(0, 192, 32)] for column in COLUMNS]
            if reversed_words:
                words = [parts[::-1] for parts in words]
            if byte_swap:
                words = [[int.from_bytes(part.to_bytes(4, 'little'), 'big') for part in parts] for parts in words]
            words = [[untemper(part) for part in parts] for parts in words]
            twists = [[(((parts[index] & 0x80000000) | (parts[index + 1] & 0x7fffffff)) >> 1) ^ (0x9908b0df if parts[index + 1] & 1 else 0) for index in range(5)] for parts in words]
            for stride in range(6, 33):
                groups = collections.defaultdict(list)
                for index in range(5):
                    if (index + 624) % stride < 6 and (index + 397) % stride < 6:
                        groups[((index + 624) // stride, (index + 397) // stride)].append(index)
                for (target_delta, middle_delta), offsets in groups.items():
                    if len(offsets) < 2:
                        continue
                    source_keys = [sum(parts[offset] << (32 * index) for index, offset in enumerate(offsets)) for parts in twists]
                    middle_keys = [sum(parts[(offset + 397) % stride] << (32 * index) for index, offset in enumerate(offsets)) for parts in words]
                    targets = {sum(parts[(offset + 624) % stride] << (32 * index) for index, offset in enumerate(offsets)): fault for fault, parts in enumerate(words)}
                    matches = []
                    lookup = targets.get
                    for source, source_key in enumerate(source_keys):
                        for middle, middle_key in enumerate(middle_keys):
                            target = lookup(source_key ^ middle_key)
                            if target is not None:
                                matches.append((source, middle, target))
                    if matches:
                        print('matches', len(matches), 'reverse', reversed_words, 'byteswap', byte_swap, 'stride', stride, 'offsets', offsets, 'example', matches[:8], flush=True)
                    if len(matches) > best:
                        best = len(matches)
                        Path('shuffled_mt_matches.json').write_text(json.dumps(dict(reversed_words=reversed_words, byte_swap=byte_swap, stride=stride, target_delta=target_delta, middle_delta=middle_delta, offsets=offsets, matches=matches)))
    print('best', best, flush=True)


if __name__ == '__main__':
    main()
