import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solve
import json
import time
import numpy as np


def generate(count, exchange=2.0, easy=0.4, hard=0.18, field=(0.04, 0, 0.10), tilt=None):
    exchanges = np.broadcast_to(exchange, (count - 1,)).copy()
    easy = np.broadcast_to(easy, (count,))
    hard = np.broadcast_to(hard, (count,))
    axis = np.tile([0., 0., 1.], (count, 1)) if tilt is None else np.asarray(tilt)
    axis /= np.linalg.norm(axis, axis=1, keepdims=True)
    hard_axis = np.tile([0., 1., 0.], (count, 1))
    hard_axis -= np.sum(hard_axis * axis, axis=1, keepdims=True) * axis
    hard_axis /= np.linalg.norm(hard_axis, axis=1, keepdims=True)
    anisotropy = easy[:, None, None] * axis[:, :, None] * axis[:, None, :] - hard[:, None, None] * hard_axis[:, :, None] * hard_axis[:, None, :]
    model = solve.SpinModel(exchanges, anisotropy, field, -axis, axis)
    plane = model.plane()
    if plane is not None:
        planar = solve.PlanarModel(model, plane)
        start, finish = [planar.spins(planar.relax(initial, maxiter=2500)) for initial in (planar.start, planar.finish)]
    else:
        start, finish = [model.relax(initial, maxiter=2500) for initial in (model.start, model.finish)]
    return {"exchange_meV": exchanges.tolist(), "anisotropy_meV": anisotropy.tolist(), "field_meV": list(field),
            "minimum_a": start.tolist(), "minimum_b": finish.tolist(), "time_limit_seconds": 85}


def check_case(name, case, dense=False, connectivity=False):
    started = time.monotonic()
    result = solve.solve(case)
    elapsed = time.monotonic() - started
    model = solve.SpinModel(case["exchange_meV"], case["anisotropy_meV"], case["field_meV"], case["minimum_a"], case["minimum_b"])
    saddle = result["saddle"]
    _, gradient, band, basis = model.derivatives(saddle)
    residual = np.max(np.linalg.norm(gradient.reshape(-1, 2), axis=1))
    values = result["eigenvalues_saddle_meV"]
    norm_error = np.max(np.abs(np.linalg.norm(saddle, axis=1) - 1))
    spectrum_error = 0.
    if dense:
        count = model.count
        cartesian = np.zeros((3 * count, 3 * count))
        _, raw_gradient = model.energy_gradient(saddle)
        for site in range(count):
            cartesian[3 * site:3 * site + 3, 3 * site:3 * site + 3] = -2 * model.anisotropy[site] - np.eye(3) * np.dot(saddle[site], raw_gradient[site])
        for bond in range(count - 1):
            cartesian[3 * bond:3 * bond + 3, 3 * bond + 3:3 * bond + 6] = -model.exchange[bond] * np.eye(3)
            cartesian[3 * bond + 3:3 * bond + 6, 3 * bond:3 * bond + 3] = -model.exchange[bond] * np.eye(3)
        transform = np.zeros((3 * count, 2 * count))
        for site in range(count):
            transform[3 * site:3 * site + 3, 2 * site:2 * site + 2] = basis[site]
        dense_hessian = transform.T @ cartesian @ transform
        spectrum_error = np.max(np.abs(np.linalg.eigvalsh(dense_hessian) - values))
        packed = np.zeros_like(dense_hessian)
        for offset in range(4):
            for column in range(2 * count - offset):
                packed[column + offset, column] = band[offset, column]
                packed[column, column + offset] = band[offset, column]
        assert np.max(np.abs(packed - dense_hessian)) < 1e-12
        perturbation = np.random.default_rng(71).normal(size=(count, 2))
        tangent = np.einsum("nik,nk->ni", basis, perturbation)
        step = 1e-4
        plus = model.difference(solve.sphere_step(saddle, step * tangent), saddle)
        minus = model.difference(solve.sphere_step(saddle, -step * tangent), saddle)
        expected = perturbation.ravel() @ dense_hessian @ perturbation.ravel()
        assert abs((plus + minus) / step**2 - expected) < max(1e-4, 1e-6 * abs(expected))
    endpoints = None
    if connectivity:
        plane = model.plane()
        if plane is not None and np.max(np.abs(saddle @ np.cross(plane[:, 0], plane[:, 1]))) < 1e-8:
            planar = solve.PlanarModel(model, plane)
            angles = planar.angles(saddle)
            unstable = solve.planar_inertia(planar, angles)
            _, halfspan, _ = solve.locations(planar)
            endpoints = [solve.basin_planar(planar, angles + sign * 0.15 * unstable / max(abs(unstable)), halfspan, time.monotonic() + 60) for sign in (-1, 1)]
        else:
            _, unstable = solve.band_modes(band)
            tangent = np.einsum("nik,nk->ni", basis, unstable.reshape(-1, 2))
            tangent *= .15 / np.max(np.linalg.norm(tangent, axis=1))
            endpoints = [solve.basin_full(model, solve.sphere_step(saddle, sign * tangent), 48, time.monotonic() + 60) for sign in (-1, 1)]
    print(f"{name}: N={model.count} time={elapsed:.3f} barrier={result['barrier_meV']:.10f} logfactor={result['log_omega0']:.9f} residual={residual:.2g} inertia={np.sum(values < 0)} low={values[:3]} spectrum_error={spectrum_error:.2g} basins={endpoints}", flush=True)
    assert residual < 2e-6
    assert norm_error < 1e-12
    assert spectrum_error < 1e-9
    assert np.sum(values < 0) == 1
    if endpoints is not None:
        assert sorted(endpoints) == [0, 1]
    return result


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "small"
    if mode == "small":
        for count in (1, 2, 6, 12, 32, 64):
            check_case(f"uniform{count}", generate(count, exchange=3 if count > 12 else 10), dense=True, connectivity=True)
        generator = np.random.default_rng(85)
        for count in (6, 32, 128):
            axes = generator.normal(scale=.07, size=(count, 3)) + [0, 0, 1]
            check_case(f"nonplanar{count}", generate(count, exchange=3 if count > 12 else 10, tilt=axes, field=(.04, .015, .10)), dense=True, connectivity=True)
    elif mode == "long":
        check_case("long4096", generate(4096), connectivity=True)
        easy = .40 - .24 * np.exp(-((np.arange(1024) - 487) / 18)**2)
        check_case("soft1024", generate(1024, easy=easy, field=(.03, 0, .10)), connectivity=True)
        easy = np.r_[np.full(512, .25), np.full(512, .4)]
        check_case("interface1024", generate(1024, easy=easy, field=(.04, 0, .1)), connectivity=True)
        generator = np.random.default_rng(84)
        axes = generator.normal(scale=.025, size=(4096, 3)) + [0, 0, 1]
        check_case("nonplanar4096", generate(4096, tilt=axes, field=(.04, .005, .10)), connectivity=True)


if __name__ == "__main__":
    main()
