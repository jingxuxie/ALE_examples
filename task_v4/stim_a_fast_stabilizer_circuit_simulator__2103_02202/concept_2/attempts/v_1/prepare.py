import json
import math
from pathlib import Path


root = Path(__file__).resolve().parent
source = root.parent.parent / "participant" / "input" / "model.json"
model = json.loads(source.read_text())
columns = [int(column, 16) for column in model["columns"]]
with (root / "matrix.txt").open("w") as target:
    for column, logical in zip(columns, model["observable"]):
        target.write(f"{column:048x} {logical}\n")
print("Model:", model.keys(), flush=True)
print("Column weights:", min(column.bit_count() for column in columns),
      max(column.bit_count() for column in columns), flush=True)
for bits in [12, 14, 16, 18, 20, 22]:
    pivot_count = 192 - bits
    left_count = (512 - pivot_count) // 2
    right_count = 512 - pivot_count - left_count
    probability = (math.comb(left_count, 2) * math.comb(right_count, 2)
                   * math.comb(pivot_count, 16) / math.comb(512, 20))
    matches = math.comb(left_count, 2) * math.comb(right_count, 2) / 2 ** bits
    print("Stern", bits, "expected iterations", 1 / probability,
          "matches per iteration", matches, flush=True)
