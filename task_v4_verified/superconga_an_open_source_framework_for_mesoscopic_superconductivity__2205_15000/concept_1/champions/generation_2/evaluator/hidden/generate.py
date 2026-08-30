import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter


ROOT = Path(__file__).resolve().parents[2]


def create_case(case_id, family, shape, seed, development=False):
    generator = np.random.default_rng(seed)
    ny, nx = shape
    rows, columns = np.indices(shape, dtype=float)
    centered_x = columns - (nx - 1) / 2
    centered_y = rows - (ny - 1) / 2
    h = 0.7 if development else 0.95
    mask = (np.abs(centered_x / (0.48 * nx))**4 + np.abs(centered_y / (0.47 * ny))**4) < 1
    disorder = gaussian_filter(generator.normal(size=shape), 3)
    disorder /= max(float(disorder.std()), 1e-8)
    alpha = -1.0 + 0.065 * disorder
    beta = 1.0 + 0.05 * np.cos(columns * 0.11) * np.sin(rows * 0.08)
    holes = []
    if family == "perforated":
        centers = [(-0.24, -0.23), (0.02, -0.23), (0.25, -0.15), (-0.23, 0.11), (0.05, 0.09), (0.24, 0.27), (-0.06, 0.32)]
        for offset_x, offset_y in centers:
            center_x = (nx - 1) / 2 + offset_x * nx + generator.uniform(-1, 1)
            center_y = (ny - 1) / 2 + offset_y * ny + generator.uniform(-1, 1)
            radius = generator.uniform(0.05, 0.075) * min(shape)
            flux = generator.choice([-1, 1]) * generator.uniform(0.35, 1.65)
            mask &= (columns - center_x)**2 + (rows - center_y)**2 > radius**2
            holes.append((center_x, center_y, radius, flux))
    if family == "high_vortex":
        for offset_x, offset_y in [(-0.16, 0.03), (0.2, -0.18)]:
            center_x = (nx - 1) / 2 + offset_x * nx
            center_y = (ny - 1) / 2 + offset_y * ny
            radius = 0.045 * min(shape)
            mask &= (columns - center_x)**2 + (rows - center_y)**2 > radius**2
            holes.append((center_x, center_y, radius, generator.uniform(0.4, 1.4)))
    count = int(mask.sum() / ((70 if family == "strong_pinning" else 115) if development else (100 if family == "strong_pinning" else 150)))
    active = np.argwhere(mask)
    pins = []
    for unused in range(count):
        center_y, center_x = active[generator.integers(len(active))]
        width = generator.uniform(1.0, 1.85) if development else generator.uniform(0.8, 1.3)
        strength = generator.uniform(2.0, 4.0) if family == "strong_pinning" else generator.uniform(1.4, 3.0)
        alpha += strength * np.exp(-((columns - center_x)**2 + (rows - center_y)**2) / (2 * width**2))
        pins.append((int(center_x), int(center_y), float(width), float(strength)))
    magnetic_field = {"strong_pinning": 0.15, "perforated": 0.125, "high_vortex": 0.24}[family]
    magnetic_field *= generator.uniform(0.93, 1.08)
    if development:
        magnetic_field *= 0.9
    ax = -0.5 * magnetic_field * h**2 * centered_y[:, :-1]
    ay = 0.5 * magnetic_field * h**2 * centered_x[:-1, :]
    ay += magnetic_field * 0.12 * h**2 * nx / (2 * np.pi) * np.sin(2 * np.pi * centered_x[:-1, :] / nx)
    for center_x, center_y, radius, flux in holes:
        angle = np.arctan2(rows - center_y, columns - center_x)
        ax += flux * np.angle(np.exp(1j * (angle[:, 1:] - angle[:, :-1])))
        ay += flux * np.angle(np.exp(1j * (angle[1:, :] - angle[:-1, :])))
    gauge = 0.9 * np.sin(columns * 0.09 + generator.uniform(-2, 2)) + 0.7 * np.cos(rows * 0.13)
    gauge += 0.0004 * centered_x * centered_y
    ax += gauge[:, 1:] - gauge[:, :-1]
    ay += gauge[1:, :] - gauge[:-1, :]
    kx = 1.0 + 0.13 * np.sin(rows[:, :-1] * 0.06) * np.cos(columns[:, :-1] * 0.07)
    ky = 1.0 + 0.11 * np.cos(rows[:-1, :] * 0.08) * np.sin(columns[:-1, :] * 0.05)
    initial = np.sqrt(np.maximum(-alpha, 0.04) / beta) * np.exp(1j * gauge) * mask
    case = {"schema_version": 1, "case_id": case_id, "shape": list(shape), "h": h, "wall_seconds": 60}
    arrays = {"mask": mask.astype(int), "alpha": alpha, "beta": beta, "ax": ax, "ay": ay, "kx": kx, "ky": ky, "initial_real": initial.real, "initial_imag": initial.imag}
    case.update({name: array.tolist() for name, array in arrays.items()})
    metadata = {"case_id": case_id, "family": family, "seed": seed, "shape": list(shape), "magnetic_field": magnetic_field, "h": h, "holes": holes, "pins": pins, "active_sites": int(mask.sum()), "nominal_bulk_flux_quanta": magnetic_field * h**2 * mask.sum() / (2 * np.pi)}
    return case, metadata


def main():
    hidden_spec = [
        ("h01", "strong_pinning", (60, 64), 871203),
        ("h02", "strong_pinning", (68, 70), 591827),
        ("h03", "perforated", (64, 66), 281639),
        ("h04", "perforated", (70, 72), 961741),
        ("h05", "high_vortex", (68, 72), 723961),
        ("h06", "high_vortex", (74, 76), 435217),
    ]
    development_spec = [
        ("dev_pinning", "strong_pinning", (40, 42), 17011),
        ("dev_perforated", "perforated", (44, 46), 27011),
        ("dev_high_vortex", "high_vortex", (46, 48), 37013),
    ]
    metadata = []
    for development, specifications in [(False, hidden_spec), (True, development_spec)]:
        directory = ROOT / ("participant/input/cases" if development else "evaluator/hidden/cases")
        for case_id, family, shape, seed in specifications:
            case, details = create_case(case_id, family, shape, seed, development)
            destination = directory / (case_id + ".json")
            if destination.exists():
                raise RuntimeError("refusing to overwrite generated case: " + str(destination))
            destination.write_text(json.dumps(case, separators=(",", ":")) + "\n")
            details["development"] = development
            metadata.append(details)
    (ROOT / "evaluator/hidden/generation.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
