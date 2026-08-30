import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def concatenate(first, second, order):
    count = len(first["sample_id"])
    combined = {}
    for key, values in first.items():
        if values.ndim and values.shape[0] == count:
            combined[key] = np.concatenate([values, second[key]])[order]
        else:
            if not np.array_equal(values, second[key]):
                raise ValueError("Shared grid mismatch")
            combined[key] = values
    return combined


def main():
    for batch, seeds in enumerate([(0, 1), (2, 3)]):
        sources = [HERE / "data" / f"seed_{seed:02d}" / "participant" / "input" for seed in seeds]
        inputs = [load(source / "challenge_input.npz") for source in sources]
        labels = [load(source / "challenge_labels.npz") for source in sources]
        order = np.random.default_rng(8285520 + batch).permutation(192)
        features = concatenate(*inputs, order)
        truth = concatenate(*labels, order)
        assert len(features["sample_id"]) == 192
        assert np.array_equal(features["sample_id"], truth["sample_id"])
        assert np.all(np.bincount(truth["family_id"], minlength=6) == 32)
        folder = HERE / f"final_broad_{batch}"
        folder.mkdir(exist_ok=True)
        np.savez_compressed(folder / "input.npz", **features)
        np.savez_compressed(folder / "labels.npz", **truth)
        manifest = {
            "count": 192, "per_family": 32, "source_seed_indices": seeds,
            "selection": "All independent IID cases retained; no error-based selection; fixed row permutation; exact official batch size and family balance.",
            "not_official_test": True,
            "files_sha256": {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in ["input.npz", "labels.npz"]},
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(folder)


if __name__ == "__main__":
    main()
