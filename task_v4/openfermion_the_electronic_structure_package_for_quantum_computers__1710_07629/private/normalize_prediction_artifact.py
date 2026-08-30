import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "concept_3/attempts/v_2_frozen"
    destination = ROOT / "concept_3/adversary/normalized_v2"
    destination.mkdir(exist_ok=False)
    copied = {}
    for path in sorted(source.iterdir()):
        if path.is_file() and not path.is_symlink():
            shutil.copy2(path, destination / path.name)
            copied[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert all(hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest for name, digest in copied.items())
    original_files = [path for path in source.rglob("*") if path.is_file()]
    manifest = {"not_a_fresh_submission": True, "source": str(source), "destination": str(destination), "operation": "Copy every root-level file byte-for-byte; omit only the dev directory of unused training intermediates and logs", "algorithm_changes": False, "weights_changed": False, "hyperparameters_changed": False, "hidden_data_used_for_normalization": False, "original_file_count": len(original_files), "original_bytes": sum(path.stat().st_size for path in original_files), "normalized_file_count": len(copied), "normalized_bytes": sum(path.stat().st_size for path in destination.iterdir()), "copied_sha256": copied}
    (destination.parent / "normalized_v2_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({key: value for key, value in manifest.items() if key != "copied_sha256"}, indent=2))


if __name__ == "__main__":
    main()
