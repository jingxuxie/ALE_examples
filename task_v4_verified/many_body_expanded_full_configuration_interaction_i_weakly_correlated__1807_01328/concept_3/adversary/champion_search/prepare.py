"""Prepare independent private truth and a separate feature-only replay mount."""

import hashlib
import json
import secrets
import shutil
import sys
import time
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

SEARCH = Path(__file__).resolve().parent
ROOT = SEARCH.parents[1]
sys.path.insert(0, str(ROOT / "participant/input/workspace"))
from generator import Hamiltonian, accepted_sample, label, low_order_features


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    paths = [path for directory in ("participant", "evaluator")
             for path in (ROOT / directory).rglob("*")
             if path.is_file() and "__pycache__" not in path.parts]
    paths.append(ROOT / "attempts/v_1/reconstruct.py")
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)}


def rare_model(witness, alternative):
    onsite = np.asarray(witness["onsite"])
    density = np.full((8, 8), witness["density_off_diagonal"])
    np.fill_diagonal(density, 0.0)
    profile = np.asarray(witness["occupied_profile"])
    amplitudes = np.asarray(witness["source_amplitudes"])
    hopping = np.zeros((8, 8))
    hopping[:2, 2:] = -profile[:, None] * amplitudes[None, :]
    hopping[2:, :2] = hopping[:2, 2:].T
    hopping[2:, 2:] = witness["default_virtual_edge_magnitude"]
    np.fill_diagonal(hopping, 0.0)
    edge = (witness["alternative_branch_validation"]["alternative_edge_magnitude"]
            if alternative else witness["special_virtual_edge_0_1"])
    hopping[2, 3] = hopping[3, 2] = edge
    positions = np.asarray([.05, .2, .35, .55, .72, .9])
    return Hamiltonian(2, 6, 1, onsite, density, hopping, profile, positions,
                        (positions > np.median(positions)).astype(np.int8))


def main():
    started = time.perf_counter()
    public = SEARCH / "sandbox_input"
    private = SEARCH / "private"
    manifest_path = private / "sampling_manifest.json"
    if manifest_path.exists() or (public / "challenge_features.npz").exists():
        raise RuntimeError("Challenge already fixed; refusing regeneration")
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    before = protected_hashes()
    seed = secrets.randbits(128)
    rng = np.random.default_rng(seed)
    rows, truth_rows, metadata = [], [], []

    def append(model, features, truth, cohort, rejected):
        identifier = secrets.token_hex(16)
        features["ids"] = np.asarray(identifier, dtype="U32")
        rows.append(features)
        hopping = np.zeros((12, 12))
        hopping[:len(model.onsite), :len(model.onsite)] = model.hopping
        truth_rows.append({"ids": np.asarray(identifier, dtype="U32"), "tail": truth["tail"],
                           "family": model.family, "n_pairs": model.n_pairs,
                           "n_virtual": model.n_virtual, "cohort": np.asarray(cohort, dtype="U24"),
                           "reference_weight": truth["reference_weight"], "residual": truth["residual"],
                           "hopping": hopping})
        metadata.append({"id": identifier, "cohort": cohort, "family": model.family,
                         "n_pairs": model.n_pairs, "n_virtual": model.n_virtual,
                         "rejections_before_acceptance": rejected})

    with threadpool_limits(limits=1):
        for family, n_pairs, n_virtual, replicate in product(range(6), (2, 3), (6, 7, 8, 9), range(4)):
            model, features, truth, rejected = accepted_sample(rng, n_pairs, n_virtual, family)
            append(model, features, truth, "independent", rejected)
        witness = json.loads((ROOT / "adversary/v1_inverse_audit.json").read_text())["rare_support_stress"]
        for alternative in (False, True):
            model = rare_model(witness, alternative)
            features = low_order_features(model)
            truth = label(model, features)
            if truth["reference_weight"] < .85 or abs(truth["tail"]) < 1.5e-4:
                raise AssertionError("Rare support fixture violates curation")
            append(model, features, truth, "rare_upper_root" if alternative else "rare_lower_root", 0)
    ordering = rng.permutation(len(rows))
    arrays = {key: np.stack([row[key] for row in rows])[ordering] for key in rows[0]}
    truth = {key: np.stack([row[key] for row in truth_rows])[ordering] for key in truth_rows[0]}
    forbidden = {"tail", "hopping", "correlation", "residual", "reference_weight", "seed", "cohort"}
    assert not forbidden.intersection(arrays)
    assert len(np.unique(arrays["ids"])) == len(rows)
    np.savez_compressed(public / "challenge_features.npz", **arrays)
    np.savez_compressed(private / "truth.npz", **truth)
    shutil.copyfile(ROOT / "attempts/v_1/reconstruct.py", public / "reconstruct.py")
    shutil.copyfile(ROOT / "participant/input/workspace/generator.py", public / "generator.py")
    source_hashes = {name: digest(public / name) for name in ("reconstruct.py", "generator.py")}
    (public / "source_hashes.json").write_text(json.dumps(source_hashes, indent=2) + "\n")
    assert source_hashes["reconstruct.py"] == before["attempts/v_1/reconstruct.py"]
    assert source_hashes["generator.py"] == before["participant/input/workspace/generator.py"]
    if protected_hashes() != before:
        raise AssertionError("Protected files changed during preparation")
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(),
                "sampling_seed_not_release_seed": seed, "independent_cases": 192,
                "support_cases": 2, "total_cases": len(rows),
                "stratification": "4 independent accepted draws per family x pair count x virtual count",
                "families": list(range(6)), "pair_counts": [2, 3], "virtual_counts": [6, 7, 8, 9],
                "rare_cases": "Original rare two-root support witness and its alternative physical root; both accepted",
                "case_metadata": [metadata[index] for index in ordering],
                "feature_keys": sorted(arrays), "feature_sha256": digest(public / "challenge_features.npz"),
                "truth_sha256": digest(private / "truth.npz"), "source_sha256": source_hashes,
                "protected_sha256": before, "runtime_seconds": time.perf_counter() - started,
                "minimum_reference_weight": float(truth["reference_weight"].min()),
                "minimum_absolute_tail": float(np.abs(truth["tail"]).min()),
                "maximum_label_solver_residual": float(truth["residual"].max()),
                "is_new_participant_generation": False,
                "official_static_score_consulted_or_duplicated": False}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ("independent_cases", "support_cases", "total_cases",
          "minimum_reference_weight", "minimum_absolute_tail", "maximum_label_solver_residual", "runtime_seconds")}, indent=2))


if __name__ == "__main__":
    main()
