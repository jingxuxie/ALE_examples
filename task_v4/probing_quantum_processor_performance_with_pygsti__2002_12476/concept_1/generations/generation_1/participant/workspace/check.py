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
        families[str(family)] = float(1 - loss[selected].mean() / data["champion_loss_risks"][selected].mean())
    core = float(1 - loss.mean() / data["champion_loss_risks"].mean())
    ratio = float(intact.mean() / data["champion_intact_risks"].mean())
    print(json.dumps(dict(core_score=core, worst_family_score=min(families.values()), family_scores=families,
        mean_loss_risk=float(loss.mean()), mean_intact_risk=float(intact.mean()), intact_mean_ratio=ratio,
        execution_ticks=cost, passed=core >= .50 and min(families.values()) >= .30 and ratio <= 1.20), indent=2))


if __name__ == "__main__":
    main()
