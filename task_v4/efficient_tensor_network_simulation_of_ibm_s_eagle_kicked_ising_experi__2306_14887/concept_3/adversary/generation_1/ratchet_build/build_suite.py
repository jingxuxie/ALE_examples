import hashlib
import itertools
import json
from pathlib import Path
import subprocess

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def write_json(path, value):
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if path.exists():
        patch = "*** Begin Patch\n*** Update File: " + str(path) + "\n@@\n"
        patch += "".join("-" + line + "\n" for line in path.read_text().splitlines())
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)


def main():
    previous = ROOT / "generations" / "generation_0"
    original = json.loads((previous / "evaluator" / "hidden" / "scenarios.json").read_text())["scenarios"]
    hidden = [dict(row, name="zero_" + row["name"], subfamily="original_zero_drift_" + row["family"],
                   z_drift_radians_per_layer=[0.0] * 12) for row in original]
    public = [dict(row, z_drift_radians_per_layer=[0.0] * 12)
              for row in json.loads((previous / "participant" / "input" / "training_scenarios.json").read_text())["scenarios"]]
    patterns = [np.ones(12), (-1.0) ** np.arange(12), np.r_[np.ones(6), -np.ones(6)],
                1 - 2 * np.asarray([0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0])]
    def entry(family, subfamily, old, drift):
        return {"name": f"{subfamily}_{len(hidden)}", "family": family, "subfamily": subfamily,
                "gain_a": float(old[0]), "gain_b": float(old[1]), "zz_common": float(old[2]),
                "zz_local": np.asarray(old[3:15]).tolist(),
                "z_drift_radians_per_layer": np.asarray(drift).tolist()}
    for pattern in patterns + [np.eye(12)[site] for site in (0, 3, 6, 9)]:
        for sign in (-1, 1):
            row = entry("core", "nominal_drift", np.zeros(15), sign * 0.01 * pattern)
            hidden.append(row)
            public.append(dict(row, family="training"))
    for signs in itertools.product((-1, 1), repeat=3):
        old = np.r_[np.asarray(signs) * [0.025, 0.025, 0.015], np.full(12, signs[2] * 0.005)]
        for pattern in patterns:
            for sign in (-1, 1):
                hidden.append(entry("worst_family", "coherent_joint_stress", old, sign * 0.01 * pattern))
    boundary = np.load(HERE.parent / "boundary_drift_cases.npz", allow_pickle=False)
    for index in np.argsort(boundary["fidelities"])[:16]:
        row = boundary["scenarios"][index]
        hidden.append(entry("worst_family", "adversarial_joint_stress", row[:15], row[15:]))
    generator = np.random.default_rng(5272887)
    for first, last in ((4864, 5376), (5376, 5888)):
        for index in generator.choice(np.arange(first, last), 32, replace=False):
            row = boundary["scenarios"][index]
            hidden.append(entry("heldout", "local_disorder", row[:15], row[15:]))
    assert len(hidden) == 223 and len(public) == 31
    payload = {"ratchet_generation": 1, "threshold": 0.95,
               "static_z_bound_radians_per_site_per_layer": 0.01, "scenarios": hidden}
    write_json(ROOT / "evaluator" / "hidden" / "scenarios.json", payload)
    write_json(ROOT / "participant" / "input" / "training_scenarios.json", {"scenarios": public})
    digest = hashlib.sha256((ROOT / "evaluator" / "hidden" / "scenarios.json").read_bytes()).hexdigest()
    path = ROOT / "evaluator" / "evaluate.py"
    old_line = next(line for line in path.read_text().splitlines() if line.startswith("SCENARIO_DIGEST ="))
    patch = "*** Begin Patch\n*** Update File: " + str(path) + "\n@@\n-" + old_line
    patch += '\n+SCENARIO_DIGEST = "' + digest + '"\n*** End Patch\n'
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    counts = {family: sum(row["family"] == family for row in hidden) for family in ("core", "worst_family", "heldout")}
    write_json(HERE / "suite_manifest.json", {"scenario_sha256": digest, "scenarios": 223,
                                             "zero_drift": 63, "public_examples": 31, "family_counts": counts})
    print(json.dumps({"digest": digest, "counts": counts}), flush=True)


if __name__ == "__main__":
    main()
