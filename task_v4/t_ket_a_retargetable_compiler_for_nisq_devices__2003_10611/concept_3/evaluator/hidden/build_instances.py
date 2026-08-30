import hashlib
import json
import math
from pathlib import Path
import random
import secrets


ROOT = Path(__file__).resolve().parents[2]


def grid_edges(height, width):
    edges = []
    for row in range(height):
        for column in range(width):
            wire = row * width + column
            if column + 1 < width:
                edges.append([wire, wire + 1])
            if row + 1 < height:
                edges.append([wire, wire + width])
    return edges


def branch_edges(size):
    spine = size // 3
    edges = [[wire, wire + 1] for wire in range(spine - 1)]
    for offset, wire in enumerate(range(spine, size)):
        if offset < spine:
            edges.append([offset, wire])
        else:
            edges.append([wire - spine, wire])
    return edges


def plant(case_id, family, size, edges, rounds, obligations, seed):
    generator = random.Random(seed)
    rows = [1 << wire for wire in range(size)]
    clocks = [0] * size
    gates = []
    appearances = {}
    last_use = [None] * size
    for round_index in range(rounds):
        candidates = edges[:]
        generator.shuffle(candidates)
        used = set()
        for first, second in candidates:
            if first in used or second in used:
                continue
            control, target = (first, second) if generator.randrange(2) else (second, first)
            pair = (control, target)
            if last_use[control] == pair and last_use[target] == pair:
                control, target = target, control
                pair = (control, target)
            used.update((control, target))
            rows[target] ^= rows[control]
            level = 1 + max(clocks[control], clocks[target])
            clocks[control] = level
            clocks[target] = level
            last_use[control] = pair
            last_use[target] = pair
            gates.append([control, target])
            mask = rows[target]
            if rounds // 5 <= round_index < rounds * 9 // 10 and mask.bit_count() >= 3:
                appearances.setdefault(mask, (round_index, len(gates), target))
    eligible = [mask for mask in appearances if mask not in rows]
    generator.shuffle(eligible)
    if len(eligible) < obligations:
        raise RuntimeError("insufficient internal parity diversity")
    selected = []
    for bucket in range(4):
        bucket_masks = [mask for mask in eligible if min(3, 4 * appearances[mask][0] // rounds) == bucket]
        selected.extend(bucket_masks[: obligations // 4])
    remaining = [mask for mask in eligible if mask not in selected]
    selected.extend(remaining[: obligations - len(selected)])
    required = sorted(selected)
    case = {
        "id": case_id,
        "family": family,
        "n": size,
        "edges": sorted([sorted(edge) for edge in edges]),
        "target_rows": rows,
        "required_parities": required,
        "max_cnots": math.ceil(len(gates) * 1.12),
        "max_depth": math.ceil(max(clocks) * 1.15),
    }
    audit = {
        "seed": seed,
        "planted_cnots": len(gates),
        "planted_depth": max(clocks),
        "obligation_locations": {str(mask): list(appearances[mask][1:]) for mask in required},
    }
    return case, gates, audit


def main():
    freeze_path = ROOT / "evaluator/hidden/freeze.json"
    if freeze_path.exists():
        raise SystemExit("Target already frozen. Refusing to regenerate or retune.")
    specifications = [
        ("ladder_12", "ladder", 12, grid_edges(2, 6), 32, 20),
        ("ladder_16", "ladder", 16, grid_edges(2, 8), 38, 26),
        ("grid_16", "grid", 16, grid_edges(4, 4), 36, 28),
        ("grid_20", "grid", 20, grid_edges(4, 5), 42, 34),
        ("branched_14", "branched", 14, branch_edges(14), 42, 24),
        ("branched_18", "branched", 18, branch_edges(18), 48, 30),
    ]
    cases = []
    circuits = {}
    audits = {}
    for specification in specifications:
        case, gates, audit = plant(*specification, secrets.randbits(128))
        cases.append(case)
        circuits[case["id"]] = gates
        audits[case["id"]] = audit
    suite = {"schema_version": 1, "instances": cases}
    witness = {"schema_version": 1, "circuits": circuits}
    suite_text = json.dumps(suite, indent=2) + "\n"
    witness_text = json.dumps(witness, separators=(",", ":")) + "\n"
    freeze = {
        "schema_version": 1,
        "frozen_before_agent_launch": True,
        "instances_sha256": hashlib.sha256(suite_text.encode()).hexdigest(),
        "planted_witness_sha256": hashlib.sha256(witness_text.encode()).hexdigest(),
        "freeze_policy": "No instance, budget, scoring, or obligation changes after this freeze; no solver trial used for selection.",
        "audits": audits,
    }
    files = {
        "participant/input/instances.json": suite_text,
        "evaluator/hidden/frozen_instances.json": suite_text,
        "evaluator/hidden/planted_witness.json": witness_text,
        "evaluator/hidden/freeze.json": json.dumps(freeze, indent=2) + "\n",
    }
    print("*** Begin Patch")
    for name, content in files.items():
        print("*** Add File: " + name)
        for line in content.splitlines():
            print("+" + line)
    print("*** End Patch")


if __name__ == "__main__":
    main()
