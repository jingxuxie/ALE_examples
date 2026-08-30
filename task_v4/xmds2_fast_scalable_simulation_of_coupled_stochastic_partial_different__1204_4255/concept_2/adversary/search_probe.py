import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from simulator import quick


BOUNDS = {
    "dispersion": (0.18, 0.45), "nonlinearity": (6.0, 20.0),
    "cross": (0.55, 1.3), "coupling": (0.2, 1.2), "detuning": (-0.5, 0.5),
    "duration": (0.45, 1.4), "population": (0.35, 0.65),
    "a1": (0.08, 0.4), "a2": (0.08, 0.4),
    "b1": (-0.25, 0.25), "b2": (-0.25, 0.25),
    "c1": (-0.25, 0.25), "c2": (-0.25, 0.25),
    "phase1": (-np.pi, np.pi), "phase2": (-np.pi, np.pi),
    "shift": (-np.pi, np.pi), "relative_phase": (-np.pi, np.pi),
}


def objective(metrics):
    return metrics["observable_gap"] - 0.4 * max(0, metrics["certificate"] / 0.00009 - 1) - 0.5 * max(0, metrics["tail_mass"] / 0.018 - 1)


generator = np.random.default_rng(710237)
calibration = json.loads((ROOT / "adversary" / "calibration.json").read_text())["records"]
current = calibration[8]["parameters"]
current_metrics = quick(current)
score = objective(current_metrics)
history = []
started = time.monotonic()
for index in range(160):
    proposal = dict(current)
    scale = 0.055 if index < 70 else 0.022
    for name in generator.choice(list(BOUNDS), size=5, replace=False):
        lower, upper = BOUNDS[name]
        proposal[name] = float(np.clip(proposal[name] + generator.normal() * scale * (upper - lower), lower, upper))
    try:
        metrics = quick(proposal)
        proposal_score = objective(metrics)
    except (ValueError, FloatingPointError):
        continue
    if proposal_score > score:
        current, current_metrics, score = proposal, metrics, proposal_score
        print(json.dumps({"iteration": index, "score": score, **metrics}), flush=True)
        history.append({"iteration": index, "parameters": current, "metrics": metrics})
        (ROOT / "adversary" / "privileged_candidate.json").write_text(json.dumps({"schema_version": 1, "parameters": current}, indent=2))
(ROOT / "adversary" / "search_probe.json").write_text(json.dumps({"wall_seconds": time.monotonic() - started, "improvements": history}, indent=2))
