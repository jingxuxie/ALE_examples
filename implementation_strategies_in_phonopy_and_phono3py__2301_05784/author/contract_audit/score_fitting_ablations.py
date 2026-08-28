"""Trusted scoring audit, not a participant solver or runtime benchmark."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
PRIVATE = ROOT / "concepts/fitting/private"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def summarize(records):
    family_scores = {}
    family_components = {}
    for family in sorted({record["family"] for record in records}):
        members = [record for record in records if record["family"] == family]
        family_scores[family] = float(np.mean([record["core_score"] for record in members]))
        family_components[family] = {
            key: float(np.mean([record["components"][key]["score"] for record in members]))
            for key in ("fc2", "fc3")
        }
    return {
        "mean_core": float(np.mean([record["core_score"] for record in records])),
        "worst_case": min(record["core_score"] for record in records),
        "family_scores": family_scores,
        "family_component_scores": family_components,
        "worst_family": min(family_scores.values()),
        "worst_family_component": min(value for scores in family_components.values() for value in scores.values()),
    }


def main():
    watched = []
    for concept in ("fitting", "polar", "cubic", "grid"):
        for suffix in ("participant/TASK.md", "participant/workspace/CONTRACT.md", "private/evaluator.py", "private/challenge_pool/manifest.json"):
            watched.append(ROOT / "concepts" / concept / suffix)
    watched.extend([PRIVATE / "reference/physics.py", ROOT / "author/evaluation.py", ROOT / "author/score_submission.py"])
    before = {str(path.relative_to(ROOT)): digest(path) for path in watched}
    (OUTPUT / "source_hashes_before.json").write_text(json.dumps(before, indent=2) + "\n")
    specification = importlib.util.spec_from_file_location("contract_audit_fitting_evaluator", PRIVATE / "evaluator.py")
    evaluator = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = evaluator
    specification.loader.exec_module(evaluator)
    cases = json.loads((PRIVATE / "challenge_pool/manifest.json").read_text())
    report = {
        "scope": "Trusted direct score_case scoring audit only; no model attempt, bwrap, runtime validation, source rebuild, or evaluation-scale change.",
        "variants": {
            "zero_tensors": "Generic shortcut: both tensors zero, shapes derived only from input.",
            "reference_fc2_zero_fc3": "PRIVILEGED harmonic-only ablation: hidden reference fc2, zero fc3; NOT a generic solver.",
            "stored_weak": "Previously measured weak output, rescored by the current scientific evaluator.",
            "stored_reference": "Stored constrained reference tensors, rescored against original heldout forces; NOT runtime evidence.",
        },
        "source_hashes_before": before,
        "cases": [],
    }
    for case in cases:
        input_path = PRIVATE / case["input"]
        reference_path = PRIVATE / case["reference"]
        baseline_path = PRIVATE / case["baseline"]
        inputs = load_arrays(input_path)
        reference = load_arrays(reference_path)
        baseline = load_arrays(baseline_path)
        primitive_count = len(inputs["p2s2"])
        shapes = {
            "fc2": (primitive_count, len(inputs["numbers2"]), 3, 3),
            "fc3": (primitive_count, len(inputs["numbers3"]), len(inputs["numbers3"]), 3, 3, 3),
        }
        zero = {name: np.zeros(shape, dtype=np.float64) for name, shape in shapes.items()}
        variants = {
            "zero_tensors": zero,
            "reference_fc2_zero_fc3": {"fc2": reference["fc2"], "fc3": zero["fc3"]},
            "stored_weak": baseline,
            "stored_reference": {name: reference[name] for name in ("fc2", "fc3")},
        }
        force_rms = {
            f"heldout_f{order}_rms": float(np.sqrt(np.mean(reference[f"heldout_f{order}"] ** 2))) if len(reference[f"heldout_f{order}"]) else None
            for order in (2, 3)
        }
        for variant, actual in variants.items():
            artifact = None
            if variant in ("zero_tensors", "reference_fc2_zero_fc3"):
                directory = OUTPUT / "outputs" / variant / case["id"]
                directory.mkdir(parents=True, exist_ok=True)
                artifact_path = directory / "result.npz"
                np.savez_compressed(artifact_path, **actual)
                actual = load_arrays(artifact_path)
                artifact = str(artifact_path.relative_to(ROOT))
            started = time.perf_counter()
            components = evaluator.score_case(actual, reference, baseline, case, inputs)
            record = {
                "id": case["id"], "family": case["family"], "split": case["split"],
                "fit_mode": int(inputs["fit_mode"]), "variant": variant,
                "core_score": float(np.mean([value["score"] for value in components.values()])),
                "components": components, "force_rms": force_rms,
                "baseline_metrics_cached": case.get("baseline_metrics"),
                "artifact": artifact, "scoring_seconds_not_solver_runtime": time.perf_counter() - started,
                "source_files": {name: {"path": str(path.relative_to(ROOT)), "sha256": digest(path)} for name, path in (("input", input_path), ("reference", reference_path), ("baseline", baseline_path))},
            }
            report["cases"].append(record)
            (OUTPUT / "fitting_ablations.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
            print(case["id"], variant, f'{record["core_score"]:.12f}', flush=True)
    report["summaries"] = {variant: summarize([record for record in report["cases"] if record["variant"] == variant]) for variant in variants}
    report["source_hashes_after"] = {str(path.relative_to(ROOT)): digest(path) for path in watched}
    report["watched_sources_unchanged"] = before == report["source_hashes_after"]
    (OUTPUT / "fitting_ablations.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["summaries"], indent=2), flush=True)


if __name__ == "__main__":
    main()
