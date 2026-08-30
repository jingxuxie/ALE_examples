import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/input"))
from gl_model import load_case
from independent import checked_field, energy_gradient, read_case


def vortex_counts(model, field):
    phase_x = np.angle(np.conjugate(field[:, :-1]) * model.ux * field[:, 1:])
    phase_y = np.angle(np.conjugate(field[:-1, :]) * model.uy * field[1:, :])
    flux = model.ax[:-1, :] + model.ay[:, 1:] - model.ax[1:, :] - model.ay[:, :-1]
    winding = np.rint((phase_x[:-1, :] + phase_y[:, 1:] - phase_x[1:, :] - phase_y[:, :-1] + flux) / (2 * np.pi))
    full = model.mask[:-1, :-1] & model.mask[1:, :-1] & model.mask[:-1, 1:] & model.mask[1:, 1:]
    return {"positive_full_plaquettes": int(np.sum(np.maximum(winding[full], 0))), "negative_full_plaquettes": int(np.sum(np.maximum(-winding[full], 0))), "hole_windings_included": False, "interpretation": "gauge-covariant discrete circulation diagnostic, not an imposed constraint"}


def main():
    manifest = read_case(ROOT / "evaluator/hidden/manifest.json")
    generator = np.random.default_rng(401209)
    diagnostics = []
    for reference in manifest["cases"]:
        model = load_case(ROOT / reference["case_path"])
        vector = generator.normal(size=model.size * 2) * 0.7
        public_energy, gradient = model.objective(vector)
        direction = generator.normal(size=vector.size)
        direction /= np.linalg.norm(direction)
        exact = float(np.dot(gradient, direction))
        numeric = (model.objective(vector + 1e-5 * direction)[0] - model.objective(vector - 1e-5 * direction)[0]) / 2e-5
        independent_energy, independent_gradient, unused = energy_gradient(model.case, model.unpack(vector))
        baseline = checked_field(ROOT / reference["baseline_path"], model.case)
        witness = checked_field(ROOT / reference["witness_path"], model.case)
        details = {"case_id": reference["case_id"], "family": reference["family"], "shape": list(model.shape), "active_sites": model.size, "real_variables": 2 * model.size, "directional_derivative_relative_error": abs(numeric - exact) / max(1, abs(exact)), "independent_energy_absolute_error": abs(public_energy - independent_energy), "independent_gradient_max_error": float(np.max(np.abs(gradient - model.pack(independent_gradient)))), "baseline_vorticity": vortex_counts(model, baseline), "witness_vorticity": vortex_counts(model, witness), "metastable_minima": {}}
        for kind in ("multistart", "expensive"):
            history = read_case(ROOT / "attempts" / kind / (reference["case_id"] + "_history.json"))
            energies = [item["energy"] for item in history if item["gradient_rms"] <= 0.002]
            details["metastable_minima"][kind] = {"converged_starts": len(energies), "distinct_energies_at_1e-4": len(set(round(energy, 4) for energy in energies)), "minimum_energy": min(energies), "maximum_energy": max(energies)}
        if details["directional_derivative_relative_error"] > 1e-6 or details["independent_gradient_max_error"] > 1e-10:
            raise RuntimeError("scientific diagnostic failed")
        diagnostics.append(details)
    (ROOT / "attempts/scientific_validation.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
