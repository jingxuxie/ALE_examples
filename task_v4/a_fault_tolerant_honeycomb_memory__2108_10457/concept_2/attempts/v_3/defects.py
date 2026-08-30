import itertools
import json
from pathlib import Path

edges = json.loads(Path('edges.json').read_text())
patterns = set()
counts = [0] * 5

def visit(pattern, monomers, limit):
    if -1 not in pattern:
        if len(monomers) != limit:
            return
        counts[limit] += 1
        for choices in itertools.product(range(3), repeat=limit):
            for cell, axis in zip(monomers, choices):
                pattern[cell] = axis
            matched = sum(pattern[first] == axis and pattern[second] == axis
                          for first in range(24) for second, axis in edges[first]) // 2
            if matched == (24 - limit) // 2:
                patterns.add(''.join(map(str, pattern)))
        for cell in monomers:
            pattern[cell] = -2
        return
    first = pattern.index(-1)
    if len(monomers) < limit:
        pattern[first] = -2
        visit(pattern, monomers + [first], limit)
        pattern[first] = -1
    for second, axis in edges[first]:
        if pattern[second] == -1:
            pattern[first] = pattern[second] = axis
            visit(pattern, monomers, limit)
            pattern[first] = pattern[second] = -1

visit([-1] * 24, [], 2)
Path('defect2.txt').write_text('\n'.join(sorted(patterns)) + '\n')
print(counts, len(patterns), flush=True)
