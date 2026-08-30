import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from build_data import build


def main():
    destination = ROOT / "adversary/private_challenges"
    destination.mkdir(parents=True, exist_ok=True)
    models, tables, diagnostics = build(600, 613997753)
    (destination / "models.json").write_text(json.dumps(models))
    np.savez_compressed(destination / "cases.npz", energies=tables)
    (destination / "diagnostics.json").write_text(json.dumps(diagnostics))
    summary = {"case_count": len(models), "families": 6, "independent_seed_offset": 613997753,
               "min_reference_weight": min(item["reference_weight"] for item in diagnostics),
               "min_gap": min(item["gap"] for item in diagnostics),
               "max_eigenpair_residual": max(item["residual"] for item in diagnostics),
               "purpose": "Broad same-distribution champion falsification space; not visible to any fresh agent."}
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
