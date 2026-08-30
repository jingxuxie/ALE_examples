import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
from model import Model


def main():
    rng = np.random.default_rng(38551)
    episodes = json.loads((ROOT / "evaluator/hidden/episodes.json").read_text())["episodes"]
    results = []
    for episode in episodes:
        model = Model(episode["spec"])
        truth = np.log(episode["rates"])
        probability = model.distribution(truth)
        errors = []
        for trial in range(4):
            start = model.bounds.mean(axis=1) if trial == 0 else rng.uniform(model.bounds[:, 0], model.bounds[:, 1])
            fitted = model.fit(probability * 1000000, initial=start, iterations=500)
            error = float(np.max(np.abs(fitted - truth)))
            errors.append(error)
        result = {"id": episode["id"], "noiseless_multistart_max_log_errors": errors}
        print(result, flush=True)
        results.append(result)
    passed = max(max(item["noiseless_multistart_max_log_errors"]) for item in results) < 0.01
    (ROOT / "adversary/inverse_report.json").write_text(json.dumps({"passed": passed, "episodes": results,
        "interpretation": "Four truth-independent starting points per episode recover exact synthetic distributions. This is an empirical injectivity/optimizer check, not a theorem of global identifiability and not a finite-budget solver."}, indent=2) + "\n")
    assert passed


if __name__ == "__main__":
    main()
