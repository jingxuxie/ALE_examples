import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np

import build
from solver import solve


def main():
    sys.dont_write_bytecode = True
    reference = Path(__file__).resolve().parent
    original_root = build.ROOT
    original_manifest = json.loads((reference / "manifest.json").read_text())
    previous = {entry["id"]: entry["input_sha256"] for entry in original_manifest["cases"]}
    started = time.monotonic()
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="regeneration-", dir=reference) as temporary:
            build.ROOT = Path(temporary)
            (build.ROOT / "private/reference").mkdir(parents=True)
            (build.ROOT / "participant/input").mkdir(parents=True)
            shutil.copyfile(reference / "author_tools.py", build.ROOT / "private/reference/author_tools.py")
            build.build(7359281, 1)
            fresh = json.loads((build.ROOT / "private/reference/manifest.json").read_text())
            for entry in fresh["cases"]:
                assert entry["input_sha256"] != previous[entry["id"]]
                with np.load(build.ROOT / entry["input"], allow_pickle=False) as archive:
                    prediction = solve(dict(archive))
                with np.load(build.ROOT / entry["truth"], allow_pickle=False) as archive:
                    error = float(np.max(np.abs(prediction - archive["target"])))
                assert error < 2e-8
                results.append({"id": entry["id"], "family": entry["family"], "input_sha256": entry["input_sha256"], "reference_max_log_error": error})
    finally:
        build.ROOT = original_root
    for entry in original_manifest["cases"]:
        assert hashlib.sha256((original_root / entry["input"]).read_bytes()).hexdigest() == entry["input_sha256"]
        assert hashlib.sha256((original_root / entry["truth"]).read_bytes()).hexdigest() == entry["truth_sha256"]
    report = {"seed": 7359281, "region": 1, "cases": results, "shipped_corpus_unchanged": True, "runtime": time.monotonic() - started}
    (reference / "regeneration_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"regenerated_cases": len(results), "shipped_corpus_unchanged": True, "runtime": report["runtime"]}))


if __name__ == "__main__":
    main()
