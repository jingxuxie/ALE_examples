from common import ROOT, write_json

import hashlib
import json

import numpy as np
from scipy import ndimage


def main():
    original = json.loads((ROOT / "broad_index.json").read_text())
    extension = []
    specifications = [(92, 116, 6, 8), (108, 108, 7, 7), (96, 128, 6, 9), (120, 120, 8, 8), (112, 132, 7, 9), (124, 136, 8, 9)]
    for variant, (ny, nx, count_y, count_x) in enumerate(specifications):
        name = "nf%02d" % (variant + 1)
        generator = np.random.default_rng(822101 + variant * 619)
        rows, columns = np.indices((ny, nx), dtype=float)
        shape = (ny, nx)
        h = 0.84 if variant < 3 else 0.92
        mask = (columns >= 3) & (columns <= nx - 4) & (rows >= 3) & (rows <= ny - 4)
        centers_x, centers_y = np.linspace(11, nx - 12, count_x), np.linspace(11, ny - 12, count_y)
        pitch_x, pitch_y = float(np.diff(centers_x).mean()), float(np.diff(centers_y).mean())
        bridge = [3.6, 4.2, 3.7, 4.0, 3.8, 4.1][variant]
        base_field = 0.0 if variant != 4 else 0.012
        ax = -0.5 * base_field * h**2 * (rows[:, :-1] - (ny - 1) / 2)
        ay = 0.5 * base_field * h**2 * (columns[:-1, :] - (nx - 1) / 2)
        holes = []
        for index_y, center_y in enumerate(centers_y):
            for index_x, base_x in enumerate(centers_x):
                center_x = base_x + (1.2 * (-1)**index_y if variant == 3 else 0)
                radius_x, radius_y = (pitch_x - bridge) / 2, (pitch_y - bridge) / 2
                removed = (abs((columns - center_x) / radius_x)**8 + abs((rows - center_y) / radius_y)**8) < 1
                mask &= ~removed
                width = [0.005, 0.025, 0.13, 0.025, 0.08, 0.18][variant]
                solenoid = 0.5 + generator.uniform(-width, width)
                if variant == 1:
                    solenoid += 0.035 * (-1)**(index_x + index_y)
                solenoid -= base_field * h**2 * removed.sum() / (2 * np.pi)
                angle = np.arctan2(rows - center_y, columns - center_x)
                ax += solenoid * np.angle(np.exp(1j * (angle[:, 1:] - angle[:, :-1])))
                ay += solenoid * np.angle(np.exp(1j * (angle[1:] - angle[:-1])))
                holes.append({"center": [float(center_x), float(center_y)], "radii": [radius_x, radius_y], "exponent": 8, "solenoid_flux_quanta": float(solenoid), "lattice_void_sites": int(removed.sum())})
        disorder = ndimage.gaussian_filter(generator.normal(size=shape), 2.0)
        alpha = -1 + 0.05 * disorder / disorder.std()
        pins = []
        if variant >= 2:
            active = np.argwhere(mask)
            for unused in range(int(mask.sum() / (120 if variant < 5 else 60))):
                center_y, center_x = active[generator.integers(len(active))]
                width, strength = generator.uniform(0.55, 1.0), generator.uniform(1.0, 2.8)
                alpha += strength * np.exp(-((rows - center_y)**2 + (columns - center_x)**2) / (2 * width**2))
                pins.append([int(center_x), int(center_y), float(width), float(strength)])
        beta = np.ones(shape)
        gauge = 0.8 * np.sin(columns * 0.09) + 0.9 * np.cos(rows * 0.07)
        ax += gauge[:, 1:] - gauge[:, :-1]
        ay += gauge[1:] - gauge[:-1]
        initial = np.sqrt(np.maximum(-alpha, 0.02)) * np.exp(1j * gauge) * mask
        case = {"schema_version": 1, "case_id": name, "shape": list(shape), "h": h, "wall_seconds": 60}
        arrays = {"mask": mask.astype(int), "alpha": alpha, "beta": beta, "ax": ax, "ay": ay, "kx": np.full((ny, nx - 1), 1.2), "ky": np.full((ny - 1, nx), 1.2), "initial_real": initial.real, "initial_imag": initial.imag}
        case.update({key: value.tolist() for key, value in arrays.items()})
        if ndimage.label(mask)[1] != 1:
            raise RuntimeError("disconnected network")
        labels, count = ndimage.label(~mask)
        exterior = set(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
        actual_holes = sum(number not in exterior for number in range(1, count + 1))
        if actual_holes != len(holes):
            raise RuntimeError("merged network holes")
        full = mask[:-1, :-1] & mask[:-1, 1:] & mask[1:, :-1] & mask[1:, 1:]
        flux = ax[:-1] + ay[:, 1:] - ax[1:] - ay[:, :-1]
        error = float(np.max(abs(flux[full] - base_field * h**2)))
        family = "collective_half_flux" if variant < 2 or variant == 3 else "pinned_fluxoid_network"
        metadata = {"case_id": name, "family": family, "shape": list(shape), "active_sites": int(mask.sum()), "actual_holes": actual_holes, "holes": holes, "pins": pins, "bulk_flux_quanta": float(np.sum(flux[full]) / (2 * np.pi)), "active_physical_flux_error": error, "active_components": 1, "minimum_stiffness": 1.2, "field": {"base": base_field, "cos_x": 0.0, "cos_y": 0.0, "cos_xy": 0.0, "wave_x": 1.0, "wave_y": 1.0, "phase_x": 0.0, "phase_y": 0.0}, "purpose": "collective near-half-flux loop allocation; small bridge network, not simply more active variables"}
        path = ROOT / "cases" / (name + ".json")
        if path.exists():
            raise RuntimeError("extension already exists")
        path.write_text(json.dumps(case, separators=(",", ":")) + "\n")
        metadata["case_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_json(ROOT / "metadata" / (name + ".json"), metadata)
        extension.append({key: metadata[key] for key in ("case_id", "family", "shape", "active_sites", "actual_holes", "bulk_flux_quanta", "active_physical_flux_error", "case_sha256")})
    write_json(ROOT / "broad_index.json", original + extension)
    print(extension)


if __name__ == "__main__":
    main()
