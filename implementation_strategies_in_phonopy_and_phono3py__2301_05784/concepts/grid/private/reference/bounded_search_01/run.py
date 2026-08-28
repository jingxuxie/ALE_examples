"""Four predeclared physical stress cases; preserve the complete initial pilot."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
from itertools import product
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent
PRIVATE = REFERENCE.parent
CONCEPT = PRIVATE.parent
TARGET = CONCEPT.parents[1]
POOL = PRIVATE / "challenge_pool/bounded_search_01"
MANIFEST = PRIVATE / "challenge_pool/manifest_search_01.json"
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(TARGET / "author/runtime"))
sys.dont_write_bytecode = True

import numpy as np
import phonopy

from build import CORE_KEYS, SOURCE, digest, get_model, load_evaluator, write_json
from solve import grid_indices, make_grid

SPECS = [
    {"id": "search_million_aln_418901", "family": "million_full_branch_bz", "material": "AlN", "seed": 418901,
     "matrix": [[128, 32, 16], [0, 128, 32], [0, 0, 64]], "left": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
     "rebase": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "samples": 23},
    {"id": "search_tio2_oblique_418903", "family": "physical_oblique_anisotropy", "material": "TiO2", "seed": 418903,
     "matrix": [[192, 48, 0], [0, 96, 0], [0, 0, 4]], "left": [[1, 0, 0], [1, 1, 0], [0, 0, 1]],
     "rebase": [[1, 12, 0], [0, 1, 3], [0, 0, 1]], "samples": 53},
    {"id": "search_sno2_longwave_418907", "family": "physical_near_gamma", "material": "SnO2", "seed": 418907,
     "matrix": [[4096, 64, 16], [0, 8, 2], [0, 0, 4]], "left": [[1, 0, 0], [1, 1, 0], [0, 0, 1]],
     "rebase": [[1, 2, 0], [0, 1, 1], [0, 0, 1]], "samples": 41},
    {"id": "search_zr3n4_optical_418909", "family": "complex_physical_optical", "material": "Zr3N4", "seed": 418909,
     "matrix": [[64, 16, 8], [0, 64, 16], [0, 0, 32]], "left": [[1, 0, 0], [0, 1, 0], [1, 0, 1]],
     "rebase": [[1, 1, 0], [0, 1, 1], [0, 0, 1]], "samples": 31},
]


def protected_files():
    paths = list((CONCEPT / "participant").rglob("*")) + list((CONCEPT / "attempt").rglob("*"))
    initial = json.loads((PRIVATE / "challenge_pool/manifest.json").read_text())
    paths.append(PRIVATE / "challenge_pool/manifest.json")
    paths.extend(PRIVATE / case[key] for case in initial
                 for key in ("input", "reference", "baseline", "metadata", "baseline_metrics"))
    paths.extend([PRIVATE / "evaluator.py", REFERENCE / "build.py", REFERENCE / "solve.py",
                  REFERENCE / "provenance.json", TARGET / "author/scores/grid_pilot.json"])
    return {str(path.relative_to(TARGET)): digest(path) for path in paths if path.is_file()}


def load_physics(material):
    if material in ("AlN", "SnO2"):
        model, paths = get_model(material)
        return model, paths, 1.0, "Unmodified official harmonic force data; NAC disabled."
    if material == "Zr3N4":
        path = SOURCE / "phonopy/test/phonopy_params_Zr3N4.yaml"
        model = phonopy.load(path, is_nac=False, log_level=0)
        return model, [path], 1.0, "Official 14-atom primitive Zr3N4 fixture; all 42 physical branches."
    fixture = SOURCE / "phonopy/test/phonopy_disp_TiO2.yaml"
    forces = SOURCE / "phonopy/test/FORCE_SETS_TiO2"
    model = phonopy.load(fixture, force_sets_filename=forces, is_nac=False, log_level=0)
    note = ("Official anatase TiO2 displacement and force data, in a highly oblique unimodular primitive-cell "
            "representation. The large basis anisotropy is coordinate-induced and explicitly not a claim "
            "that the physical crystal has a correspondingly large intrinsic aspect ratio.")
    return model, [fixture, forces], 1.0, note


def thresholds(frequencies, spec, generator, gamma):
    lower = float(frequencies.min())
    upper = float(frequencies.max())
    span = max(upper - lower, 1.0)
    samples = list(np.linspace(lower - 0.03 * span, upper + 0.03 * span, spec["samples"]))
    selected = [0, 1, 2] if spec["family"] == "physical_near_gamma" else [frequencies.shape[1] // 2, frequencies.shape[1] - 2]
    for branch in selected:
        anchor = float(gamma[branch])
        width = max(1e-6, 1e-4 * float(np.ptp(frequencies[:, branch])))
        samples.extend([anchor - width, anchor + width])
        if spec["family"] == "physical_near_gamma":
            samples.extend(np.quantile(frequencies[:, branch], [1e-4, 1e-3, 0.01]).tolist())
    flattened = np.sort(frequencies.ravel())
    for index, sample in enumerate(samples):
        while True:
            position = np.searchsorted(flattened, sample)
            nearby = flattened[max(0, position - 1):position + 1]
            if np.min(np.abs(nearby - sample), initial=np.inf) > 1.1e-10:
                break
            sample += float(generator.uniform(2e-8, 1e-7))
        samples[index] = sample
    return np.unique(samples).astype(np.float64)


def generate(spec):
    started = time.monotonic()
    model, source_paths, distance_to_angstrom, note = load_physics(spec["material"])
    generator = np.random.default_rng(spec["seed"])
    triangular = np.array(spec["matrix"], dtype=np.int64)
    left = np.array(spec["left"], dtype=np.int64)
    rebase = np.array(spec["rebase"], dtype=np.int64)
    matrix = left @ triangular
    dimensions = np.diag(triangular)
    count = int(np.prod(dimensions))
    linear = np.arange(count, dtype=np.int64)
    addresses = np.column_stack((linear % dimensions[0], linear // dimensions[0] % dimensions[1],
                                 linear // (dimensions[0] * dimensions[1]))) @ left.T
    addresses = addresses[generator.permutation(count)]
    original_cell = model.primitive.cell * distance_to_angstrom
    basis = np.linalg.inv(rebase @ original_cell)
    data = {"grid_matrix": matrix, "grid_addresses": addresses, "reciprocal_lattice": basis,
            "tie_tolerance": np.array(1e-11 * max(1., float(np.sum(basis ** 2))))}
    fractional = addresses @ np.linalg.inv(matrix).T @ np.linalg.inv(rebase).T
    fractional -= np.rint(fractional)
    branches = len(model.primitive) * 3
    frequencies = np.empty((count, branches))
    for start in range(0, count, 4096):
        model.run_qpoints(fractional[start:start + 4096], with_eigenvectors=False)
        frequencies[start:start + 4096] = model.qpoints.frequencies
    model.run_qpoints([[0, 0, 0]], with_eigenvectors=False)
    gamma = model.qpoints.frequencies[0].copy()
    data["frequencies"] = frequencies
    data["sampling_points"] = thresholds(frequencies, spec, generator, gamma)
    grid = make_grid(data)
    permutation = grid_indices(addresses, grid)
    inverse = np.empty(count, dtype=np.int64)
    inverse[permutation] = np.arange(count)
    boundary = np.flatnonzero(np.diff(grid.gp_map) > 1)
    chosen = list(generator.integers(0, count, size=128))
    chosen.extend(generator.choice(boundary, size=128, replace=True).tolist())
    translations = generator.integers(-4, 5, size=(256, 3), dtype=np.int64)
    data["query_addresses"] = addresses[inverse[chosen]] + translations @ matrix.T
    gaps = np.diff(frequencies, axis=1)
    metadata = {"id": spec["id"], "family": spec["family"], "split": "search", "seed": spec["seed"],
        "N": count, "B": branches, "K": 256, "M": len(data["sampling_points"]), "all_physical_branches": True,
        "source_files": {str(path.relative_to(TARGET)): digest(path) for path in source_paths},
        "source_note": note, "original_cell_angstrom": original_cell.tolist(), "direct_rebase": rebase.tolist(),
        "reciprocal_condition": float(np.linalg.cond(basis)),
        "physical_reciprocal_condition": float(np.linalg.cond(np.linalg.inv(original_cell))),
        "frequency_ranges_THz": np.column_stack((frequencies.min(axis=0), frequencies.max(axis=0))).tolist(),
        "gamma_frequencies_THz": gamma.tolist(), "minimum_branch_gap_THz": float(gaps.min()),
        "branch_gaps_below_1e_7_THz": int(np.sum(gaps < 1e-7)),
        "force_constants_sha256": hashlib.sha256(model.force_constants.tobytes()).hexdigest(),
        "input_generation_seconds": time.monotonic() - started,
        "tolerance_policy": "Unchanged initial absolute BZ-distance tolerance and >1e-10-THz knot separation."}
    return data, metadata


def oracle(input_path, output_path, directory):
    directory.mkdir(parents=True, exist_ok=True)
    resources = directory / "resources.txt"
    command = ["/usr/bin/time", "-f", "%M", "-o", str(resources), sys.executable, "-B",
               str(REFERENCE / "solve.py"), str(input_path), str(output_path)]

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (8192 * 1024 ** 2,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (183,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=True, preexec_fn=limits)
    try:
        stdout, stderr = process.communicate(timeout=180)
        status = "ok" if process.returncode == 0 and output_path.is_file() else "error"
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        status = "timeout"
    elapsed = time.monotonic() - started
    rss = None
    if resources.exists():
        for line in reversed(resources.read_text().splitlines()):
            if line.isdigit():
                rss = int(line)
                break
    result = {"status": status, "seconds": elapsed, "max_rss_kb": rss,
              "returncode": process.returncode, "stdout": stdout, "stderr": stderr, "command": command,
              "timeout": 180, "memory_mb": 8192, "output_path": str(output_path)}
    write_json(directory / "execution.json", result)
    return result


def validate(data, reference, metadata):
    assert all(np.isfinite(reference[key]).all() for key in CORE_KEYS)
    np.testing.assert_allclose(reference["cumulative"][0], 0, atol=1e-12)
    np.testing.assert_allclose(reference["cumulative"][-1], 1, atol=2e-10)
    assert np.min(np.diff(reference["cumulative"], axis=0)) >= -1e-10
    assert reference["dos"].min() >= -1e-10
    original_basis = np.linalg.inv(np.array(metadata["original_cell_angstrom"]))
    rebase = np.array(metadata["direct_rebase"], dtype=np.int64)
    inverse_rebase = np.rint(np.linalg.inv(rebase)).astype(np.int64)
    singular = np.linalg.svd(original_basis, compute_uv=False).min()
    radius = int(np.ceil(np.linalg.norm(original_basis, axis=0).sum() / (2 * singular))) + 1
    shifts = np.array(list(product(range(-radius, radius + 1), repeat=3)), dtype=np.int64)
    selected = np.unique(np.linspace(0, 255, 24).astype(int))
    for query in selected:
        point = inverse_rebase @ np.linalg.solve(data["grid_matrix"], data["query_addresses"][query])
        choices = shifts - np.rint(point).astype(np.int64)
        cartesian = (choices + point) @ original_basis.T
        squared = np.einsum("ij,ij->i", cartesian, cartesian)
        wanted = np.unique(choices[squared <= squared.min() + data["tie_tolerance"]] @ rebase.T, axis=0)
        start, stop = reference["image_offsets"][query:query + 2]
        np.testing.assert_array_equal(reference["image_shifts"][start:stop], wanted)
        np.testing.assert_allclose(reference["distance2"][query], squared.min(), rtol=1e-8, atol=1e-11)
    return {"passed": True, "independent_cvp_queries": len(selected), "certified_original_basis_radius": radius,
            "exact_tie_queries": int(np.sum(np.diff(reference["image_offsets"]) > 1)),
            "maximum_image_multiplicity": int(np.diff(reference["image_offsets"]).max())}


def main():
    if (HERE / "report.json").exists():
        raise SystemExit("Completed search evidence is not overwritten")
    POOL.mkdir(parents=True, exist_ok=True)
    protection_path = HERE / "protected_initial_sha256.json"
    protected = json.loads(protection_path.read_text()) if protection_path.exists() else protected_files()
    assert protected == protected_files()
    if not protection_path.exists():
        write_json(protection_path, protected)
    evaluator = load_evaluator()
    shared = evaluator.load_shared()
    report = {"policy": "At most four predeclared source-grounded cases; no changed scores/tolerances; no iterative scale escalation.",
              "planned_cases": SPECS, "initial_score_sha256": digest(TARGET / "author/scores/grid_pilot.json"),
              "submission_sha256": digest(CONCEPT / "attempt/solve.py"),
              "scorer_sha256": digest(PRIVATE / "evaluator.py"), "shared_harness_sha256": digest(TARGET / "author/evaluation.py"),
              "counterexample_signal": "Reference validates and fits 180s/8192MiB, but submitted execution fails or either component quality <0.98. This selection rule does not alter scoring.",
              "cases": []}
    if (HERE / "progress.json").exists():
        report = json.loads((HERE / "progress.json").read_text())
        report["planned_cases"] = SPECS
    report["source_feasibility_exclusion"] = (
        "Graphene-siesta was screened but not made into a scored challenge: only one force file and no "
        "explicit displaced structure are supplied; the private reader has obsolete setters and a unit "
        "parsing mismatch. No ambiguous inferred-displacement spectrum is admitted. TiO2 has explicit "
        "displacement/force pairs and replaces this source candidate before scored evaluation.")
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    completed = {case["id"] for case in report["cases"]}
    previous_elapsed = report.get("elapsed_seconds", 0.0)
    started = time.monotonic()
    for spec in SPECS:
        if spec["id"] in completed:
            print("PRESERVING completed " + spec["id"], flush=True)
            continue
        print("GENERATING " + spec["id"], flush=True)
        data, metadata = generate(spec)
        identifier = spec["id"]
        case = {"id": identifier, "family": spec["family"], "split": "search", "timeout": 180, "memory_mb": 8192,
                "keys": ["geometry", "spectral"], "core_keys": CORE_KEYS,
                **{key: f"challenge_pool/bounded_search_01/{identifier}.{suffix}"
                   for key, suffix in (("input", "input.npz"), ("reference", "reference.npz"),
                                       ("baseline", "baseline.npz"), ("baseline_metrics", "baseline.json"), ("metadata", "json"))}}
        input_path = PRIVATE / case["input"]
        np.savez_compressed(input_path, **data)
        metadata.update(case)
        metadata["input_sha256"] = digest(input_path)
        write_json(PRIVATE / case["metadata"], metadata)
        print("ORACLE " + identifier + " " + str((metadata["N"], metadata["B"], metadata["M"])), flush=True)
        execution = oracle(input_path, PRIVATE / case["reference"], HERE / identifier / "oracle")
        result = {"id": identifier, "family": spec["family"], "N": metadata["N"], "B": metadata["B"],
                  "M": metadata["M"], "oracle": execution, "counterexample": False}
        if execution["status"] == "ok":
            with np.load(PRIVATE / case["reference"], allow_pickle=False) as reference:
                result["reference_validation"] = validate(data, reference, metadata)
            metadata["reference_sha256"] = digest(PRIVATE / case["reference"])
            metadata["reference_validation"] = result["reference_validation"]
            baseline = shared.sandbox_run(CONCEPT / "participant/workspace/solve.py", input_path,
                HERE / identifier / "baseline", CONCEPT / "participant", timeout=180, memory_mb=8192)
            if baseline["status"] != "ok":
                raise RuntimeError("Baseline failed: " + str(baseline))
            (PRIVATE / case["baseline"]).write_bytes(Path(baseline["output_path"]).read_bytes())
            write_json(PRIVATE / case["baseline_metrics"], baseline)
            print("SUBMISSION " + identifier, flush=True)
            submitted = shared.sandbox_run(CONCEPT / "attempt/solve.py", input_path,
                HERE / identifier / "submission", CONCEPT / "participant", timeout=180, memory_mb=8192)
            write_json(HERE / identifier / "submission/execution.json", submitted)
            result["submission"] = submitted
            result["baseline"] = baseline
            if submitted["status"] == "ok":
                with np.load(submitted["output_path"], allow_pickle=False) as actual, \
                     np.load(PRIVATE / case["reference"], allow_pickle=False) as reference, \
                     np.load(PRIVATE / case["baseline"], allow_pickle=False) as weak:
                    result["components"] = evaluator.score_case(actual, reference, weak, case, data)
                result["core_score"] = float(np.mean([value["score"] for value in result["components"].values()]))
                result["counterexample"] = min(value["score"] for value in result["components"].values()) < 0.98
            else:
                result["core_score"] = 0.0
                result["counterexample"] = True
            manifest.append(case)
            write_json(MANIFEST, manifest)
        else:
            result["rejection"] = "Reference does not fit the existing budget; not a valid counterexample."
        write_json(PRIVATE / case["metadata"], metadata)
        report["cases"].append(result)
        report["elapsed_seconds"] = previous_elapsed + time.monotonic() - started
        write_json(HERE / "progress.json", report)
        print(json.dumps({key: result.get(key) for key in ("id", "N", "B", "M", "core_score", "counterexample", "rejection")}), flush=True)
        del data
    after = protected_files()
    assert protected == after, "Protected original pilot artifacts changed"
    report["protected_initial_unchanged"] = True
    report["valid_challenges"] = len(manifest)
    report["counterexamples"] = [case["id"] for case in report["cases"] if case["counterexample"]]
    report["outcome"] = "counterexample_requires_root_cause_review" if report["counterexamples"] else "rejected_as_robustly_solved_in_bounded_search"
    report["elapsed_seconds"] = previous_elapsed + time.monotonic() - started
    write_json(HERE / "report.json", report)
    print("OUTCOME " + report["outcome"], flush=True)


if __name__ == "__main__":
    main()
