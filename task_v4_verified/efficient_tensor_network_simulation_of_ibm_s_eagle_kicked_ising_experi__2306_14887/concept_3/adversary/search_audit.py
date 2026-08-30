"""Additional builder-only checks; never changes the frozen scenario suite."""

import json
import os
from pathlib import Path
import sys
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "champions" / "private_search"))
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from search import evaluate
from simulator import fidelities


def main():
    started = time.monotonic()
    generator = np.random.default_rng(680321)
    controls = generator.uniform(-2, 2, 48)
    scenarios = np.asarray([[0.011, -0.014] + [0.017] * 12,
                            [-0.022, 0.013] + [-0.012] * 12])
    scores, gradients = evaluate(controls, scenarios)
    gradient_error = 0.0
    for coordinate in (0, 1, 10, 17, 26, 35, 46, 47):
        direction = np.zeros(48)
        direction[coordinate] = 1e-6
        upper, _ = evaluate(controls + direction, scenarios)
        lower, _ = evaluate(controls - direction, scenarios)
        finite_difference = (upper - lower) / 2e-6
        gradient_error = max(gradient_error, float(np.max(np.abs(finite_difference - gradients[:, coordinate]))))
    public_rows = [{"gain_a": row[0], "gain_b": row[1], "zz_common": 0.0,
                    "zz_local": row[2:].tolist()} for row in scenarios]
    score_error = float(np.max(np.abs(scores - fidelities(controls.reshape(24, 2), public_rows))))
    witness = np.asarray(json.loads((ROOT / "champions" / "builder_witness" / "pulses.json").read_text())["angles"])
    additional = []
    for index in range(256):
        corners = generator.choice([-1, 1], size=3) * [0.025, 0.025, 0.015]
        local = generator.choice([-0.005, 0.005], size=12)
        additional.append(np.r_[corners[:2], corners[2] + local])
    extra_scores, _ = evaluate(witness, additional)
    report = {"gradient_coordinates": 8, "gradient_scenarios": 2,
              "max_gradient_absolute_error": gradient_error,
              "max_adjoint_public_fidelity_error": score_error,
              "additional_boundary_disorder_scenarios": len(additional),
              "additional_min_fidelity": float(extra_scores.min()),
              "additional_mean_fidelity": float(extra_scores.mean()),
              "elapsed_seconds": time.monotonic() - started,
              "passed": gradient_error < 1e-7 and score_error < 1e-11,
              "continuum_certificate": False}
    (ROOT / "adversary" / "search_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
