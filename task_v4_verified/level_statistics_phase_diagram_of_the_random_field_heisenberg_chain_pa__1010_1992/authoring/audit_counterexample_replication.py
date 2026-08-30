import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1] / "concept_3/generations/generation_2"
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
import exact


def main():
    witness = json.loads((ROOT / "adversary/scale_candidate/witness.json").read_text())
    protocol = json.loads((ROOT / "evaluator/hidden/protocol.json").read_text())
    official = json.loads((ROOT / "adversary/privileged_score.json").read_text())
    started = time.monotonic()
    original = exact.assess(witness, protocol, driver="evr")
    alternate = exact.assess(witness, protocol, driver="evd")
    differences = []
    for reference, candidate in zip([original["base"]] + original["members"],
                                    [alternate["base"]] + alternate["members"]):
        differences.extend(abs(reference[key] - candidate[key])
                           for key in ("rank_r", "proxy_r", "difference"))
    assert official["passed"] and original["pass"] and alternate["pass"]
    assert abs(official["core_score"] - original["core"]) < 1e-12
    assert max(differences) < 1e-9
    report = {"passed": True, "original_driver": "evr", "alternate_driver": "evd",
              "compared_observables": len(differences),
              "maximum_observable_difference": max(differences),
              "core_score": alternate["core"], "worst_family_score": alternate["worst_family"],
              "seconds": time.monotonic() - started}
    (ROOT / "adversary/privileged_independent_driver.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
