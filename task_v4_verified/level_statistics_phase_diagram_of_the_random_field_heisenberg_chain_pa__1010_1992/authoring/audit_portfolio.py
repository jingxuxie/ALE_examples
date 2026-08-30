import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1] / "concept_2"
sys.path.insert(0, str(ROOT / "evaluator"))
import check
from physics import observables


def main():
    spec = json.loads((ROOT / "evaluator/hidden/spec.json").read_text())
    seeds = json.loads((ROOT / "evaluator/hidden/seeds.json").read_text())["seeds"]
    design = json.loads((ROOT / "adversary/portfolio_candidate/design.json").read_text())
    original = json.loads((ROOT / "adversary/portfolio_score.json").read_text())
    check.observables = lambda fields: observables(fields, driver="evd")
    started = time.monotonic()
    alternate = check.evaluate_design(design, spec, seeds)
    assert alternate["passed"] and original["passed"]
    errors = []
    for reference_family, alternate_family in zip(original["families"], alternate["families"]):
        for reference, sample in zip(reference_family["records"], alternate_family["records"]):
            errors.extend(abs(reference[key] - sample[key]) for key in ("r_high", "r_low", "f_high", "f_low"))
    assert max(errors) < 1e-9
    result = {"passed": True, "alternate_driver": "evd full spectrum", "original_driver": "evr subset",
              "core_score": alternate["core_score"], "worst_family_score": alternate["worst_family_score"],
              "maximum_observable_difference": max(errors), "compared_observables": len(errors),
              "seconds": time.monotonic() - started}
    (ROOT / "adversary/portfolio_independent_driver.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
