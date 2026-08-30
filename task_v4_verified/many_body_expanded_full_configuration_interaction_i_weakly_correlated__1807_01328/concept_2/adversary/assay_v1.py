import collections
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "adversary"


def main():
    started = time.perf_counter()
    score_path = ROOT / "attempts/v_1.score.json"
    witness_path = ROOT / "attempts/v_1/witness.json"
    main_score = json.loads(score_path.read_text())
    if main_score.get("passed") is not True or main_score.get("valid") is not True:
        raise RuntimeError("main has not independently accepted v1")
    specification = importlib.util.spec_from_file_location("private_robustness_helpers", PRIVATE / "robustness_study.py")
    helpers = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(helpers)
    verifier = helpers.module_at("original_trusted_verifier", "evaluator/hidden/verify.py")
    witness_bytes = witness_path.read_bytes()
    witness_hash = hashlib.sha256(witness_bytes).hexdigest()
    witness = json.loads(witness_bytes)
    center = np.array([[witness[field][row][column] for row, column in helpers.EDGES] for field in helpers.FIELDS])
    bounds = np.array([[verifier.TARGET["hopping_bound_eh"]], [verifier.TARGET["density_bound_eh"]]])
    report = dict(source_artifact="attempts/v_1/witness.json", source_sha256=witness_hash, nominal_source="attempts/v_1.score.json", nominal_report_sha256=helpers.digest(score_path), nominal_report_from_main=main_score, nominal_evaluator_rerun=False, distribution="Independent uniform per upper-triangle coefficient in intersection of [theta-delta,theta+delta] and its original box; mirror exactly; always centered on final v1", seed=314159265, groups=[])
    with tempfile.TemporaryDirectory(prefix=".v1-assay-", dir=PRIVATE) as directory:
        scratch = Path(directory) / "witness.json"
        for magnitude_index, magnitude in enumerate((1e-6, 1e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2)):
            records = []
            count = 128 if magnitude == 1e-3 else 32
            for sample_index in range(count):
                generator = np.random.default_rng(np.random.SeedSequence([report["seed"], magnitude_index, sample_index]))
                values = helpers.perturbed(center, bounds, magnitude, "box_conditioned_uniform", generator)
                record = helpers.evaluate(values, center, bounds, scratch, verifier)
                record["sample_index"] = sample_index
                records.append(record)
            summary = helpers.summarize(records, True)
            summary["failure_clusters"] = dict(collections.Counter(" + ".join(sorted(record["failures"])) or "pass" for record in records))
            gate_passes = sum(not any(failure.startswith("witness_checks.") for failure in record["failures"]) for record in records)
            summary["gate_passes"] = gate_passes
            summary["gate_pass_wilson_95"] = helpers.wilson_interval(gate_passes, count)
            report["groups"].append(dict(delta_eh=magnitude, summary=summary, samples=records))
            print(json.dumps(dict(delta_eh=magnitude, passed=summary["passed_count"], count=count, failure_clusters=summary["failure_clusters"])), flush=True)
    proposed = next(group for group in report["groups"] if group["delta_eh"] == 1e-3)
    report["ratchet_condition_met"] = proposed["summary"]["gate_pass_wilson_95"][1] < 0.95 and proposed["summary"]["wilson_95_pass_interval"][1] < 0.95
    report["conditional_build_rule"] = "Main nominal passed=true AND the 128-case delta=0.001 assay's upper Wilson 95% limits for witness and gate success are both below 0.95. No nominal thresholds are changed."
    report["runtime_seconds"] = time.perf_counter() - started
    report["artifact_unchanged"] = witness_path.read_bytes() == witness_bytes
    assert report["artifact_unchanged"]
    (PRIVATE / "v1_perturbation_assay.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(dict(ratchet_condition_met=report["ratchet_condition_met"], runtime_seconds=report["runtime_seconds"], nominal_evaluator_rerun=False)), flush=True)


if __name__ == "__main__":
    main()
