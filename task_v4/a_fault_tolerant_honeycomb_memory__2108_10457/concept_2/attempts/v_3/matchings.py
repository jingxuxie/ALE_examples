import json
import os
from pathlib import Path

source = Path(os.environ['P'])
lines = (source / 'input/scale_1.stim').read_text().splitlines()
edges = [[] for _ in range(24)]
for axis, line in enumerate(lines[2:8:2]):
    for item in line.split()[1:]:
        first, second = (int(part[1:]) for part in item.split('*'))
        edges[first].append((second, axis))
        edges[second].append((first, axis))

patterns = []
def visit(pattern):
    if -1 not in pattern:
        patterns.append(''.join(map(str, pattern)))
        return
    first = pattern.index(-1)
    for second, axis in edges[first]:
        if pattern[second] == -1:
            pattern[first] = pattern[second] = axis
            visit(pattern)
            pattern[first] = pattern[second] = -1

visit([-1] * 24)
Path('matchings.txt').write_text('\n'.join(patterns) + '\n')
Path('edges.json').write_text(json.dumps(edges))
print(len(patterns), 'perfect matchings')
