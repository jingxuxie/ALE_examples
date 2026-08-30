import datetime
import hashlib
import json
from pathlib import Path
import secrets

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
GENERATION_ONE = ROOT.parent.parent


def encode(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def make_protocol(seed, case_set):
    protocol = json.loads((GENERATION_ONE / "participant" / "input" / "protocol.json").read_text())
    protocol["task_id"] = "pal_huse_spectral_center_falsification_g2_v1"
    protocol["case_set"] = case_set
    protocol["targets"]["members_required"] = 24
    protocol["targets"]["coverage_fraction"] = 0.75
    protocol.pop("offset_namespace", None)
    protocol["generator"] = {"algorithm": "sha256-u64-centered-v1", "seed_bits": 256, "members_per_family": 32}
    if case_set == "public_calibration":
        protocol["generator"]["seed_hex"] = seed
    for family in protocol["families"]:
        offsets = []
        for member in range(32):
            values = []
            for site in range(12):
                message = f"{seed}|{family['name']}|{member}|{site}".encode("ascii")
                number = int.from_bytes(hashlib.sha256(message).digest()[:8], "big")
                values.append(2.0 * number / (2 ** 64 - 1) - 1.0)
            values = np.asarray(values)
            offsets.append((family["amplitude_before_centering"] * (values - values.mean())).tolist())
        family["offsets"] = offsets
    return protocol


def main():
    public_path = ROOT / "participant" / "input" / "protocol.json"
    private_path = ROOT / "evaluator" / "hidden" / "protocol.json"
    if public_path.exists() or private_path.exists():
        raise RuntimeError("banks already generated; never replace committed probes")
    public_seed, private_seed = secrets.token_hex(32), secrets.token_hex(32)
    assert public_seed != private_seed
    public_bytes = encode(make_protocol(public_seed, "public_calibration"))
    private_bytes = encode(make_protocol(private_seed, "private_replication"))
    public_path.write_bytes(public_bytes)
    private_path.write_bytes(private_bytes)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    commitment = {"schema_version": 1, "task_id": "pal_huse_spectral_center_falsification_g2_v1",
                  "algorithm": "sha256", "encoding": "exact UTF-8 protocol.json bytes including trailing newline",
                  "committed_at_utc": timestamp,
                  "private_protocol_sha256": hashlib.sha256(private_bytes).hexdigest(),
                  "public_protocol_sha256": hashlib.sha256(public_bytes).hexdigest(),
                  "families": 4, "members_per_family": 32, "private_perturbations": 128}
    for destination in (ROOT / "participant" / "input", ROOT / "evaluator" / "hidden"):
        (destination / "commitment.json").write_bytes(encode(commitment))
    (ROOT / "adversary" / "seed_manifest.json").write_bytes(encode({"public_seed_hex": public_seed,
        "private_seed_hex": private_seed, "committed_at_utc": timestamp, "generated_before_any_scoring": True}))
    stress = json.loads((GENERATION_ONE / "adversary" / "champion_stress.json").read_text())
    evidence = {"stress_summary": stress["summary"], "stress_sha256": hashlib.sha256(
        (GENERATION_ONE / "adversary" / "champion_stress.json").read_bytes()).hexdigest(),
        "old_replication_protocols_sha256": hashlib.sha256(
        (GENERATION_ONE / "adversary" / "private_replication_protocols.json").read_bytes()).hexdigest(),
        "new_banks_reuse_old_offsets": False, "previous_fresh_code_or_witness_copied": False}
    (ROOT / "adversary" / "ratchet_evidence.json").write_bytes(encode(evidence))
    reference = ROOT / "adversary" / "privileged_reference"
    reference.mkdir(exist_ok=True)
    (reference / "witness.json").write_bytes((GENERATION_ONE / "adversary" / "champions" / "witness.json").read_bytes())
    provenance = {"source": "generation-one original PUBLIC participant/baseline/solve.py",
                  "source_sha256": hashlib.sha256((GENERATION_ONE / "participant" / "baseline" / "solve.py").read_bytes()).hexdigest(),
                  "changes": ["public seed 21992", "129-spectrum resource count", "explicit public-calibration label"],
                  "champion_code_used": False, "witness_seeded": False}
    (ROOT / "adversary" / "baseline_provenance.json").write_bytes(encode(provenance))
    print(json.dumps(commitment, indent=2))


if __name__ == "__main__":
    main()
