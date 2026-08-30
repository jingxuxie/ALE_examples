import json
import re
from pathlib import Path

participant = Path(__file__).resolve().parents[2] / "participant"
lines = (participant / "input/scale_1.stim").read_text().splitlines()
neighbors = [[] for qubit in range(24)]
for axis, line in enumerate(lines[2:7:2]):
    for left, right in re.findall(r"[XYZ](\d+)\*[XYZ](\d+)", line):
        left, right = int(left), int(right)
        neighbors[left].append((right, axis))
        neighbors[right].append((left, axis))
patterns = []


def enumerate_matchings(remaining, axes):
    if not remaining:
        patterns.append("".join(map(str, axes)))
        return
    left = min(remaining)
    for right, axis in neighbors[left]:
        if right in remaining:
            axes[left] = axes[right] = axis
            enumerate_matchings(remaining - {left, right}, axes)


enumerate_matchings(set(range(24)), [0] * 24)
Path("matchings.txt").write_text("\n".join(patterns) + "\n")
print("Perfect matchings:", len(patterns))
