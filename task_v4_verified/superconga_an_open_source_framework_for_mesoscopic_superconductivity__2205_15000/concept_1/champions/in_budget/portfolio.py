import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.ndimage import label, maximum_filter
from scipy.optimize import minimize

asset_dir = Path(__file__).resolve().parents[1] / "participant" / "input"
if not asset_dir.is_dir():
    asset_dir = Path("/participant/input")
sys.path.insert(0, str(asset_dir))
from gl_model import load_case


def geometry(model):
    rows, columns = np.indices(model.shape, dtype=float)
    curl = model.ax[:-1, :] + model.ay[:, 1:] - model.ax[1:, :] - model.ay[:, :-1]
    full = model.mask[:-1, :-1] & model.mask[1:, :-1] & model.mask[:-1, 1:] & model.mask[1:, 1:]
    flux_per_site = float(np.median(curl[full])) / (2 * np.pi)
    regions, count = label(~model.mask)
    holes = []
    for region in range(1, count + 1):
        component = regions == region
        if component[0].any() or component[-1].any() or component[:, 0].any() or component[:, -1].any():
            continue
        hole_y, hole_x = np.mean(np.argwhere(component), axis=0)
        hole_flux = float(np.sum(curl[component[:-1, :-1]])) / (2 * np.pi)
        holes.append((hole_x, hole_y, hole_flux))
    peaks = (model.alpha == maximum_filter(model.alpha, size=5)) & (model.alpha > 0.0) & model.mask
    pin_sites = np.argwhere(peaks)
    return rows, columns, flux_per_site, holes, pin_sites


def seeded_field(model, generator, info, fraction):
    rows, columns, flux_per_site, holes, pin_sites = info
    phase = np.angle(model.initial)
    amplitude = np.sqrt(np.maximum(-model.alpha, 0.06) / model.beta)
    active = np.argwhere(model.mask)
    desired = max(1, int(flux_per_site * model.size * fraction))
    centers = []
    for hole_x, hole_y, hole_flux in holes:
        winding = int(np.rint(hole_flux)) + int(generator.choice([-1, 0, 0, 0, 1]))
        phase += winding * np.arctan2(rows - hole_y, columns - hole_x)
    spacing = np.sqrt(1 / max(flux_per_site, 1e-4))
    rotation = generator.uniform(0, 2 * np.pi)
    candidates = active[generator.permutation(len(active))[:min(1200, len(active))]]
    if len(pin_sites):
        candidates = np.concatenate((pin_sites[generator.permutation(len(pin_sites))], candidates))
    for center_y, center_x in candidates:
        if len(centers) >= desired:
            break
        if centers and min((center_x - prior_x)**2 + (center_y - prior_y)**2 for prior_x, prior_y in centers) < (0.54 * spacing)**2:
            continue
        center_x = float(center_x) + 0.35 * np.cos(rotation)
        center_y = float(center_y) + 0.35 * np.sin(rotation)
        centers.append((center_x, center_y))
        radius = np.hypot(columns - center_x, rows - center_y)
        phase += np.arctan2(rows - center_y, columns - center_x)
        amplitude *= np.tanh(radius / 1.5)
    return amplitude * np.exp(1j * phase) * model.mask


def surgery(model, field, generator, info):
    rows, columns, flux_per_site, holes, pin_sites = info
    proposal = field.copy()
    if generator.random() < 0.6:
        phase = np.angle(field)
        horizontal = np.angle(np.exp(1j * (phase[:, 1:] - phase[:, :-1])))
        vertical = np.angle(np.exp(1j * (phase[1:, :] - phase[:-1, :])))
        winding = np.rint((horizontal[:-1, :] + vertical[:, 1:] - horizontal[1:, :] - vertical[:, :-1]) / (2 * np.pi))
        full = model.mask[:-1, :-1] & model.mask[1:, :-1] & model.mask[:-1, 1:] & model.mask[1:, 1:]
        cores = np.argwhere((winding > 0.5) & full)
        if len(cores):
            source_y, source_x = cores[generator.integers(len(cores))] + 0.5
            if len(pin_sites) and generator.random() < 0.7:
                distances = np.sum((pin_sites - np.array([source_y, source_x]))**2, axis=1)
                nearby = np.argsort(distances)[:min(6, len(pin_sites))]
                target_y, target_x = pin_sites[generator.choice(nearby)] + generator.uniform(-0.3, 0.3, size=2)
            else:
                target_y, target_x = np.array([source_y, source_x]) + generator.normal(size=2) * 3.0
            proposal *= np.exp(1j * (np.arctan2(rows - target_y, columns - target_x) - np.arctan2(rows - source_y, columns - source_x)))
            source_radius = np.hypot(rows - source_y, columns - source_x)
            target_radius = np.hypot(rows - target_y, columns - target_x)
            refill = np.sqrt(np.maximum(-model.alpha, 0.01) / model.beta)
            amplitude = np.abs(proposal) + np.exp(-source_radius**2 / 3) * np.maximum(0, refill - np.abs(proposal))
            proposal = amplitude * np.tanh(target_radius / 1.0) * np.exp(1j * np.angle(proposal)) * model.mask
            return proposal
    if holes and generator.random() < 0.5:
        hole_x, hole_y, unused = holes[generator.integers(len(holes))]
        winding = generator.choice([-1, 1])
        proposal *= np.exp(1j * winding * np.arctan2(rows - hole_y, columns - hole_x))
        return proposal
    if len(pin_sites) and generator.random() < 0.7:
        center_y, center_x = pin_sites[generator.integers(len(pin_sites))]
    else:
        active = np.argwhere(model.mask)
        center_y, center_x = active[generator.integers(len(active))]
    center_x = float(center_x) + generator.uniform(-0.4, 0.4)
    center_y = float(center_y) + generator.uniform(-0.4, 0.4)
    radius = np.hypot(columns - center_x, rows - center_y)
    winding = generator.choice([-1, 1])
    proposal *= np.tanh(radius / 1.5) * np.exp(1j * winding * np.arctan2(rows - center_y, columns - center_x))
    return proposal


def solve(model, seconds=54, seed=314159, mode="portfolio"):
    started = time.monotonic()
    deadline = started + seconds
    generator = np.random.default_rng(seed)
    info = geometry(model)
    best = model.initial.copy()
    best_energy = model.energy(best)
    history = []
    iteration = 0

    class BudgetExpired(Exception):
        pass

    def objective(vector):
        if time.monotonic() >= deadline:
            raise BudgetExpired()
        return model.objective(vector)

    while time.monotonic() < deadline - 0.4:
        if iteration == 0:
            initial = model.initial.copy()
            kind = "warm"
        elif mode == "multistart":
            scale = [0.6, 1.5, 3.0][(iteration - 1) % 3]
            initial = model.initial * np.exp(1j * scale * generator.normal(size=model.shape))
            kind = "random_phase"
        elif iteration < 6 or iteration % 4 == 0:
            initial = seeded_field(model, generator, info, generator.uniform(0.6, 1.1))
            kind = "vortex_seed"
        else:
            initial = surgery(model, best, generator, info)
            kind = "sector_surgery"
        try:
            result = minimize(objective, model.pack(initial), jac=True, method="L-BFGS-B", options={"maxiter": 1500, "ftol": 3e-13, "gtol": 2e-6, "maxcor": 12})
        except BudgetExpired:
            break
        field = model.unpack(result.x)
        energy = model.energy(field)
        rms = model.gradient_rms(field)
        if rms <= 0.002 and energy < best_energy:
            best, best_energy = field, energy
        history.append({"start": iteration, "kind": kind, "energy": energy, "gradient_rms": rms, "elapsed": time.monotonic() - started, "iterations": int(result.nit), "best_energy": best_energy})
        iteration += 1
    return best, history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, default=54)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--mode", choices=["portfolio", "multistart"], default="portfolio")
    parser.add_argument("--history")
    args = parser.parse_args()
    model = load_case(args.input)
    field, history = solve(model, args.seconds, args.seed, args.mode)
    with open(args.output, "wb") as stream:
        np.savez_compressed(stream, psi=field)
    if args.history:
        Path(args.history).write_text(json.dumps(history, indent=2) + "\n")
    print(json.dumps({"energy": model.energy(field), "gradient_rms": model.gradient_rms(field), "starts": len(history)}))


if __name__ == "__main__":
    main()
