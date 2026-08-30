#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator" / "hidden"


def serialize(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_new(path, payload, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
    if private:
        path.chmod(0o600)


def main():
    destinations = [ROOT / "participant/input/target.json", HIDDEN / "target.json",
                    HIDDEN / "planted/design.json", HIDDEN / "frozen_manifest.json",
                    ROOT / "evaluator/validator.py", ROOT / "participant/input/target.sha256"]
    if any(path.exists() for path in destinations):
        raise SystemExit("Frozen artifacts already exist; refusing to regenerate or overwrite.")
    generator = secrets.SystemRandom()
    pair_count, occupied_count = 4096, 768
    extra_zeros = pair_count - 2 * occupied_count
    bars = sorted(generator.sample(range(extra_zeros + occupied_count - 1), occupied_count - 1))
    boundaries = [-1] + bars + [extra_zeros + occupied_count - 1]
    gaps = [boundaries[index + 1] - boundaries[index] + 1 for index in range(occupied_count)]
    weights = [1] * 512 + [2] * 256
    generator.shuffle(weights)
    values = [0] * pair_count
    position = generator.randrange(pair_count)
    for gap, weight in zip(gaps, weights):
        values[position] = weight
        position = (position + gap) % pair_count
    assert sum(gaps) == pair_count and min(gaps) >= 2
    assert [values.count(value) for value in (0, 1, 2)] == [3328, 512, 256]
    assert all(not (values[slot] and values[(slot + 1) % pair_count]) for slot in range(pair_count))
    occupied = [(slot, value) for slot, value in enumerate(values) if value]
    correlations = [0] * pair_count
    for source, source_weight in occupied:
        for destination, destination_weight in occupied:
            correlations[(destination - source) % pair_count] += source_weight * destination_weight
    target = {"generation": 2, "instance_id": "planar-antipodal-eec-8192-v2", "schema_version": 1,
              "direction_count": 8192, "pair_count": pair_count, "allowed_values": [0, 1, 2],
              "counts": {"0": 3328, "1": 512, "2": 256}, "energy_integer_sum": 1024,
              "min_empty_between_occupied": 1, "cyclic_autocorrelation": correlations,
              "max_submission_bytes": 131072, "attempt_time_limit_seconds": 3600,
              "lag_families": [[0, 1024], [1024, 2048], [2048, 3072], [3072, 4096]],
              "family_intervals": "half-open", "core_target": "exact equality at all 4096 lags",
              "source_definition": "arXiv:1801.03219 equations (1)-(2), ordered pairs including self-pairs"}
    target_bytes = serialize(target)
    checker_bytes = (ROOT / "participant/check.py").read_bytes()
    plant_bytes = serialize({"schema_version": 1, "a": values})
    digest = hashlib.sha256(target_bytes).hexdigest()
    manifest = {"generation": 2, "target_sha256": digest,
                "validator_sha256": hashlib.sha256(checker_bytes).hexdigest(),
                "planted_sha256": hashlib.sha256(plant_bytes).hexdigest(),
                "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
                "sampling": "one SystemRandom cyclic gap composition, rotation, and shuffled nonzero labels",
                "public_seed": None, "solver_based_selection": False,
                "private_witness": "planted/design.json", "staging_only": True}
    write_new(destinations[2], plant_bytes, private=True)
    write_new(destinations[4], checker_bytes, private=True)
    write_new(destinations[1], target_bytes, private=True)
    write_new(destinations[0], target_bytes)
    write_new(destinations[3], serialize(manifest), private=True)
    write_new(destinations[5], f"{digest}  target.json\n".encode("ascii"))
    HIDDEN.chmod(0o700)
    (HIDDEN / "planted").chmod(0o700)
    print(json.dumps({"stage": "frozen_private_generation_2", "target_sha256": digest,
                      "frozen_at_utc": manifest["frozen_at_utc"], "witness_disclosed": False}), flush=True)


if __name__ == "__main__":
    main()
