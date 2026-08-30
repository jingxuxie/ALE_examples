"""Privileged release builder. Never include this directory in a fresh workspace."""

import hashlib
import json
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input/workspace"))
from generator import FAMILIES, accepted_sample, full_order_sums


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def main():
    started = time.perf_counter()
    hidden = ROOT / "evaluator/hidden"
    data = ROOT / "participant/input/workspace/data"
    hidden.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    marker = hidden / "generation_freeze.json"
    if marker.exists():
        raise RuntimeError("Release already started; refusing to change fixed examples or targets")
    criteria_path = ROOT / "evaluator/criteria.json"
    criteria = json.loads(criteria_path.read_text())
    marker.write_text(json.dumps({"created_utc": timestamp(),
                                 "criteria_sha256": digest(criteria_path),
                                 "generator_sha256": digest(ROOT / "participant/input/workspace/generator.py"),
                                 "baseline_sha256": digest(ROOT / "participant/input/workspace/baseline/predict.py"),
                                 "phase": "targets and code frozen before any release labels"}, indent=2) + "\n")
    private_seeds = {name: secrets.randbits(128) for name in ("train", "validation", "test")}
    (hidden / "seeds.json").write_text(json.dumps(private_seeds, indent=2) + "\n")
    report, private_rows, audit_models = {}, {}, []
    with threadpool_limits(limits=1):
        for split in ("train", "validation", "test"):
            rng = np.random.default_rng(private_seeds[split])
            families = criteria["hidden_families"] if split == "test" else criteria["labeled_families"]
            repetitions = criteria[f"{split}_per_stratum"]
            rows, truths = [], []
            rejections = 0
            for family in families:
                for n_pairs in criteria["pair_counts"]:
                    for n_virtual in criteria["virtual_counts"]:
                        for repetition in range(repetitions):
                            model, features, truth, rejected = accepted_sample(rng, n_pairs, n_virtual, family)
                            features["ids"] = np.asarray(secrets.token_hex(16), dtype="U32")
                            rows.append(features)
                            truths.append(truth)
                            rejections += rejected
                            if repetition == 0 and n_virtual in (6, 9):
                                audit_models.append({"split": split, "id": str(features["ids"]),
                                                     "n_pairs": n_pairs, "n_virtual": n_virtual,
                                                     "family": family, "onsite": model.onsite.tolist(),
                                                     "density": model.density.tolist(),
                                                     "hopping": model.hopping.tolist(),
                                                     "occupied_profile": model.occupied_profile.tolist(),
                                                     "positions": model.positions.tolist(),
                                                     "groups": model.groups.tolist(),
                                                     "order_sums": full_order_sums(model).tolist()})
                print(split, FAMILIES[family], "rows", len(rows), flush=True)
            ordering = rng.permutation(len(rows))
            arrays = {key: np.stack([row[key] for row in rows])[ordering] for key in rows[0]}
            truth_arrays = {key: np.asarray([row[key] for row in truths])[ordering] for key in truths[0]}
            private_rows[split] = {"ids": arrays["ids"], "family": arrays["family"], **truth_arrays}
            if split != "test":
                arrays["tail"] = truth_arrays["tail"]
            np.savez_compressed(data / ("test_features.npz" if split == "test" else f"{split}.npz"), **arrays)
            np.savez_compressed(hidden / f"{split}_truth.npz", **private_rows[split])
            report[split] = {
                "count": len(rows), "family_counts": {FAMILIES[value]: int(np.sum(arrays["family"] == value))
                                                       for value in families},
                "absolute_tail_quantiles": np.quantile(np.abs(truth_arrays["tail"]), [0, .25, .5, .75, 1]).tolist(),
                "minimum_reference_weight": float(truth_arrays["reference_weight"].min()),
                "maximum_residual": float(truth_arrays["residual"].max()),
                "rejections": rejections,
                "negative_tail_fraction": float(np.mean(truth_arrays["tail"] < 0)),
            }
    (hidden / "audit_models.json").write_text(json.dumps(audit_models) + "\n")
    report["runtime_seconds"] = time.perf_counter() - started
    report["completed_utc"] = timestamp()
    report["target_freeze_sha256"] = digest(marker)
    (hidden / "generation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    public_manifest = {"schema": "pair_tail_d_v1", "counts": {name: report[name]["count"]
                       for name in ("train", "validation", "test")},
                       "files": {path.name: digest(path) for path in sorted(data.glob("*.npz"))},
                       "id_policy": "independent cryptographic 128-bit tokens; not seed-derived",
                       "labeled_families": [FAMILIES[value] for value in criteria["labeled_families"]],
                       "hidden_only_families": ["mixed_range", "bottleneck"]}
    (data / "manifest.json").write_text(json.dumps(public_manifest, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
