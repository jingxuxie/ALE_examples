from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

import copy
import hashlib
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(CONCEPT / "participant/input"))
from gl_model import GLModel


def physical_flux_error(case, metadata):
    ny, nx = case["shape"]
    rows, columns = np.indices((ny - 1, nx - 1), dtype=float)
    field = metadata["field"]
    wave_x, wave_y = field["wave_x"], field["wave_y"]
    argument_x = wave_x * (columns - (nx - 1) / 2) + field["phase_x"]
    argument_y = wave_y * (rows - (ny - 1) / 2) + field["phase_y"]
    sine_x = np.sin(argument_x + wave_x) - np.sin(argument_x)
    sine_y = np.sin(argument_y + wave_y) - np.sin(argument_y)
    expected = case["h"]**2 * (field["base"] + field["cos_x"] / wave_x * sine_x + field["cos_y"] / wave_y * sine_y + field["cos_xy"] / (wave_x * wave_y) * sine_x * sine_y)
    ax, ay = np.asarray(case["ax"]), np.asarray(case["ay"])
    actual = ax[:-1] + ay[:, 1:] - ax[1:] - ay[:, :-1]
    mask = np.asarray(case["mask"], dtype=bool)
    full = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1] & mask[1:, 1:]
    return float(np.max(abs(actual[full] - expected[full])))


def main():
    generator = np.random.default_rng(770933)
    records = []
    for details in read_case(ROOT / "broad_index.json"):
        name = details["case_id"]
        case = read_case(ROOT / "cases" / (name + ".json"))
        metadata = read_case(ROOT / "metadata" / (name + ".json"))
        model = GLModel(case)
        vector = generator.normal(size=model.size * 2) * 0.4
        energy, gradient = model.objective(vector)
        field = model.unpack(vector)
        independent_energy, independent_gradient, unused = energy_gradient(case, field)
        fd_errors = []
        for unused in range(3):
            direction = generator.normal(size=vector.size)
            direction /= np.linalg.norm(direction)
            derivative = float(np.dot(gradient, direction))
            numeric = (model.objective(vector + 2e-5 * direction)[0] - model.objective(vector - 2e-5 * direction)[0]) / 4e-5
            fd_errors.append(abs(numeric - derivative) / max(1, abs(derivative)))
        gauge = generator.uniform(-5, 5, size=model.shape)
        transformed = copy.deepcopy(case)
        transformed["ax"] = (model.ax + gauge[:, 1:] - gauge[:, :-1]).tolist()
        transformed["ay"] = (model.ay + gauge[1:] - gauge[:-1]).tolist()
        gauge_energy, gauge_gradient, unused = energy_gradient(transformed, field * np.exp(1j * gauge))
        uniform = copy.deepcopy(case)
        uniform["alpha"] = (-np.ones(model.shape)).tolist()
        uniform["beta"] = np.ones(model.shape).tolist()
        uniform["ax"] = np.zeros_like(model.ax).tolist()
        uniform["ay"] = np.zeros_like(model.ay).tolist()
        uniform_energy, unused, uniform_rms = energy_gradient(uniform, model.mask.astype(complex))
        record = {"case_id": name, "finite_difference_max_relative_error": max(fd_errors), "independent_energy_error": abs(energy - independent_energy), "independent_gradient_error": float(np.max(abs(gradient - model.pack(independent_gradient)))), "gauge_energy_error": abs(gauge_energy - independent_energy), "gauge_gradient_error": float(np.max(abs(gauge_gradient - independent_gradient * np.exp(1j * gauge)))), "uniform_energy_error": abs(uniform_energy + case["h"]**2 * model.size / 2), "uniform_gradient_rms": uniform_rms, "physical_flux_error": physical_flux_error(case, metadata), "active_components": ndimage.label(model.mask)[1], "minimum_stiffness": min(float(np.min(case["kx"])), float(np.min(case["ky"])))}
        record["passed"] = record["finite_difference_max_relative_error"] < 1e-6 and max(record["independent_energy_error"], record["gauge_energy_error"], record["uniform_energy_error"]) < 1e-8 and max(record["independent_gradient_error"], record["gauge_gradient_error"], record["uniform_gradient_rms"], record["physical_flux_error"]) < 1e-10 and record["active_components"] == 1 and record["minimum_stiffness"] > 0
        if not record["passed"]:
            raise RuntimeError(str(record))
        records.append(record)
    original = CONCEPT / "champions/generation_1/solve.py"
    source_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((ROOT / "baseline/solve.py").read_bytes()).hexdigest() != source_hash:
        raise RuntimeError("baseline is not the exact champion")
    report = {"passed": all(record["passed"] for record in records), "case_count": len(records), "champion_sha256": source_hash, "checks_per_case": 9, "records": records}
    write_json(ROOT / "validation.json", report)
    print({key: value for key, value in report.items() if key != "records"})


if __name__ == "__main__":
    main()
