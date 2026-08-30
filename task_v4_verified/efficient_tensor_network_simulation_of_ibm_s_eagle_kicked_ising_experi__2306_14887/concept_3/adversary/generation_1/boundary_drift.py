import json
import time

import numpy as np

from physics import HERE, ROOT, OLD_SCALE, champion, fast
from broad_search import confirm


def main():
    started = time.monotonic()
    generator = np.random.default_rng(9172887)
    angles = champion()
    prior_worst = np.load(ROOT / "champions" / "generation_1" / "worst_errors.npy", allow_pickle=False)[0]
    signs = 1 - 2 * ((np.arange(4096)[:, None] >> np.arange(12)) & 1)
    exhaustive = np.c_[np.repeat(prior_worst[None, :], 4096, axis=0), 0.01 * signs]
    coherent_old = generator.choice([-1, 1], size=(768, 15)) * OLD_SCALE
    coherent_patterns = np.ones((768, 12))
    coherent_patterns[256:512] = np.r_[np.ones(6), -np.ones(6)]
    coherent_patterns[512:] = 1 - 2 * np.asarray([0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0])
    coherent = np.c_[coherent_old, 0.01 * coherent_patterns]
    mixed = np.c_[generator.choice([-1, 1], size=(512, 15)) * OLD_SCALE,
                  0.01 * generator.choice([-1, 1], size=(512, 12))]
    interior = np.c_[(2 * generator.beta(0.5, 0.5, (512, 15)) - 1) * OLD_SCALE,
                     generator.uniform(-0.01, 0.01, (512, 12))]
    scenarios = np.r_[exhaustive, coherent, mixed, interior]
    scores = []
    for start in range(0, len(scenarios), 256):
        batch, _ = fast(angles, scenarios[start:start + 256])
        scores.extend(batch.tolist())
        if len(scores) % 1024 == 0:
            print(json.dumps({"cases": len(scores), "minimum": min(scores), "seconds": time.monotonic() - started}), flush=True)
    scores = np.asarray(scores)
    np.savez_compressed(HERE / "boundary_drift_cases.npz", scenarios=scenarios, fidelities=scores)
    families = {"all_4096_local_z_signs_at_old_worst": (0, 4096),
                "coherent_z_with_random_old_vertices": (4096, 4864),
                "random_joint_old_and_z_vertices": (4864, 5376),
                "independent_joint_interiors": (5376, 5888)}
    summaries = {}
    selected = set(np.argsort(scores)[:16].tolist())
    for name, (first, last) in families.items():
        worst = first + int(np.argmin(scores[first:last]))
        selected.add(worst)
        summaries[name] = {"cases": last - first, "minimum": float(scores[worst]),
                           "below_095": int(np.sum(scores[first:last] < 0.95))}
    confirmed = [confirm(angles, scenarios[index], scores[index], "boundary_drift", 0.01)
                 for index in sorted(selected, key=lambda index: scores[index])]
    report = {"model": "PROPOSED_EXTENSION_NOT_ORIGINAL_TASK", "amplitude_bound": 0.01,
              "case_count": len(scenarios), "minimum": float(scores.min()),
              "families": summaries, "independently_confirmed": confirmed,
              "seconds": time.monotonic() - started, "not_a_continuum_certificate": True}
    (HERE / "boundary_drift_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"boundary_drift": summaries, "minimum": float(scores.min()), "seconds": report["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
