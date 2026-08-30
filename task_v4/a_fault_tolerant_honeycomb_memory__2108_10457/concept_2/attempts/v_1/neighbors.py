import itertools
from pathlib import Path

patterns = set()
for base in ("100221221100100221221100", "221100100221221100100221"):
    for distance in range(3):
        for cells in itertools.combinations(range(24), distance):
            for shifts in itertools.product((1, 2), repeat=distance):
                pattern = list(base)
                for cell, shift in zip(cells, shifts):
                    pattern[cell] = str((int(pattern[cell]) + shift) % 3)
                patterns.add("".join(pattern))
Path("neighbors.txt").write_text("\n".join(sorted(patterns)) + "\n")
print("Local variants:", len(patterns))
