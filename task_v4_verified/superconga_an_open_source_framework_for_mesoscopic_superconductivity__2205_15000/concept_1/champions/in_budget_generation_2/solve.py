import os
import time

START_WALL = time.monotonic()
START_CPU = time.process_time()
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

import engine


def loop_data(model, topology, field):
    labels, unused = ndimage.label(~model.mask)
    full = model.full(field)
    result = []
    for center in topology.holes:
        label = labels[int(center.imag), int(center.real)]
        rows, columns = np.nonzero(labels == label)
        bottom, top = int(rows.min()) - 1, int(rows.max()) + 1
        left, right = int(columns.min()) - 1, int(columns.max()) + 1
        contour = [(bottom, column) for column in range(left, right)] + [(row, right) for row in range(bottom, top)] + [(top, column) for column in range(right, left, -1)] + [(row, left) for row in range(top, bottom, -1)]
        if any(not model.mask[row, column] for row, column in contour):
            result.append({"valid": False, "winding": 0, "flux": 0.0})
            continue
        phase_sum, flux_sum = 0.0, 0.0
        for source, target in zip(contour, contour[1:] + contour[:1]):
            source_y, source_x = source
            target_y, target_x = target
            if target_x == source_x + 1:
                link = model.ax[source_y, source_x]
            elif target_x == source_x - 1:
                link = -model.ax[target_y, target_x]
            elif target_y == source_y + 1:
                link = model.ay[source_y, source_x]
            else:
                link = -model.ay[target_y, target_x]
            phase_sum += float(np.angle(np.conjugate(full[source]) * np.exp(-1j * link) * full[target]))
            flux_sum += float(link)
        minimum_amplitude = min(abs(full[row, column]) for row, column in contour)
        result.append({"valid": minimum_amplitude > 1e-8, "winding": int(np.rint((phase_sum + flux_sum) / (2 * np.pi))), "flux": flux_sum / (2 * np.pi), "minimum_contour_amplitude": float(minimum_amplitude)})
    return result


def joint_search(model, budget, seed, mode, progress):
    generator = np.random.default_rng(seed)
    topology = engine.Topology(model)
    energy, gradient = model.energy_gradient(model.initial)
    best = model.initial.copy()
    best_energy = energy
    history = []
    if len(topology.holes) >= 12 and mode != "extended":
        row_groups = np.zeros(len(topology.holes), dtype=int)
        column_groups = np.zeros(len(topology.holes), dtype=int)
        row_number, row_center, column_number = 0, float(topology.holes[0].imag), 0
        for index, center in enumerate(topology.holes):
            if center.imag - row_center > 2:
                row_number, row_center, column_number = row_number + 1, float(center.imag), 0
            row_groups[index], column_groups[index] = row_number, column_number
            column_number += 1
        for pattern in range(4):
            if budget.remaining() < 5:
                break
            data = loop_data(model, topology, best)
            current = np.array([item["winding"] for item in data])
            flux = np.array([item["flux"] for item in data])
            if pattern < 2:
                desired = np.floor(flux).astype(int) + (row_groups + column_groups + pattern) % 2
            else:
                desired = np.floor(flux).astype(int) + (row_groups // 2 + column_groups // 2 + pattern) % 2
            changes = desired - current
            changes[np.array([not item["valid"] for item in data])] = 0
            phase = np.sum(changes[:, None] * np.angle(topology.points[None, :] - topology.holes[:, None]), axis=0)
            candidate = best * np.exp(1j * phase)
            energy, field, rms = engine.conjugate_relax(model, candidate, budget, reserve=3.0, maxiter=4000, tolerance=3e-10)
            before = best_energy
            if rms < 0.0015 and energy < best_energy:
                best_energy, best = energy, field.copy()
            history.append({"kind": "collective_fluxoid_seed", "pattern": pattern, "changed_holes": int(np.count_nonzero(changes)), "energy": energy, "gradient_rms": rms, "best_energy": best_energy, "improvement": before - best_energy, "elapsed": budget.elapsed()})
    if mode in ("combined", "extended"):
        seconds = max(2.0, budget.remaining() - 3) if mode == "extended" else max(2.0, 0.32 * budget.remaining())
        extended_budget = engine.Budget(seconds=seconds)
        extended_field, trials = engine.solve(model, extended_budget, progress=False)
        field = extended_field[model.mask]
        energy, gradient = model.energy_gradient(field)
        rms = float(np.sqrt(engine.dot(gradient, gradient) / (2 * model.size)))
        if rms < 0.0015 and energy < best_energy:
            best_energy, best = energy, field.copy()
        history.append({"kind": "extended_champion", "energy": energy, "gradient_rms": rms, "best_energy": best_energy, "elapsed": budget.elapsed(), "trials": trials})
    best_energy, best, best_rms = engine.conjugate_relax(model, best, budget, maxiter=3500, tolerance=1e-10)
    current, current_energy = best.copy(), best_energy
    archive = [(best_energy, best.copy())]
    holes = topology.holes
    angles = np.angle(topology.points[None, :] - holes[:, None]) if len(holes) else np.zeros((0, model.size))
    hole_distances = abs(holes[:, None] - holes[None, :]) if len(holes) else np.zeros((0, 0))
    nearest = np.argsort(hole_distances, axis=1)[:, 1:7] if len(holes) else np.zeros((0, 0), dtype=int)
    iteration = 0
    schedule = ["pair_transfer", "pair_same", "cluster", "bridge_cut", "pair_transfer", "relocate", "cluster", "hole", "pair_same", "patch", "crossover", "thermal"]
    while mode != "extended" and budget.remaining() > 3.8:
        kind = schedule[iteration % len(schedule)]
        parent = best if generator.random() < 0.6 else current
        if generator.random() < 0.12 and len(archive) > 1:
            parent = archive[generator.integers(len(archive))][1]
        move = {}
        if len(holes) >= 2 and kind in ("pair_transfer", "pair_same", "cluster", "bridge_cut"):
            first = int(generator.integers(len(holes)))
            second = int(generator.choice(nearest[first, :min(4, len(nearest[first]))]))
            charge = int(generator.choice([-1, 1]))
            selected = [first, second]
            charges = [charge, -charge if kind == "pair_transfer" else charge]
            if kind == "cluster":
                number = int(generator.integers(2, min(7, len(holes) + 1)))
                selected = [first] + [int(value) for value in nearest[first, :number - 1]]
                charges = [charge] * len(selected)
                if generator.random() < 0.35:
                    charges = [int(generator.choice([-1, 1])) for unused in selected]
            rotation = np.exp(1j * np.sum(angles[selected] * np.asarray(charges)[:, None], axis=0))
            candidate = parent * rotation
            move = {"holes": selected, "charges": charges}
            if kind == "bridge_cut":
                source, target = holes[first], holes[second]
                displacement = target - source
                parameter = np.clip(((topology.points - source) * displacement.conjugate()).real / max(abs(displacement)**2, 1e-20), 0, 1)
                distances = abs(topology.points - (source + parameter * displacement))
                shift = 2.5 * model.h**2 * topology.alpha_scale * np.exp(-distances**2 / (1.5 * topology.core)**2)
                candidate = engine.conjugate_relax(model, candidate, budget, reserve=3.0, maxiter=500, tolerance=1e-7, shift=shift)[1]
        elif kind == "crossover" and len(archive) > 1:
            candidate = topology.crossover(parent, archive[generator.integers(len(archive))][1], generator)
        elif kind == "thermal":
            shift = 0.4 * (-model.h**2 * topology.alpha_scale - model.alpha)
            candidate = engine.conjugate_relax(model, parent, budget, maxiter=500, tolerance=1e-7, shift=shift)[1]
        else:
            candidate = topology.modify(parent, generator, "relocate" if kind not in ("patch", "hole") else kind)
            if kind == "relocate" and generator.random() < 0.55:
                candidate = topology.modify(candidate, generator, "relocate")
        before = best_energy
        energy, field, rms = engine.conjugate_relax(model, candidate, budget, maxiter=2800, tolerance=3e-10)
        valid = np.isfinite(energy) and rms < 0.0015
        if valid and energy < best_energy:
            best_energy, best, best_rms = energy, field.copy(), rms
        if valid:
            temperature = model.energy_scale * (0.12 + 0.6 * (1 - (iteration % 60) / 60)**2)
            if energy < current_energy or generator.random() < np.exp(min(0, (current_energy - energy) / temperature)):
                current, current_energy = field.copy(), energy
            if energy < best_energy + 2.0 * model.energy_scale:
                if all(abs(energy - stored_energy) > 1e-4 for stored_energy, stored in archive):
                    archive.append((energy, field.copy()))
                    archive.sort(key=lambda item: item[0])
                    archive = archive[:7]
        if iteration % 31 == 30:
            current, current_energy = best.copy(), best_energy
        record = {"kind": kind, "energy": energy, "gradient_rms": rms, "valid": bool(valid), "best_energy": best_energy, "improvement": before - best_energy, "elapsed": budget.elapsed(), "move": move}
        history.append(record)
        if progress and before - best_energy > 1e-5:
            print(json.dumps(record), flush=True)
        iteration += 1
    if budget.remaining() > 0.4:
        energy, field, rms = engine.lbfgs_relax(model, best, budget, reserve=0.25, maxiter=1800)
        if rms < 0.0015 and energy <= best_energy + 1e-8:
            best_energy, best, best_rms = energy, field, rms
    return model.full(best), history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, default=56.0)
    parser.add_argument("--seed", type=int, default=713)
    parser.add_argument("--mode", choices=["combined", "joint", "extended"], default="joint")
    parser.add_argument("--start")
    parser.add_argument("--history")
    args = parser.parse_args()
    budget = engine.Budget(seconds=args.seconds, origin=(START_WALL, START_CPU))
    with open(args.input) as stream:
        model = engine.Model(json.load(stream))
    if args.start:
        with np.load(args.start, allow_pickle=False) as archive:
            model.initial = np.ascontiguousarray(archive["psi"][model.mask], dtype=np.complex128)
    field, history = joint_search(model, budget, args.seed, args.mode, bool(args.history))
    with open(args.output, "wb") as stream:
        np.savez_compressed(stream, psi=field)
    if args.history:
        Path(args.history).write_text(json.dumps(history, indent=2) + "\n")
    energy, gradient = model.energy_gradient(field[model.mask])
    print(json.dumps({"energy": energy, "gradient_rms": float(np.sqrt(engine.dot(gradient, gradient) / (2 * model.size))), "trials": len(history), "elapsed": budget.elapsed()}))


if __name__ == "__main__":
    main()
