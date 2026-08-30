"""Bounded private within-law adversary search against an immutable snapshot."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import solve_triangular

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
sys.path.insert(0, str(ROOT / "evaluator"))
from physics import FAMILY_NAMES, QUANTILE_LEVELS, kernel, observables, wasserstein
from runtime import ExecutionError, execute_submission
from scoring import score_prediction


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def snapshot():
    source = ROOT / "attempts/v_1"
    destination = HERE / "snapshot"
    if destination.exists():
        raise ValueError("refusing to replace the candidate snapshot")
    sources = sorted(source.glob("*.py")) + [source / "pool.npz"]
    before = {path.name: digest(path) for path in sources}
    destination.mkdir()
    for path in sources:
        shutil.copyfile(path, destination / path.name)
    after = {path.name: digest(path) for path in sources}
    copied = {path.name: digest(destination / path.name) for path in sources}
    if before != after or before != copied:
        raise ValueError("candidate changed during snapshot; this directory must not be evaluated")
    record = {
        "date": "2026-08-28",
        "source": "attempts/v_1 (active candidate, not necessarily final)",
        "sha256": copied,
        "official_pass_confirmed_by_sidecar": False,
        "eligibility": "provisional; parent must confirm official pass and retest final code",
        "public_assets_sha256": {
            str(path.relative_to(ROOT / "participant")): digest(path)
            for path in sorted((ROOT / "participant").rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        },
        "frozen_target_sha256": digest(ROOT / "evaluator/hidden/target_freeze.json"),
        "fixed_split_manifest_sha256": digest(ROOT / "evaluator/hidden/split_manifest.json"),
    }
    write_json(HERE / "snapshot_manifest.json", record)
    return record


class RecordingRandom:
    def __init__(self, random):
        self.random = random
        self.draws = []

    def __getattr__(self, name):
        function = getattr(self.random, name)

        def recorded(*arguments, **keywords):
            value = function(*arguments, **keywords)
            self.draws.append({"operation": name, "value": np.asarray(value).tolist()})
            return value

        return recorded


def generate_batch(index, per_family=16):
    directory = HERE / "data" / f"seed_{index:02d}"
    location = directory / "participant/input"
    location.mkdir(parents=True, exist_ok=True)
    specification = importlib.util.spec_from_file_location("private_generator", ROOT / "evaluator/hidden/generate.py")
    generator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(generator)
    generator.ROOT = directory
    original_spectrum = generator.spectrum
    recorded = []

    def recording_spectrum(random, family):
        tracer = RecordingRandom(random)
        mass, basis = original_spectrum(tracer, family)
        recorded.append({"family_id": int(family), "component_count": int(basis.shape[1]), "draws": tracer.draws})
        return mass, basis

    generator.spectrum = recording_spectrum
    seed = int(np.random.SeedSequence([20260828, 871092, index]).generate_state(1, dtype=np.uint64)[0])
    manifest = generator.make_split("challenge", per_family, seed)
    permutation = np.random.default_rng(np.random.SeedSequence(seed).spawn(4)[2]).permutation(6 * per_family)
    ordered = [recorded[position] for position in permutation]
    write_json(directory / "parameters.json", ordered)
    manifest.update({
        "seed_index": index,
        "phase": "discovery" if index < 4 else "confirmation",
        "selection": "unconditional exact public generator law; 16 independent draws per family",
        "generator_sha256": digest(ROOT / "evaluator/hidden/generate.py"),
        "official_fixed_split_used": False,
    })
    write_json(directory / "manifest.json", manifest)
    return location / "challenge_input.npz", location / "challenge_labels.npz", ordered


def row_statistics(prediction, inputs, labels, parameters):
    mass = prediction["spectral_mass"]
    mass = mass / mass.sum(axis=1, keepdims=True)
    truth = labels["spectral_mass"]
    actual = observables(truth, inputs["omega_edges"])
    predicted = observables(mass, inputs["omega_edges"])
    normalized_w1 = wasserstein(mass, truth, inputs["omega_edges"]) / 16.0
    low_error = np.abs(predicted["low_mass"] - actual["low_mass"])
    band_error = np.abs(predicted["band_weights"] - actual["band_weights"]).sum(axis=1) / 2.0
    gap_error = np.abs(predicted["gap10"] - actual["gap10"])
    residual = actual["low_mass"][:, None] - prediction["low_mass_quantiles"]
    pinball = np.maximum(QUANTILE_LEVELS * residual, (QUANTILE_LEVELS - 1.0) * residual).mean(axis=1)
    losses = 0.45 * normalized_w1 / 0.02 + 0.20 * low_error / 0.06 + 0.15 * band_error / 0.1 + 0.1 * gap_error / 0.4 + 0.1 * pinball / 0.02
    rows = []
    for index, beta in enumerate(inputs["beta"]):
        response = kernel(beta, inputs["tau"][index], inputs["omega_edges"])
        chol = np.linalg.cholesky(inputs["covariance"][index])
        fit_residual = solve_triangular(chol, response @ mass[index] - inputs["correlation"][index], lower=True)
        truth_residual = solve_triangular(chol, response @ truth[index] - inputs["correlation"][index], lower=True)
        descriptor = parameters[index]
        family = int(labels["family_id"][index])
        assert family == descriptor["family_id"]
        peak_width = descriptor["draws"][1]["value"] if family == 0 else (descriptor["draws"][6]["value"] if family == 1 else None)
        rows.append({
            "sample_id": int(inputs["sample_id"][index]),
            "family_id": family,
            "family": FAMILY_NAMES[family],
            "beta": float(beta),
            "noise_rms": float(np.sqrt(np.trace(inputs["covariance"][index]) / 56.0)),
            "component_count": descriptor["component_count"],
            "coherent_width": peak_width,
            "true_low_mass": float(actual["low_mass"][index]),
            "predicted_low_mass": float(predicted["low_mass"][index]),
            "high_energy_mass": float(actual["band_weights"][index, 0] + actual["band_weights"][index, -1]),
            "true_gap10": float(actual["gap10"][index]),
            "loss": float(losses[index]),
            "score": float(100.0 * np.exp(-losses[index])),
            "normalized_wasserstein": float(normalized_w1[index]),
            "low_mass_error": float(low_error[index]),
            "band_error": float(band_error[index]),
            "gap_error": float(gap_error[index]),
            "pinball": float(pinball[index]),
            "covered_80pct": bool(residual[index, 0] >= 0 and residual[index, 2] <= 0),
            "interval_width": float(prediction["low_mass_quantiles"][index, 2] - prediction["low_mass_quantiles"][index, 0]),
            "quantile_cdf_hits": (residual[index] <= 0).tolist(),
            "prediction_chi_squared": float(fit_residual @ fit_residual),
            "truth_chi_squared": float(truth_residual @ truth_residual),
        })
    return rows


GROUPS = {name: (lambda row, family=index: row["family_id"] == family) for index, name in enumerate(FAMILY_NAMES)}
GROUPS.update({
    "multiband_low_information": lambda row: row["family_id"] == 5 and row["beta"] <= 16.0 and row["noise_rms"] >= 2e-4,
    "multiband_four_or_five_components": lambda row: row["family_id"] == 5 and row["component_count"] >= 4,
    "multiband_high_energy_weight": lambda row: row["family_id"] == 5 and row["high_energy_mass"] >= 0.5,
    "narrow_coherent_peak": lambda row: row["family_id"] in (0, 1) and row["coherent_width"] <= 0.14,
    "hot_noisy_all_families": lambda row: row["beta"] <= 12.0 and row["noise_rms"] >= 3e-4,
})


def summarize(rows):
    if not rows:
        return {"count": 0}
    count = len(rows)
    loss = np.array([row["loss"] for row in rows])
    covered = np.mean([row["covered_80pct"] for row in rows])
    denominator = 1.0 + 1.96**2 / count
    center = (covered + 1.96**2 / (2.0 * count)) / denominator
    radius = 1.96 * np.sqrt(covered * (1.0 - covered) / count + 1.96**2 / (4.0 * count**2)) / denominator
    random = np.random.default_rng(730491)
    indices = random.integers(0, count, (2000, count))
    bootstraps = 100.0 * np.exp(-loss[indices].mean(axis=1))
    return {
        "count": count,
        "score": float(100.0 * np.exp(-loss.mean())),
        "score_bootstrap_95pct": np.quantile(bootstraps, [0.025, 0.975]).tolist(),
        "mean_loss": float(loss.mean()),
        "coverage_80pct": float(covered),
        "coverage_wilson_95pct": [float(max(0.0, center - radius)), float(min(1.0, center + radius))],
        "mean_interval_width": float(np.mean([row["interval_width"] for row in rows])),
        "quantile_empirical_cdf": np.mean([row["quantile_cdf_hits"] for row in rows], axis=0).tolist(),
        "normalized_wasserstein": float(np.mean([row["normalized_wasserstein"] for row in rows])),
        "low_mass_mae": float(np.mean([row["low_mass_error"] for row in rows])),
        "band_error": float(np.mean([row["band_error"] for row in rows])),
        "gap_error": float(np.mean([row["gap_error"] for row in rows])),
        "pinball": float(np.mean([row["pinball"] for row in rows])),
        "median_prediction_chi_squared": float(np.median([row["prediction_chi_squared"] for row in rows])),
        "large_error_but_data_consistent": sum(row["score"] < 80.0 and row["prediction_chi_squared"] < 90.0 for row in rows),
    }


def summaries(rows):
    return {name: summarize([row for row in rows if predicate(row)]) for name, predicate in GROUPS.items()}


def save_fixture(batches, selected_group):
    location = HERE / "confirmation_fixture"
    location.mkdir(exist_ok=True)
    parts = []
    for batch in batches:
        if batch["index"] < 4:
            continue
        mask = np.array([GROUPS[selected_group](row) for row in batch["rows"]])
        if not np.any(mask):
            continue
        parts.append((batch, mask))
    if not parts:
        return None
    for category in ("inputs", "labels", "prediction"):
        collection = {}
        for key in parts[0][0][category]:
            collection[key] = parts[0][0][category][key] if key == "omega_edges" else np.concatenate([batch[category][key][mask] for batch, mask in parts])
        filename = {"inputs": "input.npz", "labels": "labels.npz", "prediction": "snapshot_predictions.npz"}[category]
        np.savez_compressed(location / filename, **collection)
    parameters = [descriptor for batch, mask in parts for descriptor, selected in zip(batch["parameters"], mask) if selected]
    write_json(location / "parameters.json", parameters)
    record = {
        "selected_group": selected_group,
        "count": len(parameters),
        "selection": "physical group selected on discovery seeds only; all members of that group from untouched confirmation seeds retained",
        "not_official_test": True,
        "not_a_new_frozen_target": True,
        "requires_final_code_retest": True,
        "files_sha256": {path.name: digest(path) for path in sorted(location.iterdir()) if path.is_file()},
    }
    write_json(location / "manifest.json", record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--budget-seconds", type=float, default=600.0)
    arguments = parser.parse_args()
    if arguments.prepare_only:
        print(json.dumps(snapshot(), indent=2), flush=True)
        return
    snapshot_record = json.loads((HERE / "snapshot_manifest.json").read_text())
    for filename, expected in snapshot_record["sha256"].items():
        assert digest(HERE / "snapshot" / filename) == expected
    started = time.monotonic()
    batches = []
    discovery = []
    confirmation = []
    selected_group = None
    errors = []
    for index in range(8):
        if time.monotonic() - started > arguments.budget_seconds - 125.0:
            break
        input_path, label_path, parameters = generate_batch(index)
        try:
            prediction, resources = execute_submission(HERE / "snapshot", input_path, ROOT / "participant/input")
        except ExecutionError as error:
            errors.append({"seed_index": index, "reason": str(error), "details": error.details})
            write_json(HERE / "execution_errors.json", errors)
            break
        inputs = load(input_path)
        labels = load(label_path)
        scientific = score_prediction(prediction, inputs, labels)
        rows = row_statistics(prediction, inputs, labels, parameters)
        for row in rows:
            row["seed_index"] = index
        batch = {"index": index, "inputs": inputs, "labels": labels, "prediction": prediction, "parameters": parameters, "rows": rows}
        batches.append(batch)
        directory = HERE / "data" / f"seed_{index:02d}"
        np.savez_compressed(directory / "predictions.npz", **prediction)
        write_json(directory / "row_analysis.json", rows)
        write_json(directory / "report.json", {**scientific, **resources})
        (discovery if index < 4 else confirmation).extend(rows)
        print(json.dumps({"seed_index": index, "phase": "discovery" if index < 4 else "confirmation", "count": len(rows), "core_score": scientific["core_score"], "worst_family_score": scientific["worst_family_score"], "family_scores": scientific["family_scores"], "runtime_seconds": resources["runtime_seconds"]}), flush=True)
        if index == 3:
            groups = summaries(discovery)
            eligible = {name: group for name, group in groups.items() if group["count"] >= 16}
            selected_group = min(eligible, key=lambda name: eligible[name]["score"])
            write_json(HERE / "discovery_selection.json", {
                "selected_group": selected_group,
                "minimum_discovery_count": 16,
                "selection_rule": "lowest discovery score among predeclared physical groups with at least 16 cases",
                "confirmation_evaluated_yet": False,
                "groups": groups,
            })
            print("SELECTED_FOR_INDEPENDENT_CONFIRMATION " + selected_group, flush=True)
    combined = discovery + confirmation
    report = {
        "provisional_active_candidate_snapshot": True,
        "official_pass_confirmed_by_sidecar": False,
        "scope": "exact unchanged public spectral and observation law; no distribution extension",
        "elapsed_seconds": time.monotonic() - started,
        "completed_batches": len(batches),
        "tested_cases": len(combined),
        "discovery_cases": len(discovery),
        "confirmation_cases": len(confirmation),
        "errors": errors,
        "aggregate": summarize(combined),
        "discovery_groups": summaries(discovery),
        "confirmation_groups": summaries(confirmation),
        "selected_group": selected_group,
        "selected_group_confirmation": summarize([row for row in confirmation if GROUPS[selected_group](row)]) if selected_group else None,
        "confirmation_fixture": save_fixture(batches, selected_group) if selected_group else None,
        "interpretation_constraints": "A selected conditional stress group is not a replacement for the balanced frozen test. Confirmation is independent of discovery. Oracle/latent labels were never mounted into the predictor. Parent must retest final code and owns ratcheting.",
    }
    for relative, expected in snapshot_record["public_assets_sha256"].items():
        assert digest(ROOT / "participant" / relative) == expected
    assert digest(ROOT / "evaluator/hidden/target_freeze.json") == snapshot_record["frozen_target_sha256"]
    assert digest(ROOT / "evaluator/hidden/split_manifest.json") == snapshot_record["fixed_split_manifest_sha256"]
    report["participant_target_manifest_unchanged"] = True
    report["current_live_source_sha256"] = {name: digest(ROOT / "attempts/v_1" / name) for name in snapshot_record["sha256"] if (ROOT / "attempts/v_1" / name).is_file()}
    report["live_code_still_matches_snapshot"] = report["current_live_source_sha256"] == snapshot_record["sha256"]
    write_json(HERE / "search_report.json", report)
    print(json.dumps({key: report[key] for key in ("completed_batches", "tested_cases", "elapsed_seconds", "selected_group", "selected_group_confirmation", "live_code_still_matches_snapshot")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
