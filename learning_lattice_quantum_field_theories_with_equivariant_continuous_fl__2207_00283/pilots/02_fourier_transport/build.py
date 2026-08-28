"""Regenerate private challenges, official outputs, calibrations and CLI checks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                        "NUMEXPR_NUM_THREADS"):
    os.environ[thread_variable] = "4"

import numpy as np


ROOT = Path(__file__).resolve().parent
AUTHORITATIVE = ROOT.parents[1] / "private/sources/bijx"
SOURCE_FILES = ["src/bijx/fourier.py", "src/bijx/bijections/fourier.py",
                "src/bijx/bijections/affine_complex.py", "src/bijx/utils.py",
                "tests/test_fourier_utils.py", "tests/test_bijections_advanced.py"]
GEOMETRIES = [
    ("odd_rectangular", (7, 9), (), (2,), True),
    ("mixed_odd_last", (8, 7), (3,), (), False),
    ("even_multichannel_shared", (10, 12), (2, 2), (2,), True),
    ("mixed_even_multibatch", (9, 10), (2,), (2, 2), False),
    ("odd_three_dimensional", (5, 7, 9), (), (2,), True),
    ("three_dimensional_planes", (6, 5, 8), (2,), (2,), True),
    ("three_dimensional_channels", (7, 6, 5), (2, 2), (), False),
    ("64_squared_shared", (64, 64), (3,), (2,), True),
    ("64_squared_channels", (64, 64), (2, 2), (), False),
    ("128_squared_channels", (128, 128), (3,), (2,), False),
    ("large_mixed_parity", (127, 128), (), (2,), True),
]


def make_input(spatial, channels, batch, shared, seed):
    from private.reference.official import FourierMeta, fft_momenta

    rng = np.random.default_rng(seed)
    meta = FourierMeta.create(spatial)
    reduced = meta.mr.shape
    spectrum_shape = reduced if shared else reduced + channels
    self_mask = np.asarray(meta.mr) & ~np.asarray(meta.mi)
    from_indices = tuple(np.asarray(meta.copy_from).T)
    to_indices = tuple(np.asarray(meta.copy_to).T)

    def constrain(values, odd=False):
        values = values.copy()
        if odd:
            values[self_mask] = 0
        if len(meta.copy_to):
            values[to_indices] = (-1 if odd else 1) * values[from_indices]
        return values

    momentum_squared = np.sum(np.asarray(fft_momenta(spatial, lattice=True))**2, axis=-1)
    if not shared:
        momentum_squared = momentum_squared.reshape(reduced + (1,) * len(channels))
    log_magnitude = constrain(rng.normal(0.04, 0.18, spectrum_shape) - 0.035 * momentum_squared)
    angles = constrain(rng.normal(0, 0.65, spectrum_shape), odd=True)
    base = np.exp(log_magnitude + 1j * angles)
    self_indices = np.argwhere(self_mask)
    for index in self_indices[::2]:
        base[tuple(index)] *= -1
    parameters = 3 + seed % 3
    amplitude = np.stack([constrain(rng.normal(0.13 if index == 0 else 0, 0.12, spectrum_shape))
                          for index in range(parameters)])
    phase = np.stack([constrain(rng.normal(0, 0.35, spectrum_shape), odd=True)
                      for _ in range(parameters)])
    probes = [base.copy()]
    bad_self = base.copy()
    bad_self[tuple(self_indices[-1])] += 0.37j
    probes.append(bad_self)
    if len(meta.copy_to):
        bad_pair = base.copy()
        bad_pair[tuple(meta.copy_to[len(meta.copy_to) // 2])] += 0.41 + 0.23j
        probes.append(bad_pair)
    interior = base.copy()
    interior[(0,) * (len(spatial) - 1) + (1,)] *= 0.6 * np.exp(0.91j)
    probes.append(interior)
    if seed % 2:
        probes.append(np.zeros_like(base))
    event = spatial + channels
    return {
        "spatial_shape": np.asarray(spatial, dtype=np.int64),
        "channel_shape": np.asarray(channels, dtype=np.int64),
        "batch_shape": np.asarray(batch, dtype=np.int64),
        "x": rng.normal(size=batch + event),
        "q": rng.normal(size=batch + (int(np.prod(spatial)),) + channels),
        "direction_x": rng.normal(scale=0.6, size=batch + event),
        "cotangent": rng.normal(size=batch + event),
        "log_density": np.asarray(rng.normal(-0.3, 0.8, batch)),
        "direction_log_density": np.asarray(rng.normal(0, 0.3, batch)),
        "theta": rng.uniform(-0.4, 0.4, parameters),
        "direction_theta": rng.normal(0, 0.3, parameters),
        "base": base, "amplitude": amplitude, "phase": phase,
        "probes": np.stack(probes),
    }


def prepare_source(source):
    hashes = {relative: hashlib.sha256((source / relative).read_bytes()).hexdigest()
              for relative in SOURCE_FILES}
    canonical = {relative: hashlib.sha256((AUTHORITATIVE / relative).read_bytes()).hexdigest()
                 for relative in SOURCE_FILES}
    if hashes != canonical:
        raise ValueError("source differs from the retained authoritative modules/tests")
    revision = subprocess.run(["git", "-C", str(AUTHORITATIVE), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=False)
    return {"authoritative_source": str(AUTHORITATIVE), "build_source": str(source),
            "git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "sha256": hashes,
            "adapter_note": "Official FourierData uses spatial-only metadata; the adapter moves channel axes before spatial axes for representation conversion, without changing source modules."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=Path("/tmp/ale_bijx") if Path("/tmp/ale_bijx").is_dir() else AUTHORITATIVE)
    parser.add_argument("--skip-cli-validation", action="store_true")
    arguments = parser.parse_args()
    sys.dont_write_bytecode = True
    os.environ.update(BIJX_SOURCE=str(arguments.source.resolve()), JAX_ENABLE_X64="1",
                      JAX_PLATFORMS="cpu", XLA_FLAGS="--xla_cpu_multi_thread_eigen=false",
                      PYTHONDONTWRITEBYTECODE="1")
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "4"
    from private.evaluator import (FAMILIES, array_error, evaluate, family_errors,
                                   measure, restrict_cores, score_errors, sha256)

    restrict_cores()
    provenance = prepare_source(arguments.source.resolve())
    from private.reference.official import jax, solve
    from private.reference.checks import run_checks
    from private.reference.weak.solve import solve as weak_solve

    for directory in ("private/challenge_pool/inputs", "private/challenge_pool/references",
                      "participant/input"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    sample = make_input((3, 4), (2,), (), False, 271802)
    np.savez_compressed(ROOT / "participant/input/example_2d.npz", **sample)
    second_sample = make_input((3, 4, 5), (), (), True, 271803)
    np.savez_compressed(ROOT / "participant/input/example_3d.npz", **second_sample)
    checks = run_checks(sample, solve(sample))
    checks["mixed_3d"] = run_checks(second_sample, solve(second_sample))
    print("Independent dense, finite-difference, symmetry and representation checks passed", flush=True)
    cases = []
    weak_measurements = []
    for index, (name, spatial, channels, batch, shared) in enumerate(GEOMETRIES):
        inputs = make_input(spatial, channels, batch, shared, 920270 + index * 137)
        started = time.perf_counter()
        expected = solve(inputs)
        strong_seconds = time.perf_counter() - started
        for value in expected.values():
            if not np.all(np.isfinite(value)):
                raise AssertionError(f"nonfinite official output: {name}")
        weak_measurements.append(measure(weak_solve(inputs), expected))
        input_path = ROOT / f"private/challenge_pool/inputs/{name}.npz"
        reference_path = ROOT / f"private/challenge_pool/references/{name}.npz"
        np.savez_compressed(input_path, **inputs)
        np.savez_compressed(reference_path, **expected)
        cases.append({"name": name, "input": f"inputs/{name}.npz",
                      "reference": f"references/{name}.npz",
                      "input_sha256": sha256(input_path), "reference_sha256": sha256(reference_path),
                      "geometry": {"spatial": spatial, "channels": channels, "batch": batch,
                                   "shared_spectrum": shared},
                      "official_compute_seconds": strong_seconds})
        print(f"Precomputed {name}: {strong_seconds:.3f}s", flush=True)
        jax.clear_caches()
    weak_errors = family_errors(weak_measurements)
    assert all(error > 1e-5 for error in weak_errors.values()), weak_errors
    assert array_error(None, np.zeros(2)) == 1e6
    assert array_error(np.full(2, np.nan), np.zeros(2)) == 1e6
    assert array_error(np.zeros(3), np.zeros(2)) == 1e6
    exact_scores = score_errors({family: 0.0 for family in FAMILIES}, weak_errors)
    weak_scores = score_errors(weak_errors, weak_errors)
    small_scores = score_errors({family: 1e-11 for family in FAMILIES}, weak_errors)
    for family in FAMILIES:
        assert abs(exact_scores[family]["score"] - 0.95) < 1e-12
        assert abs(weak_scores[family]["score"] - 0.1) < 1e-12
        assert small_scores[family]["score"] < exact_scores[family]["score"]
    manifest = {"protocol": "fourier-transport-v1", "seed": 920270,
                "pools": {"challenge": cases}, "families": FAMILIES,
                "weak_errors": weak_errors, "source": provenance,
                "independent_checks": checks,
                "runtime": {"python": sys.version, "numpy": np.__version__, "jax": jax.__version__},
                "metric": {"tau": 1e-10, "weak_score": 0.1, "strong_score": 0.95,
                           "aggregation": "equal arrays within case, equal cases within family, equal families"}}
    (ROOT / "private/challenge_pool/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not arguments.skip_cli_validation:
        for label, directory in (("strong", "private/reference"), ("weak", "private/reference/weak")):
            print(f"Validating {label} CLI on all {len(cases)} cases", flush=True)
            report = evaluate(ROOT / directory, isolate=False)
            (ROOT / f"private/{label}_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
            print(f"{label}: score={report['score']:.8f}, failures={report['failures']}", flush=True)
            assert report["failures"] == 0, report
            if label == "strong":
                assert report["score"] > 0.9, report
            else:
                assert abs(report["score"] - 0.1) < 1e-10, report


if __name__ == "__main__":
    main()
