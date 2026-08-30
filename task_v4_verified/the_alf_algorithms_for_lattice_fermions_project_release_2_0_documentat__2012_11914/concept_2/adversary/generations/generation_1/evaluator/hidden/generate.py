import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def draw_suite(contract, seed, count):
    generator = np.random.default_rng(seed)
    instances = []
    for family in contract["sampling"]["families"]:
        for sample in range(count):
            width, height = contract["sampling"]["lattice_shapes"][sample % 3]
            hopping_x = generator.uniform(*family["tx"])
            if "ty_ratio" in family:
                hopping_y = hopping_x * generator.uniform(*family["ty_ratio"])
                if generator.random() < family["swap_axes_probability"]:
                    hopping_x, hopping_y = hopping_y, hopping_x
            elif family["ty"] == "tx":
                hopping_y = hopping_x
            else:
                hopping_y = generator.uniform(*family["ty"])
            dimer_x = generator.uniform(*family["dx"])
            dimer_y = generator.uniform(*family["dy"])
            strength = generator.uniform(*family["field_strength"])
            stagger = generator.uniform(*family["stagger"])
            chemical = generator.uniform(*family["chemical_potential"])
            if family["field"] == "binary":
                fields = generator.choice([-1.0, 1.0], size=width * height)
            else:
                fields = np.clip(generator.normal(size=width * height), -2.0, 2.0)
            onsite = []
            bonds = []
            for ordinate in range(height):
                for abscissa in range(width):
                    source = abscissa + width * ordinate
                    onsite.append(float(strength * fields[source] + stagger * (-1) ** (abscissa + ordinate) - chemical))
                    for direction in ("X", "Y"):
                        if direction == "X":
                            target = (abscissa + 1) % width + width * ordinate
                            coordinate, hopping, dimer = abscissa, hopping_x, dimer_x
                        else:
                            target = abscissa + width * ((ordinate + 1) % height)
                            coordinate, hopping, dimer = ordinate, hopping_y, dimer_y
                        amplitude = hopping * (1 + dimer * (-1) ** coordinate)
                        amplitude *= generator.uniform(1 - family["disorder"], 1 + family["disorder"])
                        phase = generator.uniform(-family["phase_width"], family["phase_width"])
                        bonds.append([direction + str(coordinate % 2), source, target, float(amplitude), float(phase)])
            instances.append({"id": f"{family['name']}_{sample:02d}", "family": family["name"], "shape": [width, height], "bonds": bonds, "site_potential": onsite})
    return {"schema_version": 1, "bond_record": ["component", "source", "target", "amplitude", "phase"], "instances": instances}


def write_json(path, content):
    path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def main():
    hidden = ROOT / "evaluator/hidden"
    freeze = json.loads((hidden / "target_freeze.json").read_text())
    public = ROOT / "participant/input/spec.json"
    contract = json.loads(public.read_text())
    assert contract["scoring"]["targets"] == freeze["targets"]
    outputs = [hidden / "contract.json", hidden / "instances.json", ROOT / "participant/input/training_instances.json", hidden / "manifest.json"]
    if any(path.exists() for path in outputs):
        raise SystemExit("Refusing to overwrite frozen fixtures; generation is one-shot.")
    write_json(outputs[0], contract)
    write_json(outputs[1], draw_suite(contract, freeze["hidden_seed"], contract["sampling"]["hidden_instances_per_family"]))
    write_json(outputs[2], draw_suite(contract, freeze["training_seed"], contract["sampling"]["training_instances_per_family"]))
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [public, hidden / "target_freeze.json"] + outputs[:3]}
    write_json(outputs[3], {"phase": "frozen_before_calibration_and_design_attempts", "sha256": hashes, "numpy_version": np.__version__, "generator": "numpy.random.default_rng / PCG64", "no_selection_on_errors": True})
    print("Frozen contract and independent training/hidden fixtures generated.")


if __name__ == "__main__":
    main()
