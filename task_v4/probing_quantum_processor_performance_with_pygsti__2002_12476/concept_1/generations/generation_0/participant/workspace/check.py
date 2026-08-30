import argparse
import json
from pathlib import Path

import numpy as np

from physics import load_assets, risks, score_risks, validate_batches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    candidates, contract = load_assets(root)
    batches, cost = validate_batches(json.loads(Path(args.submission).read_text())["batches"], candidates, contract)
    data = np.load(root / "input/development.npz")
    baseline = np.array(json.loads((root / "baseline/design.json").read_text())["batches"])
    core, family_scores = score_risks(risks(data["features"], batches),
                                      risks(data["features"], baseline), data["families"])
    print(json.dumps({"core_score": core, "family_scores": family_scores,
                      "worst_family_score": min(family_scores.values()), "execution_ticks": cost}, indent=2))


if __name__ == "__main__":
    main()
