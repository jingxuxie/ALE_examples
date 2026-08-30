"""Check the static submission contract and public input-file integrity."""

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np

from reconstruct import DEFAULT_ASSETS


def main():
    output = Path(__file__).resolve().parent
    artifact = output / "predictions.npz"
    manifest = json.loads((DEFAULT_ASSETS / "data" / "manifest.json").read_text())
    verified_inputs = {}
    for filename, expected in manifest["files"].items():
        actual = hashlib.sha256((DEFAULT_ASSETS / "data" / filename).read_bytes()).hexdigest()
        assert actual == expected, f"Public input hash mismatch: {filename}"
        verified_inputs[filename] = actual
    assert artifact.is_file() and not artifact.is_symlink()
    assert artifact.stat().st_size <= 8 * 1024 ** 2
    with zipfile.ZipFile(artifact) as archive:
        uncompressed_bytes = sum(item.file_size for item in archive.infolist())
        assert uncompressed_bytes <= 8 * 1024 ** 2
        assert archive.testzip() is None
    with np.load(DEFAULT_ASSETS / "data" / "test_features.npz", allow_pickle=False) as test:
        expected_ids = test["ids"]
    with np.load(artifact, allow_pickle=False) as prediction:
        assert len(prediction.files) == 2 and set(prediction.files) == {"ids", "tail"}
        ids, tail = prediction["ids"], prediction["tail"]
        assert ids.shape == (288,) and ids.dtype == np.dtype("U32")
        assert tail.shape == (288,) and tail.dtype in (np.dtype("float32"), np.dtype("float64"))
        assert len(np.unique(ids)) == 288
        assert set(ids) == set(expected_ids)
        assert np.all(np.isfinite(tail)) and np.max(np.abs(tail)) <= 1e6
        assert np.min(np.abs(tail)) >= 1.5e-4 - 1e-12
        tail_minimum, tail_maximum = float(tail.min()), float(tail.max())
    reconstruction = json.loads((output / "reconstruction_report.json").read_text())
    for split, results in reconstruction["splits"].items():
        assert results["max_singleton_residual"] < 1e-9
        assert results["max_pair_residual"] < 1e-9
        assert results["max_triple_residual"] < 1e-9
        assert results["max_full_eigen_residual"] < 1e-9
        assert results["minimum_reference_weight"] >= 0.85 - 1e-12
        if "metrics" in results:
            assert results["metrics"]["rmse"] < 3e-5
            assert results["metrics"]["worst_family_rmse"] < 6e-5
    report = {
        "valid": True,
        "rows": 288,
        "keys": ["ids", "tail"],
        "ids_dtype": "U32",
        "tail_dtype": str(tail.dtype),
        "compressed_bytes": artifact.stat().st_size,
        "uncompressed_bytes": uncompressed_bytes,
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "tail_minimum": tail_minimum,
        "tail_maximum": tail_maximum,
        "public_input_hashes": verified_inputs,
        "hidden_evaluation": "not accessed; test labels unavailable",
    }
    (output / "artifact_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
