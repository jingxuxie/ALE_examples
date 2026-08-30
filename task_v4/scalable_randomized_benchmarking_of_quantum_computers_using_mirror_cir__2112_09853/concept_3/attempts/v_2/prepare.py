import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / "participant"
spec = json.loads((PARTICIPANT / "input/spec.json").read_text())
for family in spec["families"]:
    target = family["targets"]
    values = [family["id"], family["n"], family["max_rounds"], family["max_cx"],
              target["min_single"], target["min_double"],
              target["mean_single_milli"] / 1000, target["mean_double_milli"] / 1000,
              len(family["edges"])]
    text = " ".join(map(str, values)) + "\n"
    text += "\n".join(" ".join(map(str, edge)) for edge in family["edges"]) + "\n"
    (ROOT / (family["id"] + ".cfg")).write_text(text)
