import argparse
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from core import load_json, validate_submission
from design import search


def main():
    parser = argparse.ArgumentParser(description="Private independent post-freeze evolutionary witness search.")
    parser.add_argument("--iterations", type=int, default=120000)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    spec, digest = load_json(root / "evaluator/hidden/frozen_spec.json")
    manifest = json.loads((root / "evaluator/hidden/freeze_manifest.json").read_text())
    seeds = json.loads((root / "evaluator/hidden/fresh_seeds.json").read_text())
    if digest != manifest["spec_sha256"]:
        raise RuntimeError("frozen specification changed")
    for value, commitment in zip(seeds, manifest["fresh_seed_sha256"]):
        if hashlib.sha256(value.encode()).hexdigest() != commitment:
            raise RuntimeError("seed commitment mismatch")
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(search, family, int(seed), args.iterations)
                   for family, seed in zip(spec["families"], seeds)]
        results = [future.result() for future in futures]
    artifact = {"schema_version": 1, "circuits": [result[0] for result in results]}
    validate_submission(artifact, spec)
    (root / "attempts/private_fresh.json").write_text(json.dumps(artifact, indent=2) + "\n")
    report = {"phase": "post-freeze independent numeric search; not an agent run",
              "spec_sha256": digest, "started_unix": started,
              "finished_unix": time.time(), "seed_sha256": manifest["fresh_seed_sha256"],
              "results": [result[1] for result in results]}
    (root / "evaluator/hidden/fresh_search_results.json").write_text(json.dumps(report, indent=2) + "\n")
    for family, result in zip(spec["families"], results):
        print(family["id"], result[1]["core_score"], result[1]["iterations"], result[1]["failed"], flush=True)


if __name__ == "__main__":
    main()
