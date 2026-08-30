import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"
sys.path.insert(0, str(CONCEPT / "evaluator"))
from design_common import load_case, read_design, selected_columns


def logical_dependency(columns, support):
    pivots = {}
    for position, slot in enumerate(support):
        value = columns[slot]
        combination = 1 << position
        while value:
            pivot = value.bit_length()
            if pivot <= 4:
                selected = [support[index] for index in range(len(support)) if combination >> index & 1]
                return selected, value
            if pivot not in pivots:
                pivots[pivot] = value, combination
                break
            previous, previous_combination = pivots[pivot]
            value ^= previous
            combination ^= previous_combination
    return None


axes = read_design(CONCEPT / "champions/generation_1/design.json")
supports = json.loads((CONCEPT / "evaluator/hidden/supports.json").read_text())
certificates = []
for identifier, records in supports.items():
    path = CONCEPT / "evaluator/hidden" / (identifier + ".json.gz")
    case = load_case(path)
    columns = selected_columns(case, axes)
    counts = {}
    for sample_index, record in enumerate(records):
        if counts.get(record["family"], 0) >= 3:
            continue
        result = logical_dependency(columns, record["support"])
        if result is None:
            continue
        combination, logical_mask = result
        recomputed = 0
        for slot in combination:
            recomputed ^= columns[slot]
        if not 0 < recomputed < 16 or recomputed != logical_mask or not set(combination) <= set(record["support"]):
            raise ValueError("invalid logical counterexample")
        counts[record["family"]] = counts.get(record["family"], 0) + 1
        certificates.append({"case": identifier, "family": record["family"], "sample_index": sample_index,
                             "case_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "flagged_support": record["support"], "logical_combination_slots": combination,
                             "logical_mask": logical_mask, "zero_syndrome_verified": True})
report = {"design": axes, "certificates": certificates,
          "note": "Each selected fault combination is contained in a valid flagged support, has exactly zero syndrome, and changes at least one of the four logical Pauli coordinates. These are exact counterexamples to complete correctability for the champion, not minimum-weight certificates or an impossibility proof for other designs."}
(CONCEPT / "adversary/ratchet_1_counterexamples.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"verified_certificates": len(certificates),
                  "combination_sizes": [len(record["logical_combination_slots"]) for record in certificates]}, indent=2))
