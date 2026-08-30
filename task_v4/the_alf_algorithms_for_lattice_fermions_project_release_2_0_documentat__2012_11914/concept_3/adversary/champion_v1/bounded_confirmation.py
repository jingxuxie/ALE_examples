"""Independent smaller confirmation after discovery's resource-limited stop."""

import argparse
import json
import os
from pathlib import Path
import time

import search
import numpy as np


HERE = search.HERE
LOCATION = HERE / "bounded_confirmation"


def descriptors(inputs, labels, parameters):
    true_observables = search.observables(labels["spectral_mass"], inputs["omega_edges"])
    rows = []
    for index, descriptor in enumerate(parameters):
        family = descriptor["family_id"]
        rows.append({
            "family_id": family,
            "component_count": descriptor["component_count"],
            "beta": float(inputs["beta"][index]),
            "noise_rms": float(np.sqrt(np.trace(inputs["covariance"][index]) / 56.0)),
            "high_energy_mass": float(true_observables["band_weights"][index, 0] + true_observables["band_weights"][index, -1]),
            "coherent_width": descriptor["draws"][1]["value"] if family == 0 else (descriptor["draws"][6]["value"] if family == 1 else None),
        })
    return rows


def prepare():
    started = time.monotonic()
    LOCATION.mkdir()
    previous = json.loads((HERE / "search_report.json").read_text())
    eligible = {name: group for name, group in previous["discovery_groups"].items() if group["count"] >= 16}
    primary = min(eligible, key=lambda name: eligible[name]["score"])
    calibration_family = min(search.FAMILY_NAMES, key=lambda name: previous["discovery_groups"][name]["coverage_80pct"])
    cohorts = [
        {"name": "primary", "group": primary, "count": 16, "seed_index": 201, "per_family": 128},
        {"name": "calibration", "group": calibration_family, "count": 24, "seed_index": 201, "per_family": 128},
        {"name": "low_information_stress", "group": "multiband_low_information", "count": 24, "seed_index": 202, "per_family": 192},
    ]
    amendment = {
        "reason": "fourth 96-case discovery batch timed out; retain the three completed discovery seeds and spend only remaining compute budget",
        "original_search_elapsed_seconds": previous["elapsed_seconds"],
        "primary_selection_rule_unchanged_except_available_discovery_count": True,
        "confirmation_predictions_observed_at_selection": False,
        "cohorts": cohorts,
        "stress_interpretation": "secondary physical stress already listed in the original protocol; discovery n=11 is below primary eligibility, so this is explicitly a secondary exploratory hypothesis with fresh independent confirmation",
        "no_parameter_range_or_noise_extension": True,
        "conditional_sampling": "first qualifying rows under a physics-only predicate; no prediction or prediction error consulted",
    }
    search.write_json(LOCATION / "protocol_amendment.json", amendment)
    generated = {}
    collections = []
    for cohort in cohorts:
        seed_index = cohort["seed_index"]
        if seed_index not in generated:
            input_path, labels_path, parameters = search.generate_batch(seed_index, cohort["per_family"])
            inputs, labels = search.load(input_path), search.load(labels_path)
            generated[seed_index] = (inputs, labels, parameters, descriptors(inputs, labels, parameters))
        inputs, labels, parameters, rows = generated[seed_index]
        indices = np.array([index for index, row in enumerate(rows) if search.GROUPS[cohort["group"]](row)], dtype=int)[:cohort["count"]]
        if len(indices) != cohort["count"]:
            raise ValueError("insufficient qualifying rows; do not silently alter the physical predicate")
        collections.append((cohort, inputs, labels, parameters, indices))
    for category, offset in (("input", 1), ("labels", 2)):
        result = {}
        for name in collections[0][offset]:
            result[name] = collections[0][offset][name] if name == "omega_edges" else np.concatenate([entry[offset][name][entry[4]] for entry in collections])
        np.savez_compressed(LOCATION / f"{category}.npz", **result)
    parameters = [entry[3][index] for entry in collections for index in entry[4]]
    membership = [entry[0]["name"] for entry in collections for index in entry[4]]
    search.write_json(LOCATION / "parameters.json", parameters)
    search.write_json(LOCATION / "membership.json", membership)
    assert len(set(int(identifier) for identifier in search.load(LOCATION / "input.npz")["sample_id"])) == 64
    preparation = {"preparation_seconds": time.monotonic() - started, "count": len(parameters), "files_sha256": {name: search.digest(LOCATION / name) for name in ("input.npz", "labels.npz", "parameters.json", "membership.json", "protocol_amendment.json")}}
    search.write_json(LOCATION / "preparation.json", preparation)
    print(json.dumps({**preparation, "cohorts": cohorts}, indent=2), flush=True)


def run():
    started = time.monotonic()
    preparation = json.loads((LOCATION / "preparation.json").read_text())
    for name, expected in preparation["files_sha256"].items():
        assert search.digest(LOCATION / name) == expected
    amendment = json.loads((LOCATION / "protocol_amendment.json").read_text())
    remaining = 600.0 - amendment["original_search_elapsed_seconds"] - preparation["preparation_seconds"]
    wall_limit = min(110.0, remaining - 5.0)
    if wall_limit < 20.0:
        raise ValueError("insufficient remaining bounded compute budget")
    affinity = sorted(os.sched_getaffinity(0))
    selected_cpu = affinity[1] if len(affinity) > 1 else affinity[0]
    os.sched_setaffinity(0, {selected_cpu})
    prediction, resources = search.execute_submission(HERE / "snapshot", LOCATION / "input.npz", search.ROOT / "participant/input", wall_seconds=wall_limit)
    inputs, labels = search.load(LOCATION / "input.npz"), search.load(LOCATION / "labels.npz")
    parameters = json.loads((LOCATION / "parameters.json").read_text())
    membership = np.array(json.loads((LOCATION / "membership.json").read_text()))
    search.score_prediction(prediction, inputs, labels)
    rows = search.row_statistics(prediction, inputs, labels, parameters)
    np.savez_compressed(LOCATION / "predictions.npz", **prediction)
    search.write_json(LOCATION / "row_analysis.json", rows)
    results = {}
    for cohort in amendment["cohorts"]:
        mask = membership == cohort["name"]
        selected_rows = [row for row, selected in zip(rows, mask) if selected]
        results[cohort["name"]] = {"physical_group": cohort["group"], **search.summarize(selected_rows)}
        fixture = LOCATION / (cohort["name"] + "_fixture")
        fixture.mkdir()
        for filename, collection in (("input.npz", inputs), ("labels.npz", labels), ("snapshot_predictions.npz", prediction)):
            selected = {key: values if key == "omega_edges" else values[mask] for key, values in collection.items()}
            np.savez_compressed(fixture / filename, **selected)
        search.write_json(fixture / "parameters.json", [descriptor for descriptor, selected in zip(parameters, mask) if selected])
        manifest = {"selected_group": cohort["group"], "count": int(mask.sum()), "selection": "independent conditional confirmation; all selected cases retained regardless of prediction", "not_official_test": True, "requires_final_code_retest": True, "files_sha256": {path.name: search.digest(path) for path in fixture.iterdir() if path.is_file()}}
        search.write_json(fixture / "manifest.json", manifest)
    snapshot_record = json.loads((HERE / "snapshot_manifest.json").read_text())
    for relative, expected in snapshot_record["public_assets_sha256"].items():
        assert search.digest(search.ROOT / "participant" / relative) == expected
    assert search.digest(search.ROOT / "evaluator/hidden/target_freeze.json") == snapshot_record["frozen_target_sha256"]
    assert search.digest(search.ROOT / "evaluator/hidden/split_manifest.json") == snapshot_record["fixed_split_manifest_sha256"]
    elapsed = time.monotonic() - started
    report = {
        "count": len(rows),
        "cohorts": results,
        "resources": resources,
        "worker_affinity_cpu": selected_cpu,
        "affinity_reason": "same one-core resource, but second allowed CPU to avoid contending with the official runner's first-core affinity",
        "confirmation_elapsed_seconds": elapsed,
        "combined_search_and_preparation_compute_wall_seconds": amendment["original_search_elapsed_seconds"] + preparation["preparation_seconds"] + elapsed,
        "participant_target_manifest_unchanged": True,
        "not_official_score_or_pass_decision": True,
        "snapshot_solve_sha256": snapshot_record["sha256"]["solve.py"],
        "live_solve_sha256": search.digest(search.ROOT / "attempts/v_1/solve.py"),
    }
    search.write_json(LOCATION / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    arguments = parser.parse_args()
    prepare() if arguments.prepare_only else run()
