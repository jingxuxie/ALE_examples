import argparse
import hashlib
import json
import shutil
import stat
from pathlib import Path


def freeze(source, destination):
    source = source.resolve()
    if destination.exists():
        raise ValueError("frozen destination already exists")
    destination.mkdir(parents=True)
    manifest = {"source": str(source), "files": {}, "rejected_special_files": []}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        target = destination / relative
        kind = path.lstat().st_mode
        if stat.S_ISLNK(kind):
            manifest["rejected_special_files"].append(str(relative))
        elif stat.S_ISDIR(kind):
            target.mkdir(parents=True, exist_ok=True)
        elif stat.S_ISREG(kind):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            manifest["files"][str(relative)] = {"sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                                "bytes": target.stat().st_size}
        else:
            manifest["rejected_special_files"].append(str(relative))
    destination.with_suffix(".freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    manifest = freeze(args.source, args.destination)
    print(json.dumps({"files": len(manifest["files"]), "rejected_special_files": manifest["rejected_special_files"]}))


if __name__ == "__main__":
    main()
