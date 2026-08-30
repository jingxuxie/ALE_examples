import json
from pathlib import Path

import numpy as np
from scipy.special import eval_legendre


ROOT = Path(__file__).resolve().parents[1]


def build_case(seed, family, serial):
    random = np.random.default_rng(seed)
    count = 72
    spins = np.tile([0, 0, 2, 4, 6, 8], count // 6)
    dimensions = spins + 1.15 + random.uniform(0.15, 4.5, count)
    dimensions[spins == 0] += 2.0
    dimensions[0] = 1.511
    if family == "crowded_singlets":
        spins[:24] = 0
        dimensions[1:24] = 3.1 + np.arange(23)*0.035
    times = np.geomspace(0.075, 0.9, 36)
    angles = random.uniform(-0.88, 0.98, len(times))
    orders = np.arange(len(times)) % 4
    if family == "spin_aliases":
        angles = random.uniform(0.78, 0.995, len(times))
    design = np.exp(-times[:, None] * dimensions) * eval_legendre(spins[None, :], angles[:, None])
    design *= (dimensions[None, :] / 8.0)**orders[:, None]
    columns = np.sqrt(np.mean(design**2, axis=0))
    design /= columns
    max_atoms = 7 if serial == 0 else 9
    pool = np.arange(1, 24) if family == "crowded_singlets" else np.arange(1, count)
    support = np.r_[0, np.sort(random.choice(pool, max_atoms-1, replace=False))]
    vectors = random.normal(size=(max_atoms, 2))
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    magnitudes = random.uniform(0.35, 1.0, max_atoms)
    if family == "weak_residues":
        magnitudes[2:5] *= np.array([0.035, 0.07, 0.14])
    if family == "mixed_cancellation":
        vectors[:, 0] = np.sqrt(0.5)
        vectors[:, 1] = np.sqrt(0.5) * np.where(np.arange(max_atoms) % 2, -1.0, 1.0)
    vectors *= magnitudes[:, None]
    vectors[0, 0] = 0.73
    products = np.stack([vectors[:, 0]**2, vectors[:, 0]*vectors[:, 1], vectors[:, 1]**2], axis=1)
    target = design[:, support] @ products
    scales = np.maximum(0.15, np.abs(target))
    instance = {"id": f"{family}_{serial}", "family": family, "max_atoms": max_atoms,
                "trace_budget": float(np.sum(vectors**2)*1.03), "shared_ope_squared": 0.73**2,
                "candidates": [{"dimension": float(delta), "spin": int(spin), "column_scale": float(scale)}
                               for delta, spin, scale in zip(dimensions, spins, columns)],
                "probes": [{"t": float(time), "eta": float(angle), "order": int(order)}
                           for time, angle, order in zip(times, angles, orders)],
                "design": design.tolist(), "target": target.tolist(), "scales": scales.tolist()}
    answer = {"id": instance["id"], "atoms": [{"index": int(index), "ope": vector.tolist()}
                                             for index, vector in zip(support, vectors)]}
    return instance, answer


def main():
    instances, answers = [], []
    families = ["crowded_singlets", "spin_aliases", "mixed_cancellation", "weak_residues"]
    for family_index, family in enumerate(families):
        for serial in range(2):
            instance, answer = build_case(150407997 + 103*family_index + serial, family, serial)
            instances.append(instance)
            answers.append(answer)
    payload = {"model": "column-normalized leading radial partial-wave moment surrogate", "instances": instances}
    (ROOT / "participant/input/instances.json").write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    (ROOT / "evaluator/hidden/instances.json").write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    (ROOT / "adversary/planted.json").write_text(json.dumps({"cases": answers}, indent=2) + "\n")


if __name__ == "__main__":
    main()
