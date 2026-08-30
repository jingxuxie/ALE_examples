import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))

import bdg


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-patch", action="store_true")
    arguments = parser.parse_args()
    hidden = ROOT / "evaluator" / "hidden"
    if arguments.snapshot_patch:
        print("*** Begin Patch")
        for source, destination in ((ROOT / "participant" / "workspace" / "bdg.py", hidden / "forward_model.py"),
                                    (ROOT / "participant" / "input" / "target.json", hidden / "target.json")):
            if destination.exists():
                raise ValueError("snapshot already exists; do not silently refreeze")
            print("*** Add File: " + str(destination))
            print("\n".join("+" + line for line in source.read_text().splitlines()))
        print("*** End Patch")
        return
    write_json(ROOT / "participant" / "input" / "model.json", bdg.SPEC)
    for split, offset in (("train", 12001), ("calibration", 23001)):
        episodes = []
        for family_index, family in enumerate(bdg.SPEC["families"]):
            for index in range(2):
                seed = offset + 100 * family_index + index
                scene = bdg.draw_scene(seed, family)
                actions = bdg.uniform_actions()
                values = bdg.simulate(scene, actions)
                episodes.append({"id": split + "-" + family + "-" + str(index), "family": family, "seed": seed,
                                 "scene": scene, "example_actions": actions,
                                 "example_observations": [round(float(value), 12) for value in values]})
        write_json(ROOT / "participant" / "input" / (split + ".json"), {"episodes": episodes})
    seeds_path = hidden / "seeds.json"
    if not seeds_path.exists():
        draws = [{"id": "private-" + str(family_index * 4 + index), "family": family,
                  "seed": secrets.randbits(128)} for family_index, family in enumerate(bdg.SPEC["families"]) for index in range(4)]
        write_json(seeds_path, {"version": "ldos-draws-v1", "draws": draws})
    files = [ROOT / "participant" / "workspace" / "bdg.py", ROOT / "participant" / "input" / "target.json",
             hidden / "forward_model.py", hidden / "target.json", seeds_path]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    write_json(hidden / "frozen_manifest.json", {"version": "freeze-v1", "frozen_before_fresh_agent": True, "sha256": hashes})


if __name__ == "__main__":
    main()
