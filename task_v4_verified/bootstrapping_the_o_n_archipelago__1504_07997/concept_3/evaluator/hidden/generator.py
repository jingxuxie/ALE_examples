"""Private deterministic seeds; the entire resource distribution is public."""

import hashlib
import hmac
import json
from pathlib import Path

from model import FAMILIES, generate


def suite(split, per_family, seed_file=None):
    source = Path(seed_file) if seed_file else Path(__file__).with_name("seeds.json")
    key = bytes.fromhex(json.loads(source.read_text())["master_key_hex"])
    if len(key) < 16:
        raise ValueError("private key must contain at least 128 bits")

    def derive(label):
        return hmac.new(key, label.encode(), hashlib.sha256).digest()

    records = []
    for family in FAMILIES:
        for repeat in range(per_family):
            label = f"{split}/{family}/{repeat}"
            parameter_seed = int.from_bytes(derive("parameters/" + label)[:16], "big")
            noise_seed = int.from_bytes(derive("noise/" + label)[:16], "big")
            records.append({
                "id": derive("identifier/" + label).hex()[:16],
                "instance": generate(parameter_seed, family), "noise_seed": noise_seed,
                "order": derive("order/" + label).hex(),
            })
    return sorted(records, key=lambda record: record["order"])
