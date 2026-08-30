#!/usr/bin/env python3
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator" / "hidden"


def write_new(path, payload, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
    if private:
        path.chmod(0o600)


def serialize(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main():
    paths = [ROOT / "participant" / "input" / "target.json", HIDDEN / "target.json",
             HIDDEN / "planted" / "design.json", HIDDEN / "frozen_manifest.json"]
    if any(path.exists() for path in paths):
        raise SystemExit("Target already exists or freeze is incomplete; refusing to regenerate.")
    generator = secrets.SystemRandom()
    occupied_count = 96
    extra_zeros = 512 - 2 * occupied_count
    bars = sorted(generator.sample(range(extra_zeros + occupied_count - 1), occupied_count - 1))
    boundaries = [-1] + bars + [extra_zeros + occupied_count - 1]
    gaps = [boundaries[index + 1] - boundaries[index] + 1 for index in range(occupied_count)]
    weights = [1] * 64 + [2] * 32
    generator.shuffle(weights)
    values = [0] * 512
    position = generator.randrange(512)
    for gap, weight in zip(gaps, weights):
        values[position] = weight
        position = (position + gap) % 512
    assert sum(gaps) == 512 and min(gaps) >= 2
    assert [values.count(value) for value in (0, 1, 2)] == [416, 64, 32]
    assert all(not (values[slot] and values[(slot + 1) % 512]) for slot in range(512))
    correlations = [sum(values[slot] * values[(slot + lag) % 512] for slot in range(512))
                    for lag in range(512)]
    target = {
        "instance_id": "planar-antipodal-eec-1024-v1", "schema_version": 1,
        "direction_count": 1024, "pair_count": 512, "allowed_values": [0, 1, 2],
        "counts": {"0": 416, "1": 64, "2": 32}, "energy_integer_sum": 128,
        "min_empty_between_occupied": 1, "cyclic_autocorrelation": correlations,
        "source_definition": "arXiv:1801.03219v2 equations (1)-(2), ordered pairs including self-pairs",
        "max_submission_bytes": 16384, "core_target": "exact equality at all 512 lags",
        "lag_families": [[0, 128], [128, 256], [256, 384], [384, 512]],
        "family_intervals": "half-open",
    }
    payload = serialize(target)
    digest = hashlib.sha256(payload).hexdigest()
    write_new(paths[2], serialize({"schema_version": 1, "a": values}), private=True)
    write_new(paths[1], payload, private=True)
    write_new(paths[0], payload)
    manifest = {
        "target_sha256": digest,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation": 0,
        "sampling": "one SystemRandom cyclic independent support via uniform gap composition, shuffled ternary labels",
        "public_seed": None,
        "rejection_or_solver_based_selection": False,
        "planted_witness": "planted/design.json",
        "planted_sha256": hashlib.sha256(paths[2].read_bytes()).hexdigest(),
        "target_status": "immutable before all baseline and fresh-agent attempts",
    }
    write_new(paths[3], serialize(manifest), private=True)
    write_new(ROOT / "participant" / "input" / "target.sha256",
              f"{digest}  target.json\n".encode("ascii"))
    HIDDEN.chmod(0o700)
    (HIDDEN / "planted").chmod(0o700)
    print(json.dumps({"target_sha256": digest, "frozen_at_utc": manifest["frozen_at_utc"],
                      "witness_disclosed": False}))


if __name__ == "__main__":
    main()
