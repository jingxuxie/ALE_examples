import argparse
import json
from pathlib import Path

import numpy as np

from physics import load_assets, validate_batches
from resilience import risk_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    candidates, contract = load_assets(root)
    batches, cost = validate_batches(json.loads(Path(args.submission).read_text())["batches"], candidates, contract)
    data = np.load(root / "input/development.npz", allow_pickle=False)
    intact, loss, worst = risk_profile(data["features"], batches, contract["lost_circuits"], 64)
    families = {}
    for family in np.unique(data["families"]):
        selected = data["families"] == family
        families[str(family)] = float(data["champion_intact_risks"][selected].mean() / loss[selected].mean())
    core = float(data["champion_intact_risks"].mean() / loss.mean())
    ratio = float(intact.mean() / data["champion_intact_risks"].mean())
    print(json.dumps(dict(core_score=core, worst_family_score=min(families.values()), family_scores=families,
        mean_loss_risk=float(loss.mean()), mean_intact_risk=float(intact.mean()), intact_mean_ratio=ratio,
        execution_ticks=cost, passed=core >= contract["target_core_score"] and min(families.values()) >= contract["target_worst_family_score"] and ratio <= 1.20), indent=2))


if __name__ == "__main__":
    main()
