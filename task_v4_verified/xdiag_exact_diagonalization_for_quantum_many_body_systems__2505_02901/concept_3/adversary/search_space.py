import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import LOWER, UPPER


def main():
    random = np.random.default_rng(499716025)
    cases = []
    for family in ("weak_exchange_large_field", "mixed_sign_disorder", "near_symmetry", "strong_frustration"):
        for parameter_index in range(6):
            parameters = LOWER + (UPPER - LOWER) * random.uniform(0.01, 0.99, 20)
            if family == "weak_exchange_large_field":
                parameters[:6] = random.uniform(0.55, 0.7, 6)
                parameters[6:11] = random.uniform(0.43, 0.5, 5) * random.choice([-1, 1])
                parameters[11] = random.uniform(0.3, 0.55)
                parameters[12:14] = random.uniform(0.05, 0.11, 2)
            elif family == "mixed_sign_disorder":
                parameters[:6] = random.uniform(0.56, 0.85, 6)
                parameters[6:11] = random.uniform(0.35, 0.49, 5) * random.choice([-1, 1], 5)
                parameters[12:14] = random.uniform(0.05, 0.2, 2)
            elif family == "near_symmetry":
                parameters[:6] = random.choice([0.55, 1.0, 1.45])
                parameters[6:11] = random.uniform(-0.012, 0.012, 5) if parameter_index % 2 else 0.0
                parameters[11] = random.choice([0.3, 1.0, 1.7])
                parameters[12:14] = random.choice([0.05, 0.275, 0.5])
            elif family == "strong_frustration":
                parameters[:6] = random.uniform(0.55, 0.85, 6)
                parameters[12:14] = random.uniform(0.43, 0.5, 2)
                parameters[11] = random.uniform(1.45, 1.7)
                parameters[6:11] = random.uniform(-0.1, 0.1, 5)
            if parameter_index % 2:
                parameters[14:20] = random.uniform(0.04, 0.05, 6)
            assert np.all(parameters >= LOWER) and np.all(parameters <= UPPER)
            for repetition in range(2):
                cases.append({"id": f"device-{int(random.integers(10000000, 99999999))}", "family": family, "parameters": parameters.tolist(), "noise_seed": int(random.integers(2**31)), "parameter_cluster": f"{family}-{parameter_index}", "noise_repetition": repetition})
    (ROOT / "adversary/stress_devices.json").write_text(json.dumps(cases, indent=2) + "\n")
    manifest = {"parameter_vectors": len(cases) // 2, "independent_noise_repetitions": 2, "device_interactions": len(cases), "all_within_original_public_parameter_box": True, "families": {"weak_exchange_large_field": "Local fields separate sites energetically while weak exchange suppresses transfer; nonlinear spectral aliases and weak information compete.", "mixed_sign_disorder": "Independent field-sign patterns test multimodal inference beyond globally aligned disorder.", "near_symmetry": "Exact or approximate translation/spin symmetries create spectral degeneracies; diagonalization remains well-defined.", "strong_frustration": "Comparable first- and second-neighbor terms and large anisotropy produce crowded many-body spectra."}, "selection_rule": "Parameter-space sweep fixed without selecting measurement-noise realizations. Repeat each parameter vector twice to distinguish persistent model/design failures from noise outliers."}
    (ROOT / "adversary/search_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
