"""Build physical inputs, pinned official references, and measured baselines."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
PRIVATE = CONCEPT / "private"
TARGET = CONCEPT.parents[1]
RUNTIME = TARGET / "author/runtime"
SOURCE = TARGET / "author/source"
sys.path.insert(0, str(RUNTIME))
sys.dont_write_bytecode = True

import numpy as np
import phonopy
import phono3py
import spglib

from solve import grid_indices, make_grid

FAMILIES = {"skew": "non_diagonal_skew", "ties": "exact_boundary_ties",
            "optical": "flat_close_branches", "flat": "flat_close_branches",
            "dense": "dense_scale"}
CORE_KEYS = ["image_offsets", "image_shifts", "distance2", "dos", "cumulative"]
MODELS = {}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def get_model(material):
    if material not in MODELS:
        if material == "AlN":
            fixture = SOURCE / "phono3py/test/phono3py_params_AlN332.yaml.xz"
            crystal = phono3py.load(fixture, produce_fc=False, is_nac=False, log_level=0)
            if crystal.fc2 is None:
                crystal.produce_fc2()
            model = phonopy.Phonopy(crystal.unitcell, crystal.supercell_matrix,
                                    primitive_matrix=crystal.primitive_matrix)
            model.force_constants = crystal.fc2
            paths = [fixture]
        else:
            fixture = SOURCE / "phonopy/test/phonopy_disp_SnO2.yaml"
            forces = SOURCE / "phonopy/test/FORCE_SETS_SnO2"
            model = phonopy.load(fixture, force_sets_filename=forces,
                                 is_nac=False, log_level=0)
            paths = [fixture, forces]
        MODELS[material] = (model, paths)
    return MODELS[material]


def design(kind, split, seed):
    generator = np.random.default_rng(np.random.SeedSequence([seed, list(FAMILIES).index(kind)]))
    heldout = split == "heldout"
    if kind == "dense":
        diagonal = [50, 48, 44] if heldout else [48, 48, 48]
        material = "SnO2" if heldout else "AlN"
    elif kind == "optical":
        diagonal = [24, 20, 18] if heldout else [20, 18, 16]
        material = "AlN" if heldout else "SnO2"
    elif kind == "ties":
        diagonal = [20, 16, 14] if heldout else [18, 18, 12]
        material = "SnO2" if heldout else "AlN"
    elif kind == "flat":
        diagonal = [1, 1, 1]
        material = "AlN" if heldout else "SnO2"
    else:
        diagonal = [18, 16, 12] if heldout else [12, 14, 10]
        material = "SnO2" if heldout else "AlN"
    if kind not in ("dense", "flat"):
        diagonal[0] += 2 * int(generator.integers(0, 3))
    triangular = np.diag(diagonal).astype(np.int64)
    triangular[0, 1] = 2 * int(generator.integers(1, 4))
    triangular[0, 2] = 2 * int(generator.integers(0, 3))
    triangular[1, 2] = 2 * int(generator.integers(1, 4))
    if kind == "flat":
        triangular[0, 1] = 1
        triangular[0, 2] = 0
        triangular[1, 2] = 1
    left = np.eye(3, dtype=np.int64)
    if heldout or kind == "skew":
        left[1, 0] = 1
    rebase = np.eye(3, dtype=np.int64)
    if material == "SnO2":
        rebase[0, 1] = 1 + int(generator.integers(0, 2))
        rebase[1, 2] = 1
    elif heldout:
        rebase[0, 2] = 1
    return material, triangular, left, rebase, generator


def sampling_points(frequencies, kind, generator):
    minimum = float(frequencies.min())
    maximum = float(frequencies.max())
    span = max(maximum - minimum, 1.0)
    thresholds = list(np.linspace(minimum - span * 0.03, maximum + span * 0.03,
                                  29 if kind == "dense" else 41))
    for branch in range(frequencies.shape[1]):
        values = frequencies[:, branch]
        for quantile in (0.15, 0.5, 0.85):
            anchor = float(np.quantile(values, quantile))
            offset = max(float(np.ptp(values)) * 0.003, 2e-7)
            thresholds.extend([anchor - offset, anchor + offset])
    sorted_values = np.sort(frequencies.ravel())
    for index, threshold in enumerate(thresholds):
        for retry in range(100):
            position = np.searchsorted(sorted_values, threshold)
            neighbors = sorted_values[max(0, position - 1) : position + 1]
            if np.min(np.abs(neighbors - threshold), initial=np.inf) > 1.1e-10:
                break
            threshold += (2e-8 + float(generator.random()) * 8e-8) * (retry + 1)
        thresholds[index] = threshold
    return np.unique(np.array(thresholds, dtype=np.float64))


def make_input(kind, split, seed, smoke=False):
    material, triangular, left, rebase, generator = design(kind, split, seed)
    if smoke:
        triangular = np.array([[4, 2, 0], [0, 4, 2], [0, 0, 3]], dtype=np.int64)
        left = np.eye(3, dtype=np.int64)
        rebase = np.eye(3, dtype=np.int64)
    model, source_paths = get_model(material)
    matrix = left @ triangular
    dimensions = np.diag(triangular)
    count = int(np.prod(dimensions))
    linear = np.arange(count, dtype=np.int64)
    representatives = np.column_stack((linear % dimensions[0],
                                      linear // dimensions[0] % dimensions[1],
                                      linear // (dimensions[0] * dimensions[1]))) @ left.T
    representatives = representatives[generator.permutation(count)]
    cell = rebase @ model.primitive.cell
    reciprocal = np.linalg.inv(cell)
    data = {"grid_matrix": matrix, "reciprocal_lattice": reciprocal,
            "grid_addresses": np.array(representatives, dtype=np.int64, order="C"),
            "tie_tolerance": np.array(1e-11 * max(1.0, float(np.sum(reciprocal ** 2))))}
    fractional = representatives @ np.linalg.inv(matrix).T
    original_fractional = fractional @ np.linalg.inv(rebase).T
    original_fractional -= np.rint(original_fractional)
    frequencies = []
    for start in range(0, count, 4096):
        model.run_qpoints(original_fractional[start : start + 4096], with_eigenvectors=False)
        frequencies.append(model.qpoints.frequencies.copy())
    full_frequencies = np.concatenate(frequencies)
    if kind in ("optical", "flat"):
        branches = [3, 4, 9, 10, 11] if material == "AlN" else [6, 7, 15, 16, 17]
    else:
        branches = [0, 8, 9, 11] if material == "AlN" else [0, 14, 16, 17]
    data["frequencies"] = np.array(full_frequencies[:, branches], dtype=np.float64, order="C")
    data["sampling_points"] = sampling_points(data["frequencies"], kind, generator)
    grid = make_grid(data)
    indices = grid_indices(representatives, grid)
    inverse = np.empty(count, dtype=np.int64)
    inverse[indices] = np.arange(count)
    boundary = np.flatnonzero(np.diff(grid.gp_map) > 1)
    number_queries = 32 if smoke or kind == "flat" else (512 if kind == "dense" else 192)
    selected = list(generator.integers(0, count, size=number_queries // 2))
    if len(boundary):
        selected.extend(generator.choice(boundary, size=number_queries - len(selected), replace=True).tolist())
    else:
        selected.extend(generator.integers(0, count, size=number_queries - len(selected)).tolist())
    selected[0] = int(indices[np.argmin(np.sum(representatives ** 2, axis=1))])
    queries = representatives[inverse[selected]].copy()
    translations = generator.integers(-3, 4, size=(number_queries, 3), dtype=np.int64)
    translations[0] = 0
    queries += translations @ matrix.T
    data["query_addresses"] = np.array(queries, dtype=np.int64, order="C")
    provenance = {
        "material": material, "source_files": {str(path.relative_to(TARGET)): digest(path) for path in source_paths},
        "primitive_cell_original": model.primitive.cell.tolist(), "direct_basis_rebase": rebase.tolist(),
        "force_constants_shape": list(model.force_constants.shape),
        "force_constants_sha256": hashlib.sha256(model.force_constants.tobytes()).hexdigest(),
        "frequency_procedure": "Official harmonic force constants, signed sorted eigenfrequencies in THz; NAC disabled; no synthetic energies or random force constants.",
        "force_fit": "phono3py.produce_fc2 (traditional)" if material == "AlN" else "phonopy.load harmonic FORCE_SETS (traditional)",
        "band_indices_zero_based": branches, "grid_matrix": matrix.tolist(), "N": count,
        "B": len(branches), "K": number_queries, "M": len(data["sampling_points"]),
        "frequency_ranges_THz": np.column_stack((data["frequencies"].min(axis=0), data["frequencies"].max(axis=0))).tolist(),
        "minimum_selected_band_separation_THz": float(np.diff(data["frequencies"], axis=1).min()),
        "exactly_flat_columns": int(np.sum(np.ptp(data["frequencies"], axis=0) == 0)),
        "flat_interpretation": "One-point periodic interpolation of actual Gamma modes" if kind == "flat" else None,
    }
    return data, provenance


def load_evaluator():
    specification = importlib.util.spec_from_file_location("grid_evaluator", PRIVATE / "evaluator.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def official_reference(input_path, output_path, identifier):
    logs = HERE / "runs" / identifier
    logs.mkdir(parents=True, exist_ok=True)
    memory_path = logs / "official.resources.txt"
    command = ["/usr/bin/time", "-f", "%M", "-o", str(memory_path), sys.executable,
               "-B", str(HERE / "solve.py"), str(input_path), str(output_path)]
    start = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True, timeout=900)
    elapsed = time.perf_counter() - start
    (logs / "official.stdout.txt").write_text(process.stdout)
    (logs / "official.stderr.txt").write_text(process.stderr)
    if process.returncode or not output_path.exists():
        raise RuntimeError("Official reference failed: " + process.stderr[-3000:])
    return {"status": "ok", "seconds": elapsed, "max_rss_kb": int(memory_path.read_text().strip()),
            "command": command, "input_sha256": digest(input_path), "reference_sha256": digest(output_path)}


def measure_baseline(case, evaluator):
    execution = evaluator.load_shared().sandbox_run(
        CONCEPT / "participant/workspace/solve.py", PRIVATE / case["input"],
        HERE / "runs" / case["id"] / "baseline", CONCEPT / "participant",
        timeout=case["timeout"], memory_mb=case["memory_mb"])
    if execution["status"] != "ok":
        write_json(HERE / "runs" / case["id"] / "baseline_failure.json", execution)
        raise RuntimeError("Baseline sandbox failed: " + execution["stderr"])
    baseline_path = PRIVATE / case["baseline"]
    baseline_path.write_bytes(Path(execution["output_path"]).read_bytes())
    with np.load(baseline_path, allow_pickle=False) as actual, \
         np.load(PRIVATE / case["reference"], allow_pickle=False) as reference, \
         np.load(PRIVATE / case["input"], allow_pickle=False) as data:
        execution["components"] = evaluator.score_case(actual, reference, actual, case, data)
    execution["output_path"] = case["baseline"]
    execution["baseline_sha256"] = digest(baseline_path)
    write_json(PRIVATE / case["baseline_metrics"], execution)
    print(json.dumps({"id": case["id"], "baseline_seconds": execution["seconds"],
                      "baseline_rss_kb": execution["max_rss_kb"], "components": execution["components"]}), flush=True)


def provenance():
    expected = ("2.43.4", "3.19.2", "2.5.0", "2.2.6")
    actual = (phonopy.__version__, phono3py.__version__, spglib.__version__, np.__version__)
    if actual != expected:
        raise RuntimeError("Wrong private runtime: " + repr(actual))
    revisions = {name: subprocess.check_output(["git", "-C", str(SOURCE / name), "rev-parse", "HEAD"], text=True).strip()
                 for name in ("phonopy", "phono3py")}
    modules = ["phono3py/phonon/grid.py", "phono3py/other/tetrahedron_method.py",
               "phonopy/structure/tetrahedron_method.py", "phonopy/harmonic/dynamical_matrix.py"]
    modules.extend(str(path.relative_to(RUNTIME)) for package in ("phono3py", "phonopy")
                   for path in (RUNTIME / package).glob("*.so"))
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "source_revisions": revisions,
            "private_versions": dict(zip(("phonopy", "phono3py", "spglib", "numpy"), actual)),
            "module_sha256": {name: digest(RUNTIME / name) for name in modules},
            "runtime4": {"phonopy": "4.1.0", "role": "optional independent validation, not generating strong references"},
            "official_calls": ["phono3py.phonon.grid.BZGrid (SNF and dense BZ image map)",
                               "phono3py.other.tetrahedron_method.get_integration_weights(function='I'/'J')",
                               "phonopy.Phonopy.run_qpoints from official fitted harmonic force constants"],
            "ablation": "Author-built diagonal-component rounding plus histogram, not an alleged historical software bug.",
            "geometry_tolerance": "Official BZ candidate multiplicities filtered to the public absolute squared-distance tolerance.",
            "threads": {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("initial", "pool", "heldout"), default="initial")
    parser.add_argument("--seed", type=int, default=17029)
    parser.add_argument("--heldout-seed", type=int, default=79043)
    parser.add_argument("--family", choices=tuple(FAMILIES), action="append")
    parser.add_argument("--measure-baseline-only", action="store_true")
    args = parser.parse_args()
    pool = PRIVATE / "challenge_pool"
    pool.mkdir(parents=True, exist_ok=True)
    manifest_path = pool / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    evaluator = load_evaluator()
    if args.measure_baseline_only:
        for case in manifest:
            measure_baseline(case, evaluator)
        return
    write_json(HERE / "provenance.json", provenance())
    smoke_path = CONCEPT / "participant/input/example.npz"
    if not smoke_path.exists():
        smoke_path.parent.mkdir(parents=True, exist_ok=True)
        data, metadata = make_input("skew", "pool", 6031, smoke=True)
        np.savez_compressed(smoke_path, **data)
        metadata.update(id="smoke", family="unlabeled_public", split="smoke", core_keys=CORE_KEYS)
        write_json(HERE / "smoke.metadata.json", metadata)
        metrics = official_reference(smoke_path, HERE / "smoke.reference.npz", "smoke")
        write_json(HERE / "smoke.official.json", metrics)
    splits = [("pool", args.seed), ("heldout", args.heldout_seed)] if args.split == "initial" else [(args.split, args.seed)]
    for split, seed in splits:
        for kind in args.family or FAMILIES:
            identifier = f"{split}_{kind}_{seed}"
            if any(case["id"] == identifier for case in manifest):
                print("Already built " + identifier, flush=True)
                continue
            print("Building " + identifier, flush=True)
            start = time.perf_counter()
            data, metadata = make_input(kind, split, seed)
            case = {"id": identifier, "family": FAMILIES[kind], "split": split,
                    "input": f"challenge_pool/{identifier}.input.npz",
                    "reference": f"challenge_pool/{identifier}.reference.npz",
                    "baseline": f"challenge_pool/{identifier}.baseline.npz",
                    "baseline_metrics": f"challenge_pool/{identifier}.baseline.json",
                    "metadata": f"challenge_pool/{identifier}.json",
                    "timeout": 180, "memory_mb": 8192, "keys": ["geometry", "spectral"],
                    "core_keys": CORE_KEYS, "seed": seed}
            np.savez_compressed(PRIVATE / case["input"], **data)
            official = official_reference(PRIVATE / case["input"], PRIVATE / case["reference"], identifier)
            with np.load(PRIVATE / case["reference"], allow_pickle=False) as reference:
                multiplicities = np.diff(reference["image_offsets"])
                metadata["exact_tie_queries"] = int(np.sum(multiplicities > 1))
                metadata["maximum_image_multiplicity"] = int(multiplicities.max())
            metadata.update(case, official=official, build_seconds=time.perf_counter() - start,
                            input_bytes=(PRIVATE / case["input"]).stat().st_size)
            write_json(PRIVATE / case["metadata"], metadata)
            measure_baseline(case, evaluator)
            manifest.append(case)
            write_json(manifest_path, manifest)
    print("Manifest cases: " + str(len(manifest)), flush=True)


if __name__ == "__main__":
    main()
