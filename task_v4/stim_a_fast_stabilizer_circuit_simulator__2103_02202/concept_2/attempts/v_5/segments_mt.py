import collections
import json
from pathlib import Path
from probe import COLUMNS, untemper


def main():
    for reversed_words in [False, True]:
        for byte_swap in [False, True]:
            words = [[(column >> shift) & 0xffffffff for shift in range(0, 192, 32)] for column in COLUMNS]
            if reversed_words:
                words = [parts[::-1] for parts in words]
            if byte_swap:
                words = [[int.from_bytes(part.to_bytes(4, 'little'), 'big') for part in parts] for parts in words]
            words = [[untemper(part) for part in parts] for parts in words]
            twists = [[(((parts[index] & 0x80000000) | (parts[index + 1] & 0x7fffffff)) >> 1) ^ (0x9908b0df if parts[index + 1] & 1 else 0) for index in range(5)] for parts in words]
            sources = [(parts[offset] | (parts[offset + 1] << 32), fault, offset) for fault, parts in enumerate(twists) for offset in range(4)]
            middles = [(parts[offset] | (parts[offset + 1] << 32), fault, offset) for fault, parts in enumerate(words) for offset in range(5)]
            targets = {key: (fault, offset) for key, fault, offset in middles}
            lookup = targets.get
            matches = []
            for source_key, source, source_offset in sources:
                for middle_key, middle, middle_offset in middles:
                    result = lookup(source_key ^ middle_key)
                    if result is not None:
                        matches.append((source, source_offset, middle, middle_offset, *result))
            print('segments', reversed_words, byte_swap, 'matches', len(matches), 'examples', matches[:20], flush=True)
            if matches:
                Path(f'segment_matches_{int(reversed_words)}_{int(byte_swap)}.json').write_text(json.dumps(matches))


if __name__ == '__main__':
    main()
