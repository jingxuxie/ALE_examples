"""Validate reference conventions independently and audit stored artifacts."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from itertools import combinations, product
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
TARGET = CONCEPT.parents[1]
sys.path.insert(0, str(TARGET / "author/runtime"))

import numpy as np
from scipy.spatial import ConvexHull

from build import design, digest, load_evaluator, write_json
from solve import grid_indices, make_grid, solve


def nearest_images(data, result):
    basis = data["reciprocal_lattice"]
    inverse = np.linalg.inv(data["grid_matrix"])
    smallest = np.linalg.svd(basis, compute_uv=False).min()
    radius = int(np.ceil(np.linalg.norm(basis, axis=0).sum() / (2 * smallest))) + 1
    translations = np.array(list(product(range(-radius, radius + 1), repeat=3)), dtype=np.int64)
    for query, address in enumerate(data["query_addresses"]):
        point = inverse @ address
        center = -np.rint(point).astype(np.int64)
        shifts = translations + center
        cartesian = (shifts + point) @ basis.T
        squared = np.einsum("ij,ij->i", cartesian, cartesian)
        minimum = squared.min()
        wanted = np.unique(shifts[squared <= minimum + data["tie_tolerance"]], axis=0)
        start, stop = result["image_offsets"][query : query + 2]
        np.testing.assert_array_equal(result["image_shifts"][start:stop], wanted)
        np.testing.assert_allclose(result["distance2"][query], minimum, rtol=1e-10, atol=1e-12)
    return {"queries": len(data["query_addresses"]), "certified_box_radius": radius}


def tetrahedra_values(data):
    matrix = data["grid_matrix"]
    count = len(data["grid_addresses"])
    adjugate = np.rint(np.linalg.inv(matrix) * count).astype(np.int64)
    keys = data["grid_addresses"] @ adjugate.T % count
    lookup = {tuple(key): row for row, key in enumerate(keys)}
    vertices = np.array([[vertex & 1, (vertex >> 1) & 1, (vertex >> 2) & 1]
                         for vertex in range(8)], dtype=np.int64)
    microcell = data["reciprocal_lattice"] @ np.linalg.inv(matrix)
    diagonals = np.array([[1, 1, 1], [-1, 1, 1], [1, -1, 1], [1, 1, -1]]) @ microcell.T
    diagonal = int(np.argmin(np.einsum("ij,ij->i", diagonals, diagonals)))
    sets = [
        [[0, 7, 1, 3], [0, 7, 1, 5], [0, 7, 2, 3], [0, 7, 2, 6], [0, 7, 4, 5], [0, 7, 4, 6]],
        [[1, 6, 0, 2], [1, 6, 0, 4], [1, 6, 2, 3], [1, 6, 3, 7], [1, 6, 4, 5], [1, 6, 5, 7]],
        [[2, 5, 0, 1], [2, 5, 0, 4], [2, 5, 1, 3], [2, 5, 3, 7], [2, 5, 4, 6], [2, 5, 6, 7]],
        [[3, 4, 0, 1], [3, 4, 0, 2], [3, 4, 1, 5], [3, 4, 2, 6], [3, 4, 5, 7], [3, 4, 6, 7]],
    ]
    result = []
    for address in data["grid_addresses"]:
        corner_keys = (address + vertices) @ adjugate.T % count
        rows = [lookup[tuple(key)] for key in corner_keys]
        corners = data["frequencies"][rows]
        result.extend(corners[np.array(sets[diagonal])])
    return np.array(result)


def clipped_simplex_cdf(energies, threshold):
    vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    inside = energies < threshold
    if inside.all():
        return 1.0
    if not inside.any():
        return 0.0
    points = list(vertices[inside])
    for first, second in combinations(range(4), 2):
        if inside[first] != inside[second]:
            fraction = (threshold - energies[first]) / (energies[second] - energies[first])
            points.append(vertices[first] + fraction * (vertices[second] - vertices[first]))
    return float(6 * ConvexHull(np.array(points)).volume)


def independent_spectral_check():
    with np.load(CONCEPT / "participant/input/example.npz", allow_pickle=False) as archive:
        data = dict(archive)
    thresholds = np.unique([float(np.quantile(data["frequencies"][:, branch], 0.43)) + 3.14159e-5
                            for branch in range(data["frequencies"].shape[1])])
    separation = np.min(np.abs(thresholds[:, None, None] - data["frequencies"][None]))
    step = min(1e-5, float(separation) * 0.1)
    data["sampling_points"] = thresholds
    official = solve(data, block_size=17)
    tetrahedra = tetrahedra_values(data)
    cumulative = np.zeros_like(official["cumulative"])
    derivative = np.zeros_like(cumulative)
    for sample, threshold in enumerate(thresholds):
        for branch in range(cumulative.shape[1]):
            values = tetrahedra[:, :, branch]
            cumulative[sample, branch] = np.mean([clipped_simplex_cdf(energies, threshold) for energies in values])
            derivative[sample, branch] = np.mean([
                (clipped_simplex_cdf(energies, threshold + step) - clipped_simplex_cdf(energies, threshold - step)) / (2 * step)
                for energies in values])
    np.testing.assert_allclose(official["cumulative"], cumulative, rtol=2e-9, atol=2e-10)
    np.testing.assert_allclose(official["dos"], derivative, rtol=2e-5, atol=2e-7)
    return {"method": "Independent clipping of the barycentric simplex, convex-hull volumes, and central derivatives",
            "tetrahedra": len(tetrahedra), "thresholds": len(thresholds), "derivative_step": step,
            "maximum_cumulative_error": float(np.max(np.abs(official["cumulative"] - cumulative))),
            "maximum_dos_error": float(np.max(np.abs(official["dos"] - derivative)))}


def main():
    private = CONCEPT / "private"
    manifest = json.loads((private / "challenge_pool/manifest.json").read_text())
    evaluator = load_evaluator()
    report = {"cases": [], "independent_spectral_check": independent_spectral_check()}
    for case in manifest:
        metadata = json.loads((private / case["metadata"]).read_text())
        with np.load(private / case["input"], allow_pickle=False) as data, \
             np.load(private / case["reference"], allow_pickle=False) as reference, \
             np.load(private / case["baseline"], allow_pickle=False) as baseline:
            count = len(data["grid_addresses"])
            assert count == round(np.linalg.det(data["grid_matrix"]))
            assert metadata["N"] == count
            grid = make_grid(data)
            permutation = grid_indices(data["grid_addresses"], grid)
            np.testing.assert_array_equal(np.sort(permutation), np.arange(count))
            sorted_values = np.sort(data["frequencies"].ravel())
            positions = np.searchsorted(sorted_values, data["sampling_points"])
            distances = [min(abs(float(sorted_values[neighbor] - threshold))
                             for neighbor in (max(0, position - 1), min(len(sorted_values) - 1, position)))
                         for threshold, position in zip(data["sampling_points"], positions)]
            assert min(distances) > 1e-10
            assert np.all(reference["dos"] >= -1e-10)
            assert np.all(np.diff(reference["cumulative"], axis=0) >= -1e-10)
            np.testing.assert_allclose(reference["cumulative"][0], 0, atol=1e-12)
            np.testing.assert_allclose(reference["cumulative"][-1], 1, atol=2e-10)
            np.testing.assert_allclose(reference["dos"][[0, -1]], 0, atol=1e-12)
            if count == 1:
                wanted = (data["sampling_points"][:, None] > data["frequencies"][0]).astype(float)
                np.testing.assert_allclose(reference["cumulative"], wanted, atol=1e-14)
                np.testing.assert_allclose(reference["dos"], 0, atol=1e-14)
            geometry = nearest_images(data, reference)
            quality = evaluator.score_case(reference, reference, baseline, case, data)
            assert all(component["score"] == 1.0 for component in quality.values())
            weak_quality = evaluator.score_case(baseline, reference, baseline, case, data)
            for component in weak_quality.values():
                if component["baseline_error"] >= 1e-8:
                    assert component["score"] == 0.5
            missing_geometry = {"dos": reference["dos"], "cumulative": reference["cumulative"]}
            independent = evaluator.score_case(missing_geometry, reference, baseline, case, data)
            assert independent["geometry"]["score"] == 0 and independent["spectral"]["score"] == 1
            perturbed = dict(reference)
            perturbed["cumulative"] = reference["cumulative"] + 1e-10
            tiny_error = evaluator.score_case(perturbed, reference, reference, case, data)
            assert 0 < tiny_error["spectral"]["score"] < 1
            assert tiny_error["geometry"]["score"] == 1
            perturbed["cumulative"] = reference["cumulative"] + 2e-10
            larger_error = evaluator.score_case(perturbed, reference, reference, case, data)
            assert larger_error["spectral"]["score"] < tiny_error["spectral"]["score"]
            assert digest(private / case["input"]) == metadata["official"]["input_sha256"]
            assert digest(private / case["reference"]) == metadata["official"]["reference_sha256"]
            item = {"id": case["id"], "N": count, "geometry_validation": geometry,
                    "minimum_threshold_separation_THz": min(distances), "reference_components": quality,
                    "baseline_components": weak_quality, "exact_tie_queries": metadata["exact_tie_queries"]}
            report["cases"].append(item)
            print(json.dumps({"id": case["id"], "validation": "ok", "N": count}), flush=True)
    pool_hashes = {digest(private / case["input"]) for case in manifest if case["split"] == "pool"}
    heldout_hashes = {digest(private / case["input"]) for case in manifest if case["split"] == "heldout"}
    assert not pool_hashes & heldout_hashes
    first = design("skew", "heldout", 912001)
    second = design("skew", "heldout", 912019)
    assert not np.array_equal(first[1], second[1]) or not np.array_equal(first[3], second[3])
    report["fresh_seed_design_check"] = True
    report["pool_heldout_disjoint"] = True
    report["passed"] = True
    write_json(HERE / "validation.json", report)


if __name__ == "__main__":
    main()
