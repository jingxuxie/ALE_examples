import json
from pathlib import Path
import sys

import bdg


def main():
    metadata = json.loads(sys.stdin.readline())
    private_relative = Path("evaluator/hidden/seeds.json")
    roots = (Path("/participant").parent, Path(__file__).resolve().parents[1], Path("/participant").resolve().parent)
    for root in roots:
        if (root / private_relative).exists():
            raise RuntimeError("private seeds exposed")
    for destination in ("/output/probe.txt", "/tmp/probe.txt"):
        if Path(destination).exists():
            raise RuntimeError("scratch persisted across episodes")
        Path(destination).write_text("scratch works")
    try:
        Path("/participant/forbidden.txt").write_text("unexpected")
    except OSError:
        pass
    else:
        raise RuntimeError("participant writable")
    try:
        Path("/submission/forbidden.txt").write_text("unexpected")
    except OSError:
        pass
    else:
        raise RuntimeError("submission writable")
    print(json.dumps({"type": "query", "site": 12, "energy_index": 20}), flush=True)
    observation = json.loads(sys.stdin.readline())
    scene = bdg.draw_scene(71, "dispersed")
    print(json.dumps({"type": "final", "estimate": scene}), flush=True)
    print(json.dumps({"public_metadata_only": set(metadata) == {"type", "protocol", "model", "target"},
                      "observation_keys": sorted(observation), "scratch_ok": True, "mounts_read_only": True}), file=sys.stderr)


if __name__ == "__main__":
    main()
