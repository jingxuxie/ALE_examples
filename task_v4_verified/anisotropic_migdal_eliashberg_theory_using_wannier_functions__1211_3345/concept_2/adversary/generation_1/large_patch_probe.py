import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import difflib
import hashlib
import json
import re
import signal
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from prepare_pending import PENDING, ROOT, protected_state, text_patch

POOL = ROOT / "adversary/ratchet_pool"
sys.path.insert(0, str(POOL))
from pool_common import EliashbergSolver, audit_pair, json_write, load_instance, physics_report, read_artifact


def prepare_dimension_adapter(folder):
    source = ROOT / "champions/generation_1/frozen_submission/search.py"
    original = source.read_text()
    participant_assignment = re.search(r'^PARTICIPANT = Path\([^\n]+\)$', original, flags=re.MULTILINE).group()
    substitutions = [
        (participant_assignment, 'PARTICIPANT = Path("/participant")'),
        ("self.rows, self.columns = np.triu_indices(8, 1)",
         "self.patch_count = len(self.instance[\"weights\"])\n        self.rows, self.columns = np.triu_indices(self.patch_count, 1)\n        self.edge_count = len(self.rows)"),
        ("range(28)", "range(self.edge_count)"),
        ("np.zeros((3, 28))", "np.zeros((3, self.edge_count))"),
        ("range(8)", "range(self.patch_count)"),
        ("8 * equation.ravel()", "self.patch_count * equation.ravel()"),
        ('8 * (self.instance["row_sums"]', 'self.patch_count * (self.instance["row_sums"]'),
        ("reshape(3, 28)", "reshape(3, self.edge_count)"),
    ]
    adapted = original
    changes = []
    for previous, following in substitutions:
        count = adapted.count(previous)
        assert count > 0
        changes.append({"before": previous, "after": following, "occurrences": count})
        adapted = adapted.replace(previous, following)
    restored = adapted
    for previous, following in reversed(substitutions):
        restored = restored.replace(following, previous)
    assert restored == original
    destination = folder / "adapter/search.py"
    text_patch(destination, adapted)
    (folder / "adapter/dimension_and_path.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), adapted.splitlines(True), fromfile="frozen_submission/search.py", tofile="dimension_adapter/search.py")))
    json_write(folder / "adapter/manifest.json", {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "adapted_sha256": hashlib.sha256(adapted.encode()).hexdigest(),
        "changes": changes, "all_other_source_bytes_unchanged_after_reversing_plumbing": True,
        "target_handling": "No success-ratio stop exists in the original search. Target is read by the checker from the new config; all iteration limits, tolerances, seed, restarts and solver choices are unchanged.",
    })
    return destination


def generate(folder):
    candidate = folder / "candidate_n24"
    if (candidate / "audit.json").exists():
        return candidate, json.loads((candidate / "audit.json").read_text())
    started_cpu = time.process_time()
    base = load_instance(PENDING / "archived_originals/participant/input")
    config = json.loads(json.dumps(base["config"]))
    sources = [
        ("original_fresh_pair", PENDING / "archived_originals/participant/input", ROOT / "champions/generation_1/frozen_submission/witness.npz"),
        ("rough_broad", POOL / "instances/rough_broad/input", POOL / "instances/rough_broad/witness.npz"),
        ("rough_assortative", POOL / "instances/rough_assortative/input", POOL / "instances/rough_assortative/witness.npz"),
    ]
    patches = 24
    weights = np.full(patches, 1. / patches)
    patch_index = np.arange(patches)
    band_index = patch_index // 8
    local_index = patch_index % 8
    profiles = np.array([1 + .35 * np.cos((local_index + 1) * np.pi / 9 + 2 * np.pi * (band_index + mode) / 3)
                         for mode in range(3)])
    shared = np.array([.0055 + .0015 * np.outer(profile, profile) for profile in profiles])
    reference = shared.copy()
    pair = np.stack([shared.copy(), shared.copy()])
    source_records = []
    for band, (name, input_path, witness_path) in enumerate(sources):
        source_instance = load_instance(input_path)
        source_pair = read_artifact(witness_path, source_instance["config"])
        source_solver = EliashbergSolver(source_instance["weights"], source_instance["row_sums"], base["energies_mev"], config)
        temperatures = [source_solver.critical_temperature(modes, 48)["tc_kelvin"] for modes in source_pair]
        order = np.argsort(temperatures)
        source_pair = source_pair[order]
        target_low = 84.

        def residual(scale):
            solver = EliashbergSolver(source_instance["weights"], source_instance["row_sums"] * scale, base["energies_mev"], config)
            return solver.eigenpair(source_pair[0] * scale, target_low, 48)["eigenvalue"] - 1

        scale = float(brentq(residual, .45, 1.6, xtol=1e-10))
        block = slice(8 * band, 8 * (band + 1))
        fixed = np.array([.006 * np.outer(profile[block], profile[block]) for profile in profiles])
        reference[:, block, block] = 3 * scale * source_instance["reference"] + fixed
        pair[:, :, block, block] = 3 * scale * source_pair + fixed[None]
        source_records.append({
            "band": band, "name": name, "source_input_sha256": source_instance["input_sha256"],
            "source_witness_sha256": hashlib.sha256(witness_path.read_bytes()).hexdigest(),
            "common_energy_low_high_before_scaling": np.asarray(temperatures)[order].tolist(),
            "integrated_coupling_scale": scale, "isolated_low_target_kelvin": target_low,
        })
    config.update(dataset_id="nonidentical_three_band_n24", artifact_shape=[2, 3, patches, patches],
                  entry_upper=float(np.ceil(max(float(pair.max()), float(reference.max()))) + 1), target_ratio=1.)
    instance = {
        "config": config, "reference": reference, "weights": weights, "energies_mev": base["energies_mev"].copy(),
        "row_sums": reference @ weights, "diagonal": np.diagonal(reference, axis1=1, axis2=2).copy(),
        "static": reference.sum(axis=0),
    }
    provisional = physics_report(pair, instance)
    target = float(np.floor((provisional["score"] - .003) * 100 + 1e-10) / 100)
    config["target_ratio"] = target
    input_folder = candidate / "input"
    input_folder.mkdir(parents=True, exist_ok=True)
    json_write(input_folder / "config.json", config)
    with (input_folder / "reference.npz").open("wb") as stream:
        np.savez_compressed(stream, **{key: value for key, value in instance.items() if key != "config"})
    instance = load_instance(input_folder)
    with (candidate / "witness.npz").open("wb") as stream:
        np.savez_compressed(stream, kernels=pair)
    loaded_pair = read_artifact(candidate / "witness.npz", config)
    assert np.array_equal(loaded_pair, pair)
    pair = loaded_pair
    audit = audit_pair(pair, instance)
    json_write(candidate / "audit.json", audit)
    with (candidate / "baseline.npz").open("wb") as stream:
        np.savez_compressed(stream, kernels=np.stack([reference, reference]))
    baseline = audit_pair(np.stack([reference, reference]), instance)
    json_write(candidate / "baseline_audit.json", baseline)
    commutators = []
    for kernel_index, modes in enumerate(pair):
        for first in range(3):
            for second in range(first + 1, 3):
                commutators.append({"kernel": kernel_index, "modes": [first, second],
                                    "relative_frobenius": float(np.linalg.norm(modes[first] @ modes[second] - modes[second] @ modes[first]) /
                                                                (np.linalg.norm(modes[first]) * np.linalg.norm(modes[second])))})
    provenance = {
        "patches": patches, "bands": 3, "source_records": source_records,
        "coupling_convention": "Within-band matrices are scaled by N/8 to preserve integrated couplings with weights 1/N; all bands have different source arrays. Shared positive reciprocal interband matrices and distinct mode-dependent intraband perturbations are added to both endpoints and reference.",
        "no_hidden_labels": "Contiguous bands are public, labels are not permuted. This is not a replicated-block instance.",
        "noncommuting_mode_diagnostics": commutators,
        "integrated_total_row_range": [float(instance["row_sums"].sum(axis=0).min()), float(instance["row_sums"].sum(axis=0).max())],
        "target_rule": "Largest 0.01-spaced ratio at least 0.003 below the independently evaluated private score, frozen before any large-instance champion replay; require >=1.10 for retention.",
        "target_ratio": target, "private_score": audit["score"], "private_valid": audit["valid"],
        "retained": bool(audit["valid"] and target >= 1.10), "generation_cpu_seconds": time.process_time() - started_cpu,
        "numerical_contract": "Original three positive-energy scenarios, counts96/192 plus nominal384, zero Coulomb. Independent signed96 assembly in every family and original regular-row control.",
    }
    json_write(candidate / "provenance.json", provenance)
    print(json.dumps(provenance), flush=True)
    return candidate, audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true")
    arguments = parser.parse_args()
    before = protected_state()
    folder = PENDING / "large_patch_probe"
    folder.mkdir(exist_ok=True)
    candidate, private = generate(folder)
    adapter = prepare_dimension_adapter(folder)
    if arguments.replay:
        from replay_champion import replay
        target = load_instance(candidate / "input")["config"]["target_ratio"]
        assert private["valid"] and target >= 1.10
        results = []
        started = time.monotonic()

        def budget_exceeded(signum, frame):
            raise TimeoutError("900-second bounded private replay budget exhausted; incomplete runs are not evidence of optimization failure")

        generation_cpu = json.loads((candidate / "provenance.json").read_text())["generation_cpu_seconds"]
        replay_budget = max(1, int(900 - generation_cpu))
        signal.signal(signal.SIGALRM, budget_exceeded)
        signal.alarm(replay_budget)
        try:
            control = replay("dimension_adapter_original_control", PENDING / "archived_originals/participant/input", 1.1245411788778297, adapter)
            assert control["valid"] and abs(control["score"] - 1.1245411788778297) < 1e-8
            for family in ("compressed_spectrum", "nominal", "expanded_spectrum"):
                result = replay("large_n24__" + family, candidate / "input", private["score"], adapter, family)
                results.append(result)
                json_write(folder / "replay_progress.json", {"results": results, "target_ratio": target})
                if result.get("valid"):
                    break
            reason = "Actual dimension-adapted champion solves the larger instance." if any(result.get("valid") for result in results) else "No passing completed replay yet; any failure needs full-family/endpoint and resource review before being promoted as hardness evidence."
        except TimeoutError as error:
            reason = str(error)
        finally:
            signal.alarm(0)
        json_write(folder / "replay_summary.json", {
            "results": results, "target_ratio": target, "private_score": private["score"],
            "champion_passed": any(result.get("valid") for result in results),
            "reason": reason, "elapsed_wall_seconds": time.monotonic() - started,
            "no_fresh_model_launched": True, "active_package_unchanged": before == protected_state(),
            "budget_seconds": replay_budget,
            "generation_cpu_seconds": generation_cpu,
        })
        print(json.dumps({"large_probe_finished": True, "reason": reason}), flush=True)
    assert before == protected_state()


if __name__ == "__main__":
    main()
