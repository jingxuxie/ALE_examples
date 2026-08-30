import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "concept_1"


def instance(family, seed, index):
    rng = np.random.default_rng(seed)
    count = 18 if family == "dense" else 20
    if family == "dense":
        couplings = rng.normal(size=(count, count)) / np.sqrt(count) * (1.8 + 0.65 * index)
        couplings = np.tril(couplings, -1)
        couplings += couplings.T
        fields = rng.normal(0, 0.04, count)
    elif family == "memory":
        patterns = rng.choice([-1., 1.], (3 + index, count))
        couplings = (2.0 + 0.4 * index) * (patterns.T @ patterns) / count
        perturbation = np.tril(rng.normal(0, 0.025, (count, count)), -1)
        couplings += perturbation + perturbation.T
        np.fill_diagonal(couplings, 0)
        fields = rng.normal(0, 0.025, count)
    else:
        couplings = np.zeros((count, count))
        for row in range(4):
            for column in range(5):
                site = row * 5 + column
                for neighbor in (((row + 1) % 4) * 5 + column, row * 5 + (column + 1) % 5):
                    couplings[site, neighbor] = couplings[neighbor, site] = rng.choice([-1., 1.]) * (0.8 + 0.35 * index)
        fields = rng.normal(0, 0.03, count)
    order = rng.permutation(count)
    gauge = rng.choice([-1., 1.], count)
    couplings = couplings[np.ix_(order, order)] * gauge[:, None] * gauge[None, :]
    fields = fields[order] * gauge
    return {"n": count, "couplings": couplings.tolist(), "fields": fields.tolist()}


def main():
    for directory in ("participant/input", "evaluator/hidden", "attempts", "champions", "adversary"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    cases = []
    for family_index, family in enumerate(("dense", "memory", "lattice")):
        example = instance(family, 311 + family_index, 0)
        name = "sk" if family == "dense" else family
        (ROOT / "participant" / "input" / ("example_" + name + ".json")).write_text(json.dumps(example))
        for index in range(3):
            value = instance(family, 172831 + family_index * 713 + index * 17, index)
            identifier = family + "_" + str(index)
            raw = json.dumps(value).encode()
            filename = identifier + ".json"
            (ROOT / "evaluator" / "hidden" / filename).write_bytes(raw)
            cases.append({"id": identifier, "family": family, "file": filename, "sha256": hashlib.sha256(raw).hexdigest()})
    manifest = {"version": 1, "cases": cases, "families": ["dense", "memory", "lattice"], "generated_before_agents": True}
    (ROOT / "evaluator" / "hidden" / "manifest.json").write_text(json.dumps(manifest, indent=2))
    status = {"concept": "compact_equilibrium_proposals", "verification_mode": "A", "status": "built_not_tested",
              "ratchet_generations": 0, "solvability": "unknown", "target_frozen_before_agents": True}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
