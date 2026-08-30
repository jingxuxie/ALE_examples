import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
STAGE = ROOT / "generations/generation_3"
sys.path.insert(0, str(STAGE / "evaluator/hidden"))

from search_api import PROTOCOL, assess_member, family, parse_submission
from simulator import field_distance, independent, integrate, observable_distance


def main():
    started = time.monotonic()
    evidence = json.loads((STAGE / "evaluator/hidden/ratchet_evidence.json").read_text())
    anchor = max(evidence["fully_referenced_failures"], key=lambda item: item["assessment"]["certificate"])
    base = parse_submission((ROOT / "champions/generation_2/submission.json").read_text())
    descriptor = next(member for member in PROTOCOL["family"] if member.get("coordinates") == anchor["coordinates"])
    transformed = dict(family(base))[descriptor["name"]]
    comparison = integrate(transformed, 256, 4096)
    refined = integrate(transformed, 320, 8192)
    independent_state, evaluations = independent(transformed, 256, tolerance=2e-12)
    deltas = {
        "320_mode_8192_step_field_delta": float(np.max(field_distance(comparison, refined))),
        "320_mode_8192_step_observable_delta": float(np.max(observable_distance(comparison, refined))),
        "256_mode_tighter_DOP853_field_delta": float(np.max(field_distance(comparison, independent_state))),
        "256_mode_tighter_DOP853_observable_delta": float(np.max(observable_distance(comparison, independent_state))),
    }
    uncertainty = anchor["assessment"]["reference"]
    assert max(value for name, value in deltas.items() if name.endswith("field_delta")) <= uncertainty["field_uncertainty"]
    assert max(value for name, value in deltas.items() if name.endswith("observable_delta")) <= uncertainty["observable_uncertainty"]
    nearby = []
    for scale in (0.99, 1.01):
        changed = dict(transformed)
        name = evidence["selected_factor"]
        sign = anchor["coordinates"][-1]
        width = evidence["selected_width"]
        changed[name] = base[name] + sign * width * scale if evidence["operation"] == "add" else base[name] * (1 + sign * width * scale)
        report = assess_member(changed)
        nearby.append({"uncertainty_width_scale": scale, "assessment": report})
    previous = json.loads((ROOT / "champions/generation_2/evaluation.json").read_text())
    old_descriptor = next(member for member in PROTOCOL["family"][:37] if member.get("coordinates") == anchor["coordinates"][:5])
    previous_report = next(member for member in previous["family"] if member["name"] == old_descriptor["name"])
    assert previous_report["passed"]
    result = {
        "anchor_member": descriptor,
        "anchor_assessment": anchor["assessment"],
        "same_five_coordinates_without_sixth_factor": previous_report,
        "additional_refinement": deltas,
        "additional_independent_rhs_evaluations": evaluations,
        "extra_reference_checks_fit_recorded_uncertainty": True,
        "nearby_factor_checks": nearby,
        "nearby_failures_resolved": all(item["assessment"]["reference"]["resolved"] and not item["assessment"]["passed"] for item in nearby),
        "runtime_seconds": time.monotonic() - started,
    }
    (AUDIT / "anchor_validation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({name: value for name, value in result.items() if name not in ("anchor_assessment", "same_five_coordinates_without_sixth_factor", "nearby_factor_checks")}), flush=True)


if __name__ == "__main__":
    main()
