"""Grade only a static witness.json; never execute submission code."""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path


os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from problem import FAMILIES, Kernel, load_witness
from reference import verify
from target import integrate


def evaluate(submission_dir):
    started = time.monotonic()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
              "resource_score": 0.0, "runtime/resource_score": 0.0, "passed": False,
              "valid": False, "reason": "not evaluated"}
    try:
        witness = load_witness(Path(submission_dir) / "witness.json")
        with open(ROOT / "evaluator/hidden/frozen_manifest.json", encoding="utf-8") as stream:
            manifest = json.load(stream)
        for relative, expected in manifest.items():
            if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError("frozen asset integrity failure: " + relative)
        kernel = Kernel()
        targets = [integrate(kernel.integrand(witness, family), trace=True) for family in FAMILIES]
        reference = verify(witness)
        families = {}
        scores = []
        for channel, family in enumerate(FAMILIES):
            target = targets[channel]
            audit = reference["channels"][channel]
            value = float(audit["reference_value"])
            source_error = abs(target["value"] - value)
            frozen_error = abs(target["value"] - reference["frozen_fine"][channel])
            conservative_error = max(0.0, min(source_error, frozen_error) - float(audit["uncertainty_allowance"]))
            threshold = max(20 * target["tolerance"], 50 * target["estimated_error"],
                            1e-5 * float(audit["reference_l1_guard"]))
            margin = conservative_error / threshold
            qualifies = bool(audit["resolved"] and target["converged"] and margin >= 1)
            score = min(1.0, margin) if audit["resolved"] and target["converged"] else 0.0
            scores.append(score)
            families[family] = {"score": score, "passed": qualifies, "margin": margin,
                                "source_error": source_error, "frozen_error": frozen_error,
                                "conservative_quadrature_error": conservative_error,
                                "required_error": threshold, "target": target, "audit": audit}
        report.update({"valid": True, "passed": all(item["passed"] for item in families.values()),
                       "core_score": math.fsum(scores) / len(scores), "worst_family_score": min(scores),
                       "runtime_score": 1.0, "resource_score": 1.0, "runtime/resource_score": 1.0,
                       "families": families, "reference": reference})
        if report["passed"]:
            report["reason"] = "All three color moments materially falsify the frozen quadrature estimates; source/frozen integrands agree."
        elif not all(audit["resolved"] for audit in reference["channels"]):
            report["reason"] = "Reference convergence or frozen/source agreement gate failed; no quadrature claim accepted."
        else:
            report["reason"] = "Valid witness, but at least one color moment does not meet the fixed falsification condition."
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, OverflowError) as error:
        report["reason"] = str(error)
    report["runtime_seconds"] = time.monotonic() - started
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission_dir")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = evaluate(args.submission_dir)
    destination = Path(args.report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("core_score", "worst_family_score", "runtime_score", "resource_score", "passed", "valid", "reason")}))


if __name__ == "__main__":
    main()
