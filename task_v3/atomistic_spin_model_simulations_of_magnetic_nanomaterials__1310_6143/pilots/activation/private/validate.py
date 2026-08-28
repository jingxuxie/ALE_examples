import hashlib
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from evaluator import calibrated_score, physical_loss, weak_result
from numerics import diagnostics


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private"


def main():
    answers = PRIVATE / "strong_submission" / "answers"
    answers.mkdir(exist_ok=True)
    validations = []
    sensitivity = []
    ablations = []
    for path in sorted(PRIVATE.glob("**/validation.json")):
        case = json.loads((path.parent / "case.json").read_text())
        reference = json.loads((path.parent / "solution.json").read_text())
        validation = json.loads(path.read_text())
        validations.append(validation)
        shutil.copyfile(path.parent / "solution.json", answers / (case["case_id"] + ".json"))
        strong_loss, _ = physical_loss(case, reference, reference)
        weak_loss, _ = physical_loss(case, weak_result(case), reference)
        scores = [calibrated_score(loss, weak_loss, strong_loss, 0, 1)[0] for loss in [weak_loss * 2, weak_loss, (weak_loss + strong_loss) / 2, strong_loss, strong_loss - 0.1]]
        assert all(lower < upper for lower, upper in zip(scores, scores[1:])), scores
        assert abs(scores[1] - 0.5) < 1e-12
        assert abs(scores[3] - 0.9375) < 1e-12
        sensitivity.append({"case_id": case["case_id"], "monotonic_scores_worse_weak_intermediate_strong_better": scores})
        saddle_only = copy.deepcopy(reference)
        placeholder = weak_result(case)
        for key in ['eigenvalues_min_meV', 'eigenvalues_saddle_meV', 'log_omega0']:
            saddle_only[key] = placeholder[key]
        spectrum_only = copy.deepcopy(reference)
        spectrum_only['saddle'] = case['minimum_a']
        spectrum_only['barrier_meV'] = 0.0
        minimum = diagnostics(case, np.asarray(case['minimum_a']))
        spectrum_only['eigenvalues_saddle_meV'] = minimum['eigenvalues']
        row = dict(case_id=case['case_id'], strong=scores[3], weak=scores[1])
        for name, result in [('saddle_only', saddle_only), ('spectrum_only', spectrum_only)]:
            loss, checks = physical_loss(case, result, reference)
            row[name] = calibrated_score(loss, weak_loss, strong_loss, 0, 1)[0]
            assert row[name] < 0.70, row
        ablations.append(row)
    (PRIVATE / "scoring_sensitivity.json").write_text(json.dumps(sensitivity, indent=2) + "\n")
    (PRIVATE / "scoring_ablations.json").write_text(json.dumps(ablations, indent=2) + "\n")
    for split in ["initial", "challenge"]:
        for submission, basename in [("weak_submission", "baseline_scores"), ("strong_submission", "strong_reference_scores")]:
            output = PRIVATE / (basename + ("" if split == "initial" else "_challenge") + ".json")
            command = [sys.executable, str(PRIVATE / "evaluator.py"), "--submission", str(PRIVATE / submission), "--output", str(output), "--split", split]
            subprocess.run(command, check=True)
            scores = json.loads(output.read_text())
            assert all(case["status"] == "ok" for case in scores["cases"]), scores
            if submission == "strong_submission":
                assert min(case["score"] for case in scores["cases"]) > 0.9, scores
            print(basename, split, scores["score"], flush=True)
    source = ROOT.parents[1] / "authoring" / "spirit"
    source_hashes = {}
    for relative in ["core/src/engine/Method_GNEB.cpp", "core/src/engine/HTST.cpp", "core/src/engine/Hamiltonian_Heisenberg.cpp", "core/python/spirit/libSpirit.so"]:
        source_hashes[relative] = hashlib.sha256((source / relative).read_bytes()).hexdigest()
    pilot_hashes = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.suffix in {".py", ".md", ".json", ".cfg"} and "vendor" not in path.parts and "runs" not in path.parts and path.name != "provenance.json":
            pilot_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary = {"source_revision": subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(), "source_sha256": source_hashes, "pilot_sha256": pilot_hashes, "native_reference_cases": len(validations), "max_native_spectrum_error_meV": max(record["independent_spectrum_max_error_meV"] for record in validations), "max_native_barrier_error_meV": max(record["independent_native_barrier_error_meV"] for record in validations), "max_saddle_residual_meV": max(record["saddle_residual_meV"] for record in validations), "max_finite_difference_hessian_error_meV": max(record["finite_difference_hessian_max_error_meV"] for record in validations), "max_log_omega0_error": max(record["independent_log_omega0_error"] for record in validations), "confirmation_generated": False, "model_attempts_launched": 0}
    (PRIVATE / "provenance.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({name: value for name, value in summary.items() if not isinstance(value, dict)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
