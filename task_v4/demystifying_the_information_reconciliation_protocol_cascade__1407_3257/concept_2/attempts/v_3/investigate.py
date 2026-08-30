import collections
import itertools
import json
from pathlib import Path

root = Path('/tmp/cascade-c2-g2-v3-mirk7s27')
deployment = json.loads((root / 'participant/input/deployment.json').read_text())
signatures = [[] for position in range(deployment['n'])]
for pass_index, specification in enumerate(deployment['passes']):
    for offset, position in enumerate(specification['permutation']):
        signatures[position].append(offset // 128)
output = root / 'attempts/v_3'
(output / 'signatures.txt').write_text('\n'.join(' '.join(map(str, signature)) for signature in signatures))
pair_counts = collections.Counter()
for dimensions in itertools.combinations(range(6), 3):
    groups = collections.defaultdict(list)
    for position, signature in enumerate(signatures):
        groups[tuple(signature[dimension] for dimension in dimensions)].append(position)
    for group in groups.values():
        for pair in itertools.combinations(group, 2):
            pair_counts[pair] += 1
for pair, count in pair_counts.items():
    if count > 1:
        print(pair, signatures[pair[0]], signatures[pair[1]], flush=True)
basis = {}
best_weight = 8192
for first, second in sorted(pair_counts, key=lambda pair: -pair_counts[pair]):
    syndrome = 0
    for position in (first, second):
        for pass_index, block in enumerate(signatures[position]):
            syndrome ^= 1 << (64 * pass_index + block)
    support = (1 << first) ^ (1 << second)
    while syndrome:
        pivot = syndrome.bit_length() - 1
        if pivot not in basis:
            basis[pivot] = syndrome, support
            break
        other_syndrome, other_support = basis[pivot]
        syndrome ^= other_syndrome
        support ^= other_support
    if syndrome == 0 and support and support.bit_count() < best_weight:
        best_weight = support.bit_count()
        positions = [position for position in range(8192) if support >> position & 1]
        print('KERNEL', best_weight, positions, flush=True)
        (output / 'core.json').write_text(json.dumps({'errors': positions}) + '\n')
