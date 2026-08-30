import hashlib
import json
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/workspace"))

import numpy as np

from descriptors import feature_matrix
from physics import hamiltonian, observables, sector


def independent_hamiltonian(fields):
    length = len(fields)
    dimension = 2 ** length
    basis = [state for state in range(dimension) if bin(state).count("1") == length // 2]
    full = np.zeros((dimension, dimension))
    for state in range(dimension):
        spins = [0.5 if state & (1 << site) else -0.5 for site in range(length)]
        full[state, state] = sum(field * spin for field, spin in zip(fields, spins))
        for site in range(length):
            neighbour = (site + 1) % length
            full[state, state] += spins[site] * spins[neighbour]
            if spins[site] != spins[neighbour]:
                flipped = state ^ (1 << site) ^ (1 << neighbour)
                full[flipped, state] += 0.5
    return full[np.ix_(basis, basis)]


def main():
    training = [json.loads(line) for line in (ROOT / "participant/input/train.jsonl").read_text().splitlines()]
    report = {"checks": {}, "ed_timing_seconds": {}, "subset_full_differences": {}, "invariance_max_errors": {}}
    public_physics = (ROOT / "participant/workspace/physics.py").read_bytes()
    private_physics = (ROOT / "evaluator/physics.py").read_bytes()
    assert public_physics == private_physics
    report["checks"]["frozen_physics_identical"] = hashlib.sha256(private_physics).hexdigest()
    small_fields = [0.17, -0.89, 1.27, -0.31]
    np.testing.assert_allclose(hamiltonian(small_fields), independent_hamiltonian(small_fields), atol=1e-14)
    report["checks"]["independent_periodic_hamiltonian"] = "passed"
    selected = [next(case for case in training if case["L"] == length and case["family"] == family)
                for length in (10, 12) for family in ("iid_uniform", "ordered_blocks", "alternating_correlated", "shuffled_pairs")]
    for case in selected:
        fields = np.asarray(case["fields"])
        key = case["family"] + "/L" + str(case["L"])
        started = time.monotonic()
        reference = observables(fields)["f"]
        report["ed_timing_seconds"][key] = time.monotonic() - started
        np.testing.assert_allclose(reference, case["f"], atol=2e-11, rtol=0)
        full = observables(fields, full=True, driver="evd")
        report["subset_full_differences"][key] = abs(reference - full["f"])
        np.testing.assert_allclose(reference, full["f"], atol=2e-10, rtol=0)
        variants = (np.roll(fields, 3), fields[::-1], -fields, fields + 1.234)
        errors = [abs(observables(variant)["f"] - reference) for variant in variants]
        report["invariance_max_errors"][key] = max(errors)
        assert max(errors) < 2e-10
        descriptors = feature_matrix([{"fields": fields}] + [{"fields": variant} for variant in variants])
        np.testing.assert_allclose(descriptors[1:], np.broadcast_to(descriptors[0], descriptors[1:].shape),
                                   atol=1e-10, rtol=1e-10)
    report["checks"]["target_and_descriptor_symmetries"] = "translation, reflection, spin reversal, uniform field shift"
    report["checks"]["stored_labels_recomputed"] = len(selected)
    report["checks"]["central_subset_vs_full_evd"] = "passed at both lengths, all four families"
    report["checks"]["central_rank_counts"] = {str(length): len(sector(length)[0]) // 3 for length in (10, 12)}
    for length in (10, 12):
        timings = [value for key, value in report["ed_timing_seconds"].items() if key.endswith("L" + str(length))]
        report[f"median_L{length}_ed_seconds"] = float(np.median(timings))
    report["estimated_full_ed_320_serial_seconds"] = 160 * (report["median_L10_ed_seconds"] + report["median_L12_ed_seconds"])
    path = ROOT / "participant/input/physics_checks.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
