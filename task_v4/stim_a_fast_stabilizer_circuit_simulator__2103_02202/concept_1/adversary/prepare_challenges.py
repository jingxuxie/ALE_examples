import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import instance
from audit_structure import rank


def main():
    destination = ROOT / "adversary/challenge_pool"
    destination.mkdir(exist_ok=True)
    manifest = []
    for family_index, family in enumerate(("biased", "correlated", "drifting")):
        for index in range(8):
            seed = 7049821 + family_index * 91721 + index * 1607
            model = instance(seed, family)
            signatures = [signature for channel in model["channels"] for signature in channel["signatures"]]
            detector_mask = (1 << model["detectors"]) - 1
            if rank(signatures) != rank([signature & detector_mask for signature in signatures]) + 1:
                raise RuntimeError("degenerate challenge")
            path = destination / (family + "_" + str(index) + ".json")
            path.write_text(json.dumps(model, indent=2) + "\n")
            manifest.append({"name": path.stem, "family": family, "seed": seed,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (ROOT / "adversary/challenge_pool_manifest.json").write_text(json.dumps({
        "purpose": "prospective broad private challenge space for any solved champion; not graded in generation 1",
        "count": len(manifest), "families": 3, "cases": manifest}, indent=2) + "\n")
    print("Prepared", len(manifest), "private challenge instances; generation-1 evaluator unchanged")


if __name__ == "__main__":
    main()
