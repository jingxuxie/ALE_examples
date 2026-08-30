import hashlib
import json
from pathlib import Path
import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE / "concept_1" / "generations" / "generation_2"
PARTITIONS = {"quartets": [4, 4, 4, 4, 4], "quintets": [5, 5, 5, 5], "mixed": [6, 7, 7]}


def material(partition, strength, seed):
    rng = np.random.default_rng(seed)
    couplings, fields = np.zeros((20, 20)), np.zeros(20)
    start = 0
    for count in partition:
        block = np.full((count, count), -strength)
        np.fill_diagonal(block, 0)
        couplings[start:start + count, start:start + count] = block
        fields[start:start + count] = strength * (1 if count % 2 == 0 else 2) + rng.normal(0, 0.02, count)
        start += count
    disorder = np.tril(rng.normal(0, 0.006, (20, 20)), -1)
    couplings += disorder + disorder.T
    order, gauge = rng.permutation(20), rng.choice([-1., 1.], 20)
    couplings = couplings[np.ix_(order, order)] * gauge[:, None] * gauge[None, :]
    fields = fields[order] * gauge
    return {"n": 20, "couplings": couplings.tolist(), "fields": fields.tolist()}


def main():
    for folder in ("participant/input", "evaluator/hidden", "attempts", "champions", "adversary"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    cases = []
    for family_index, (family, partition) in enumerate(PARTITIONS.items()):
        public = material(partition, (1.6, 2.1, 2.6)[family_index], 431707 + family_index)
        (ROOT / "participant" / "input" / ("example_" + family + ".json")).write_text(json.dumps(public))
        for index, strength in enumerate((1.9, 2.5, 3.1)):
            value = material(partition, strength, 710371 + 131 * family_index + 97 * index)
            identifier = family + "_" + str(index)
            raw = json.dumps(value).encode()
            (ROOT / "evaluator" / "hidden" / (identifier + ".json")).write_bytes(raw)
            cases.append({"id": identifier, "family": family, "file": identifier + ".json", "sha256": hashlib.sha256(raw).hexdigest()})
    (ROOT / "evaluator" / "hidden" / "manifest.json").write_text(json.dumps({"version": 2, "cases": cases, "families": list(PARTITIONS), "targets_fixed_before_fresh": True}, indent=2))
    source = PACKAGE / "concept_1" / "adversary" / "champion1_modular_stress" / "results.json"
    records = json.loads(source.read_text())
    audit = {"parent_champion": "concept_1/champions/generation_1", "searched_cases": 44,
             "new_family_cases": len(records), "absolute_kl_failures": [record for record in records if record.get("kl", 0) > 0.12],
             "root_cause": "Competing local magnetization sectors induce nonlinear conditional structure that the champion's hard prefix partition and shallow component fits do not capture accurately.",
             "scientific_scope": "Same finite Ising Hamiltonian and artifact capacity; denser modular frustration exposes a measurable compression gap, not hidden trivia or numerical instability.",
             "ratchet": 1, "known_passing_solution": False,
             "target_rationale": "At least60% overall and50% per-family improvement, with .04/.06-nat absolute gaps. These targets are fixed before the challenger and remain open until demonstrated."}
    (ROOT / "adversary" / "ratchet_rationale.json").write_text(json.dumps(audit, indent=2))
    (ROOT / "status.json").write_text(json.dumps({"status": "built_not_tested", "verification_mode": "A", "generation": 2, "ratchet_generations": 1, "solvability": "unknown"}, indent=2))


if __name__ == "__main__":
    main()
