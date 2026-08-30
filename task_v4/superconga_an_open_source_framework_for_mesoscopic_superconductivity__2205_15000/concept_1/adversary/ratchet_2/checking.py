from common import ASSETS, ROOT, read_json, write_json

import sys
import time

import numpy as np
from scipy import ndimage
from scipy.optimize import minimize

sys.path.insert(0, str(ASSETS / "authoring"))
sys.path.insert(0, str(ASSETS / "evaluator"))
sys.path.insert(0, str(ASSETS / "participant/input"))
from independent import checked_field, energy_gradient, lower_bound
from evaluate import aggregate, invalid_case, lock_cpu_affinity, score_field, scratch_usage
from gl_model import GLModel
from sandbox import Sandbox


def physical_flux_error(case, metadata):
    height, width = case["shape"]
    rows, columns = np.indices((height - 1, width - 1), dtype=float)
    field = metadata["field"]
    wave_x, wave_y = field["wave_x"], field["wave_y"]
    argument_x = wave_x * (columns - (width - 1) / 2) + field["phase_x"]
    argument_y = wave_y * (rows - (height - 1) / 2) + field["phase_y"]
    sine_x = np.sin(argument_x + wave_x) - np.sin(argument_x)
    sine_y = np.sin(argument_y + wave_y) - np.sin(argument_y)
    expected = case["h"]**2 * (field["base"] + field["cos_x"] / wave_x * sine_x + field["cos_y"] / wave_y * sine_y + field["cos_xy"] / (wave_x * wave_y) * sine_x * sine_y)
    ax, ay = np.asarray(case["ax"]), np.asarray(case["ay"])
    actual = ax[:-1] + ay[:, 1:] - ax[1:] - ay[:, :-1]
    mask = np.asarray(case["mask"], dtype=bool)
    full = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1] & mask[1:, 1:]
    return float(np.max(abs(actual[full] - expected[full])))


def hole_loops(case, field, minimum_amplitude):
    mask = np.asarray(case["mask"], dtype=bool)
    labels, number = ndimage.label(~mask)
    exterior = set(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    ax, ay = np.asarray(case["ax"]), np.asarray(case["ay"])
    loops = []
    for label in range(1, number + 1):
        if label in exterior:
            continue
        rows, columns = np.nonzero(labels == label)
        bottom, top = int(rows.min()) - 1, int(rows.max()) + 1
        left, right = int(columns.min()) - 1, int(columns.max()) + 1
        contour = [(bottom, column) for column in range(left, right)] + [(row, right) for row in range(bottom, top)] + [(top, column) for column in range(right, left, -1)] + [(row, left) for row in range(top, bottom, -1)]
        record = {"hole_label": label, "center": [float(columns.mean()), float(rows.mean())], "valid": False}
        if any(not mask[row, column] for row, column in contour):
            loops.append(record)
            continue
        amplitude = min(abs(field[row, column]) for row, column in contour)
        phase_sum, flux_sum = 0.0, 0.0
        for source, destination in zip(contour, contour[1:] + contour[:1]):
            source_row, source_column = source
            dest_row, dest_column = destination
            if dest_column == source_column + 1:
                link = ax[source_row, source_column]
            elif dest_column == source_column - 1:
                link = -ax[dest_row, dest_column]
            elif dest_row == source_row + 1:
                link = ay[source_row, source_column]
            else:
                link = -ay[dest_row, dest_column]
            phase_sum += float(np.angle(np.conjugate(field[source]) * np.exp(-1j * link) * field[destination]))
            flux_sum += float(link)
        record.update({"valid": bool(amplitude >= minimum_amplitude), "winding": int(np.rint((phase_sum + flux_sum) / (2 * np.pi))), "flux_quanta": flux_sum / (2 * np.pi), "minimum_amplitude": float(amplitude)})
        loops.append(record)
    return loops


def vortex_map(case, field, minimum_amplitude):
    mask = np.asarray(case["mask"], dtype=bool)
    ax, ay = np.asarray(case["ax"]), np.asarray(case["ay"])
    horizontal = np.angle(np.conjugate(field[:, :-1]) * np.exp(-1j * ax) * field[:, 1:])
    vertical = np.angle(np.conjugate(field[:-1]) * np.exp(-1j * ay) * field[1:])
    circulation = horizontal[:-1] + vertical[:, 1:] - horizontal[1:] - vertical[:, :-1]
    flux = ax[:-1] + ay[:, 1:] - ax[1:] - ay[:, :-1]
    charge = np.rint((circulation + flux) / (2 * np.pi)).astype(int)
    active = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1] & mask[1:, 1:]
    amplitudes = np.minimum.reduce((abs(field[:-1, :-1]), abs(field[:-1, 1:]), abs(field[1:, :-1]), abs(field[1:, 1:])))
    return charge, active & (amplitudes >= minimum_amplitude)


def compare_topology(case, baseline, witness, policy):
    first = hole_loops(case, baseline, policy["minimum_hole_contour_amplitude"])
    second = hole_loops(case, witness, policy["minimum_hole_contour_amplitude"])
    changes = [{"baseline": source, "witness": destination} for source, destination in zip(first, second) if source["valid"] and destination["valid"] and source["winding"] != destination["winding"]]
    first_charge, first_active = vortex_map(case, baseline, policy["minimum_bulk_vortex_amplitude"])
    second_charge, second_active = vortex_map(case, witness, policy["minimum_bulk_vortex_amplitude"])
    changed = (first_charge != second_charge) & first_active & second_active
    locations = np.argwhere(changed)
    return {"changed_hole_windings": changes, "changed_hole_count": len(changes), "reliable_hole_contours": sum(source["valid"] and destination["valid"] for source, destination in zip(first, second)), "changed_vortex_plaquettes": int(changed.sum()), "vortex_changes": [{"row": int(row), "column": int(column), "baseline_charge": int(first_charge[row, column]), "witness_charge": int(second_charge[row, column])} for row, column in locations], "meaningful": bool(changes or changed.sum() >= 2)}


class PolishDeadline(Exception):
    pass


def local_polish(case, field, seconds):
    model = GLModel(case)
    started = time.monotonic()
    initial_energy, unused, initial_rms = energy_gradient(case, field)
    current = model.pack(field)
    iterations = 0
    def callback(vector):
        nonlocal current, iterations
        current = vector.copy()
        iterations += 1
        if time.monotonic() - started >= seconds:
            raise PolishDeadline()
    completed = True
    try:
        result = minimize(model.objective, current, jac=True, method="L-BFGS-B", callback=callback, options={"maxiter": 2000, "maxls": 40, "ftol": 1e-15, "gtol": 1e-9, "maxcor": 20})
        current = result.x
        message = str(result.message)
    except PolishDeadline:
        completed = False
        message = "bounded diagnostic polish deadline"
    polished = model.unpack(current)
    energy, unused, rms = energy_gradient(case, polished)
    return polished, {"initial_energy": initial_energy, "initial_gradient_rms": initial_rms, "energy": energy, "gradient_rms": rms, "gain": initial_energy - energy, "iterations": iterations, "wall_seconds": time.monotonic() - started, "completed": completed, "message": message}


def diagnose(reference, case, field, policy):
    witness = checked_field(ROOT / reference["witness_path"], case, policy["result_max_bytes"])
    energy, unused, rms = energy_gradient(case, field)
    gap = energy - reference["witness_energy"]
    if gap < policy["minimum_remaining_gap"]:
        return {"energy": energy, "gradient_rms": rms, "remaining_gap": gap, "substantive": False, "reason": "no meaningful remaining energy gap"}
    polished, polish = local_polish(case, field, policy["maximum_local_polish_seconds"])
    topology = compare_topology(case, polished, witness, policy)
    reasons = []
    if not polish["completed"] or polish["gradient_rms"] > policy["stationarity_rms_max"]:
        reasons.append("local polish control incomplete")
    if polish["energy"] - reference["witness_energy"] < policy["minimum_remaining_gap"]:
        reasons.append("gap collapses under local polish")
    if polish["gain"] > policy["maximum_polish_fraction_of_gap"] * gap:
        reasons.append("large tolerance/polish contribution")
    if not topology["meaningful"]:
        reasons.append("no reliable topological misallocation")
    return {"energy": energy, "gradient_rms": rms, "remaining_gap": gap, "polish": polish, "topology": topology, "substantive": not reasons, "control_inconclusive": not polish["completed"] or polish["gradient_rms"] > policy["stationarity_rms_max"], "reason": "; ".join(reasons) if reasons else "stationary topological gap survives tight local polish"}
