import itertools
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent
words = ['stim', 'memory', 'parity', 'parity-memory', 'parity_memory', 'certificate', 'bounded-distance', 'bounded_distance', 'syndrome', 'witness', 'model', 'logical', 'hidden', 'seed', 'counterexample', 'dense', 'planted', 'instrument']
suffixes = ['', '2', '36', 'v2', 'v3', '2025', '2026', '20260206', '20260828', '512-192-36', '2103.02202']
labels = {separator.join((word, suffix)) if suffix else word for word, suffix, separator in itertools.product(words, suffixes, ['', '-', '_', ':'])}
labels |= {value.upper() for value in labels}
labels |= {f'{first}-{second}' for first in words for second in words if first != second}
labels = sorted(labels)
seeds = [0xC0FFEE, 0xBAD5EED, 0x51A81E, 0xC0DE, 0xBEEF, 0x5EED, 0xDEC0DE, 0xFA17, 0xF00D, 0xA11CE, 0xC0FFEE42, 0xC0FFEE1234, 0x5EEDC0DE, 0x123456789ABCDEF, 0xA5A5A5A5, 0xAAAAAAAA, 1000003, 1000033, 100000007, 10101010, 12341234, 987654321, 20260206, 20260828]
seeds += [int.from_bytes(value.encode(), 'little') for value in ('stim', 'STIM', 'seed', 'CODE', 'ALE')]
labels.extend(seeds)
(OUT / 'string_labels.json').write_text(json.dumps(labels))
(OUT / 'string_ids.txt').write_text('\n'.join(str(index) for index in range(len(labels)))+'\n')
with (OUT / 'string_states.txt').open('w') as output:
    for label in labels:
        state = random.Random(label).getstate()[1]
        output.write(' '.join(map(str, state))+'\n')
print('states', len(labels))
