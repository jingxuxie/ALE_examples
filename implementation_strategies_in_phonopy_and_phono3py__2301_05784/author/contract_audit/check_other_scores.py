"""Rescore stored author controls and check flat-grid data; no runtime claims."""

import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import numpy as np

from score_fitting_ablations import digest, load_arrays


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent


def main():
    report = {"scope": "Trusted direct score_case author controls only; no participant execution or source rebuild.", "concepts": {}}
    for concept in ("polar", "cubic", "grid"):
        private = ROOT / "concepts" / concept / "private"
        specification = importlib.util.spec_from_file_location(f"audit_{concept}", private / "evaluator.py")
        evaluator = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(evaluator)
        manifest = json.loads((private / "challenge_pool/manifest.json").read_text())
        cases = manifest if isinstance(manifest, list) else manifest["cases"]
        result = {"cases": [], "evaluator_sha256": digest(private / "evaluator.py"), "manifest_sha256": digest(private / "challenge_pool/manifest.json")}
        for case in cases:
            inputs = load_arrays(private / case["input"])
            reference = load_arrays(private / case["reference"])
            baseline = load_arrays(private / case["baseline"])
            variants = {"stored_weak": baseline, "stored_reference": reference}
            if concept != "grid":
                variants["zero_outputs"] = {name: np.zeros_like(values) for name, values in reference.items()}
            else:
                query_count = len(inputs["query_addresses"])
                spectral_shape = (len(inputs["sampling_points"]), inputs["frequencies"].shape[1])
                variants["zero_shift_zero_spectra"] = {
                    "image_offsets": np.arange(query_count + 1, dtype=np.int64),
                    "image_shifts": np.zeros((query_count, 3), dtype=np.int64),
                    "distance2": np.zeros(query_count, dtype=np.float64),
                    "dos": np.zeros(spectral_shape, dtype=np.float64),
                    "cumulative": np.zeros(spectral_shape, dtype=np.float64),
                }
            for variant, actual in variants.items():
                components = evaluator.score_case(actual, reference, baseline, case, inputs)
                if concept == "cubic":
                    components = {name: {"score": score, "error": evaluator.component_error(actual[name], reference[name]), "baseline_error": evaluator.component_error(baseline[name], reference[name])} for name, score in components.items()}
                result["cases"].append({"id": case["id"], "family": case["family"], "split": case["split"], "variant": variant, "components": components, "core_score": float(np.mean([value["score"] for value in components.values()]))})
            if concept == "grid":
                threshold_gap = float(np.min(np.abs(inputs["sampling_points"][:, None] - np.unique(inputs["frequencies"])[None, :])))
                flat = np.ptp(inputs["frequencies"], axis=0) == 0
                check = {"id": case["id"], "minimum_threshold_frequency_gap": threshold_gap, "flat_branch_count": int(flat.sum())}
                if flat.any():
                    expected = (inputs["sampling_points"][:, None] >= inputs["frequencies"][0, flat][None, :]).astype(np.float64)
                    check["flat_cumulative_max_abs_error"] = float(np.max(np.abs(reference["cumulative"][:, flat] - expected)))
                    check["flat_dos_max_abs"] = float(np.max(np.abs(reference["dos"][:, flat])))
                result.setdefault("flat_checks", []).append(check)
        result["summaries"] = {}
        for variant in variants:
            records = [record for record in result["cases"] if record["variant"] == variant]
            families = {family: float(np.mean([record["core_score"] for record in records if record["family"] == family])) for family in {record["family"] for record in records}}
            result["summaries"][variant] = {"mean_core": float(np.mean([record["core_score"] for record in records])), "family_balanced_core": float(np.mean(list(families.values()))), "worst_family": min(families.values()), "min_case": min(record["core_score"] for record in records), "max_case": max(record["core_score"] for record in records)}
        report["concepts"][concept] = result
        print(concept, json.dumps(result["summaries"]), flush=True)
    (OUTPUT / "other_scores.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
