"""Privileged one-time dataset construction; never distributed to candidates."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from generator import draw_dataset


def main():
    hidden = ROOT / "evaluator" / "hidden"
    manifest_path = hidden / "data_manifest.json"
    if manifest_path.exists():
        raise RuntimeError("Dataset already frozen; refusing regeneration")
    seed_path = hidden / "seeds.json"
    if seed_path.exists():
        seeds = json.loads(seed_path.read_text())
    else:
        seeds = {name: secrets.randbits(63) for name in ("train", "validation", "test", "audit")}
        seed_path.write_text(json.dumps(seeds, indent=2) + "\n")
        seed_path.chmod(0o600)
    hashes = {}
    started = time.time()
    for name, per_family in (("train", 96), ("validation", 16), ("test", 16), ("audit", 3)):
        features, labels, private = draw_dataset(seeds[name], per_family)
        destination = ROOT / "participant" / "input" if name in ("train", "validation") else hidden
        for suffix, values in (("features", features), ("labels", labels)):
            path = destination / f"{name}_{suffix}.npz"
            np.savez_compressed(path, **values)
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        private_path = hidden / f"{name}_latent.npz"
        np.savez_compressed(private_path, **private)
        private_path.chmod(0o600)
        print(f"generated {name}: {4 * per_family} cases ({time.time() - started:.1f}s)", flush=True)
    target_hash = hashlib.sha256((hidden / "target.json").read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(dict(version=1, target_sha256=target_hash, files=hashes,
                                            selection="independent balanced draws, no rejection"), indent=2) + "\n")
    for path in hidden.iterdir():
        if path.is_file():
            path.chmod(0o600)


if __name__ == "__main__":
    main()
