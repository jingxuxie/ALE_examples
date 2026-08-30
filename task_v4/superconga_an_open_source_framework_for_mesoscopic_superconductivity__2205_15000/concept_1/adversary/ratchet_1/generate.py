import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage


ROOT = Path(__file__).resolve().parent


def make_case(family, variant, seed):
    generator = np.random.default_rng(seed)
    shapes = {
        "coupled_fluxoid": [(80, 84), (88, 88), (92, 96), (96, 100), (100, 104), (108, 108)],
        "bridge_competition": [(80, 88), (84, 92), (88, 96), (92, 100), (96, 104), (100, 108)],
        "vortex_pinning": [(84, 92), (88, 96), (92, 100), (96, 104), (100, 108), (104, 112)],
    }
    shape = shapes[family][variant]
    ny, nx = shape
    rows, columns = np.indices(shape, dtype=float)
    centered_x, centered_y = columns - (nx - 1) / 2, rows - (ny - 1) / 2
    h = [0.88, 0.95, 1.0, 0.9, 1.0, 0.95][variant]
    mask = (np.abs(centered_x / (nx / 2 - 2.5))**8 + np.abs(centered_y / (ny / 2 - 2.5))**8) < 1
    if family == "coupled_fluxoid":
        count_y, count_x = [(4, 4), (4, 5), (5, 5), (5, 6), (6, 5), (6, 6)][variant]
        base_field = [0.035, 0.055, 0.08, 0.035, 0.075, 0.05][variant]
        field_x, field_y, field_xy = 0.024, -0.015, 0.018
    elif family == "bridge_competition":
        count_y, count_x = [(4, 5), (5, 5), (5, 6), (6, 6), (6, 6), (6, 7)][variant]
        base_field = [0.045, 0.02, 0.065, 0.035, 0.07, 0.04][variant]
        field_x, field_y, field_xy = 0.075, -0.055, 0.045
    else:
        count_y, count_x = [(3, 4), (4, 4), (3, 5), (4, 5), (4, 5), (5, 5)][variant]
        base_field = [0.22, 0.27, 0.30, 0.25, 0.32, 0.28][variant]
        field_x, field_y, field_xy = 0.09, -0.06, 0.055
    wave_x, wave_y = 2 * np.pi / (nx * 0.86), 2 * np.pi / (ny * 0.94)
    phase_x, phase_y = generator.uniform(-1, 1, size=2)
    argument_x = wave_x * centered_x + phase_x
    argument_y = wave_y * centered_y + phase_y
    ax = h**2 * (-0.5 * base_field * centered_y[:, :-1] - field_y / wave_y * np.sin(argument_y[:, :-1]))
    ay = h**2 * (0.5 * base_field * centered_x[:-1, :] + field_x / wave_x * np.sin(argument_x[:-1, :]))
    ay += h**2 * field_xy / (wave_x * wave_y) * np.sin(argument_x[:-1, :]) * (np.sin(argument_y[1:, :]) - np.sin(argument_y[:-1, :]))
    smooth_ax, smooth_ay = ax.copy(), ay.copy()
    centers_x = np.linspace(14, nx - 15, count_x)
    centers_y = np.linspace(14, ny - 15, count_y)
    pitch_x = float(np.diff(centers_x).mean())
    pitch_y = float(np.diff(centers_y).mean())
    holes = []
    for index_y, base_y in enumerate(centers_y):
        for index_x, base_x in enumerate(centers_x):
            center_x, center_y = base_x + generator.uniform(-0.45, 0.45), base_y + generator.uniform(-0.45, 0.45)
            if family == "bridge_competition":
                bridge_x = [3.2, 4.0, 3.0, 3.8, 4.7, 3.1][variant]
                bridge_y = [4.5, 3.0, 4.0, 3.0, 3.6, 4.0][variant]
                radius_x, radius_y = (pitch_x - bridge_x) / 2, (pitch_y - bridge_y) / 2
                exponent = 6
            elif family == "coupled_fluxoid":
                radius_x = 0.38 * pitch_x * generator.uniform(0.93, 1.03)
                radius_y = 0.38 * pitch_y * generator.uniform(0.93, 1.03)
                exponent = 4 if variant % 2 else 2
            else:
                radius_x = generator.uniform(2.8, 4.7)
                radius_y = generator.uniform(2.8, 5.0)
                exponent = 2
            hole_mask = np.abs((columns - center_x) / radius_x)**exponent + np.abs((rows - center_y) / radius_y)**exponent < 1
            mask &= ~hole_mask
            local_field = base_field + field_x * np.cos(wave_x * (center_x - (nx - 1) / 2) + phase_x) + field_y * np.cos(wave_y * (center_y - (ny - 1) / 2) + phase_y)
            local_field += field_xy * np.cos(wave_x * (center_x - (nx - 1) / 2) + phase_x) * np.cos(wave_y * (center_y - (ny - 1) / 2) + phase_y)
            offsets = [0.025, 0.065, 0.12, 0.035, 0.10, 0.05]
            target_flux = generator.integers(0, 3) + 0.5 + generator.uniform(-offsets[variant], offsets[variant])
            if family == "bridge_competition" and (index_x + 2 * index_y + variant) % 3 == 0:
                target_flux *= -1
            if family == "vortex_pinning":
                target_flux = generator.uniform(-1.0, 3.5)
            solenoid = target_flux - h**2 * local_field * int(hole_mask.sum()) / (2 * np.pi)
            angle = np.arctan2(rows - center_y, columns - center_x)
            ax += solenoid * np.angle(np.exp(1j * (angle[:, 1:] - angle[:, :-1])))
            ay += solenoid * np.angle(np.exp(1j * (angle[1:, :] - angle[:-1, :])))
            holes.append({"center": [float(center_x), float(center_y)], "radii": [float(radius_x), float(radius_y)], "exponent": exponent, "solenoid_flux_quanta": float(solenoid), "approximate_target_total_flux_quanta": float(target_flux), "lattice_void_sites": int(hole_mask.sum())})
    disorder = ndimage.gaussian_filter(generator.normal(size=shape), 3.5)
    disorder /= disorder.std()
    alpha = -1.0 + 0.065 * disorder
    beta = 1.0 + 0.07 * np.sin(columns * 0.071) * np.cos(rows * 0.063)
    pin_count = int(mask.sum() / (64 if family == "vortex_pinning" else 170))
    candidates = np.argwhere(mask & (ndimage.distance_transform_edt(mask) > 1.4))
    pins = []
    for unused in range(pin_count):
        center_y, center_x = candidates[generator.integers(len(candidates))]
        width = generator.uniform(0.65, 1.3) if family != "vortex_pinning" else generator.uniform(0.8, 1.5)
        strength = generator.uniform(1.2, 3.7)
        alpha += strength * np.exp(-((columns - center_x)**2 + (rows - center_y)**2) / (2 * width**2))
        pins.append([int(center_x), int(center_y), float(width), float(strength)])
    kx = 1.05 + 0.18 * np.sin(rows[:, :-1] * 0.09) * np.cos(columns[:, :-1] * 0.057)
    ky = 1.02 + 0.16 * np.cos(rows[:-1, :] * 0.06) * np.sin(columns[:-1, :] * 0.083)
    gauge = 0.9 * np.sin(columns * 0.073 + generator.uniform(-2, 2)) + 0.8 * np.cos(rows * 0.093) + 0.0003 * centered_x * centered_y
    ax += gauge[:, 1:] - gauge[:, :-1]
    ay += gauge[1:, :] - gauge[:-1, :]
    initial = np.sqrt(np.maximum(-alpha, 0.04) / beta) * np.exp(1j * gauge) * mask
    case_id = {"coupled_fluxoid": "cf", "bridge_competition": "bc", "vortex_pinning": "vp"}[family] + "%02d" % (variant + 1)
    case = {"schema_version": 1, "case_id": case_id, "shape": list(shape), "h": h, "wall_seconds": 60}
    arrays = {"mask": mask.astype(int), "alpha": alpha, "beta": beta, "ax": ax, "ay": ay, "kx": kx, "ky": ky, "initial_real": initial.real, "initial_imag": initial.imag}
    case.update({name: array.tolist() for name, array in arrays.items()})
    active_components = ndimage.label(mask)[1]
    void_labels, void_count = ndimage.label(~mask)
    boundary_labels = set(np.concatenate((void_labels[0], void_labels[-1], void_labels[:, 0], void_labels[:, -1])))
    actual_holes = len([value for value in range(1, void_count + 1) if value not in boundary_labels])
    if active_components != 1 or actual_holes != len(holes):
        raise RuntimeError("geometry is not one connected grain with distinct intended holes: " + case_id)
    full = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1] & mask[1:, 1:]
    flux = ax[:-1] + ay[:, 1:] - ax[1:] - ay[:, :-1]
    expected_flux = smooth_ax[:-1] + smooth_ay[:, 1:] - smooth_ax[1:] - smooth_ay[:, :-1]
    error = float(np.max(np.abs((flux - expected_flux)[full])))
    if error > 1e-11:
        raise RuntimeError("active solenoid curvature or gauge error")
    metadata = {"case_id": case_id, "family": family, "variant": variant, "seed": seed, "shape": list(shape), "h": h, "active_sites": int(mask.sum()), "holes": holes, "pins": pins, "actual_holes": actual_holes, "active_components": active_components, "field": {"base": base_field, "cos_x": field_x, "cos_y": field_y, "cos_xy": field_xy, "wave_x": wave_x, "wave_y": wave_y, "phase_x": float(phase_x), "phase_y": float(phase_y)}, "active_physical_flux_error": error, "bulk_flux_quanta": float(np.sum(expected_flux[full]) / (2 * np.pi)), "minimum_stiffness": min(float(kx.min()), float(ky.min()))}
    return case, metadata


def main():
    index = []
    for family_index, family in enumerate(("coupled_fluxoid", "bridge_competition", "vortex_pinning")):
        for variant in range(6):
            seed = 590017 + family_index * 13007 + variant * 1009
            case, metadata = make_case(family, variant, seed)
            case_path = ROOT / "cases" / (case["case_id"] + ".json")
            if case_path.exists():
                raise RuntimeError("refusing to overwrite case")
            case_path.write_text(json.dumps(case, separators=(",", ":")) + "\n")
            metadata["case_sha256"] = hashlib.sha256(case_path.read_bytes()).hexdigest()
            (ROOT / "metadata" / (case["case_id"] + ".json")).write_text(json.dumps(metadata, indent=2) + "\n")
            index.append({key: metadata[key] for key in ("case_id", "family", "shape", "active_sites", "actual_holes", "bulk_flux_quanta", "active_physical_flux_error", "case_sha256")})
    (ROOT / "broad_index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
