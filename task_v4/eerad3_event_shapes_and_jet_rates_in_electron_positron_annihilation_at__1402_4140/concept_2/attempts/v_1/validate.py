import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np


ASSETS = Path(__file__).resolve().parents[2] / "participant"
sys.path.insert(0, str(ASSETS / "workspace"))
from shapes import calculate


SHAPES = ("tau", "C", "rho_H", "B_T", "B_W", "y23")
OBSERVABLES = SHAPES + ("y34", "y45")


def independent_calculate(event):
    energy = float(event[:, 0].sum())
    momenta = event[:, 1:]
    subsets = list(itertools.combinations(range(5), 1))
    subsets += list(itertools.combinations(range(5), 2))
    candidates = [momenta[list(subset)].sum(axis=0) for subset in subsets]
    candidates.sort(key=lambda momentum: np.linalg.norm(momentum), reverse=True)
    axis = candidates[0] / np.linalg.norm(candidates[0])
    projections = momenta @ axis
    masses = []
    broadenings = []
    occupancies = []
    for selection in (projections > 0, projections <= 0):
        hemisphere = event[selection].sum(axis=0)
        masses.append((hemisphere[0] ** 2 - np.dot(hemisphere[1:], hemisphere[1:])) / energy ** 2)
        broadenings.append(sum(np.linalg.norm(np.cross(momentum, axis))
                               for momentum in momenta[selection]) / (2 * energy))
        occupancies.append(int(selection.sum()))
    c_parameter = 0.0
    pair_invariants = []
    for first, second in itertools.combinations(range(5), 2):
        dot_product = np.dot(momenta[first], momenta[second])
        energy_product = event[first, 0] * event[second, 0]
        c_parameter += 3 * (energy_product - dot_product ** 2 / energy_product) / energy ** 2
        pair_invariants.append(2 * (energy_product - dot_product))
    values = {
        "tau": 1 - 2 * np.linalg.norm(candidates[0]) / energy,
        "C": c_parameter,
        "rho_H": max(masses),
        "B_T": sum(broadenings),
        "B_W": max(broadenings),
        "thrust_gap": 2 * (np.linalg.norm(candidates[0]) - np.linalg.norm(candidates[1])) / energy,
        "hemisphere_margin": min(abs(projections)),
        "hemisphere_occupancy": min(occupancies),
        "sij_min": min(pair_invariants),
    }
    jets = [row.copy() for row in event]
    merge_gaps = []
    pseudojet_norms = []
    while len(jets) >= 3:
        norms = [np.linalg.norm(jet[1:]) for jet in jets]
        pseudojet_norms.extend(norms)
        distances = []
        for first, second in itertools.combinations(range(len(jets)), 2):
            cosine = np.dot(jets[first][1:], jets[second][1:]) / (norms[first] * norms[second])
            distance = 2 * min(jets[first][0], jets[second][0]) ** 2 * (1 - np.clip(cosine, -1, 1)) / energy ** 2
            distances.append((distance, first, second))
        distances.sort()
        distance, first, second = distances[0]
        values[f"y{len(jets) - 1}{len(jets)}"] = distance
        merge_gaps.append(distances[1][0] - distance)
        jets[first] = jets[first] + jets[second]
        del jets[second]
    values["merge_gap"] = min(merge_gaps)
    values["pseudojet_norm"] = min(pseudojet_norms)
    return {name: float(value) for name, value in values.items()}


def physical_checks(event):
    residuals = {
        "energy_sum_error": abs(float(event[:, 0].sum()) - 1),
        "momentum_sum_error": float(np.linalg.norm(event[:, 1:].sum(axis=0))),
        "massless_error": float(np.max(abs(event[:, 0] - np.linalg.norm(event[:, 1:], axis=1)))),
    }
    assert max(residuals.values()) <= 1e-10, residuals
    assert event[:, 0].min() >= 0.03
    assert abs(event).max() <= 1 + 1e-10
    return residuals


def regularity_checks(values):
    thresholds = {
        "sij_min": 1e-4, "y45": 1e-4, "thrust_gap": 1e-7,
        "hemisphere_margin": 1e-6, "merge_gap": 1e-8,
        "pseudojet_norm": 1e-8, "hemisphere_occupancy": 2,
    }
    for name, threshold in thresholds.items():
        assert values[name] >= threshold, (name, values[name], threshold)


def rotation(quaternion):
    scalar, vector_x, vector_y, vector_z = np.array(quaternion, dtype=float) / np.linalg.norm(quaternion)
    cross_matrix = np.array([[0, -vector_z, vector_y], [vector_z, 0, -vector_x], [-vector_y, vector_x, 0]])
    result = np.eye(3) + 2 * scalar * cross_matrix + 2 * cross_matrix @ cross_matrix
    assert abs(np.linalg.det(result) - 1) < 1e-14
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path, nargs="?", default=Path(__file__).with_name("submission.json"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("validation.json"))
    args = parser.parse_args()
    assert args.submission.stat().st_size <= 16384
    data = json.loads(args.submission.read_text())
    assert isinstance(data, dict) and set(data) == {"events"}
    assert isinstance(data["events"], list) and len(data["events"]) == 2
    for event in data["events"]:
        assert isinstance(event, list) and len(event) == 5
        for row in event:
            assert isinstance(row, list) and len(row) == 4
            assert all(type(value) in (int, float) for value in row)
    events = np.array(data["events"], dtype=float)
    assert events.shape == (2, 5, 4) and np.isfinite(events).all()
    values = [independent_calculate(event) for event in events]
    diagnostics = []
    for event, reference in zip(events, values):
        physical = physical_checks(event)
        regularity_checks(reference)
        public = calculate(event)
        public_difference = max(abs(reference[name] - public[name]) for name in OBSERVABLES)
        assert public_difference <= 2e-10
        variants = [event[list(permutation)] for permutation in itertools.permutations(range(5))]
        for quaternion in ([1, 2, 3, 4], [3, -1, 4, 2], [2, 5, -3, 1]):
            rotated = event.copy()
            rotated[:, 1:] = event[:, 1:] @ rotation(quaternion).T
            variants.extend([rotated, rotated[[2, 0, 4, 1, 3]]])
        invariance_difference = 0.0
        for variant in variants:
            physical_checks(variant)
            transformed = independent_calculate(variant)
            regularity_checks(transformed)
            invariance_difference = max(invariance_difference, max(abs(reference[name] - transformed[name]) for name in OBSERVABLES))
        assert len(variants) == 126
        assert invariance_difference <= 2e-10
        diagnostics.append({**physical, "energy_min": float(event[:, 0].min()),
                            "public_calculator_difference": public_difference,
                            "invariance_checks": len(variants),
                            "invariance_max_difference": invariance_difference,
                            "observables": reference})
    differences = {name: abs(values[0][name] - values[1][name]) for name in SHAPES}
    ratio = max(value["y45"] for value in values) / min(value["y45"] for value in values)
    assert max(differences.values()) <= 1e-7, differences
    assert ratio >= 3, ratio
    report = {"passed": True, "shape_differences": differences, "y45_ratio": ratio,
              "submission_bytes": args.submission.stat().st_size, "events": diagnostics}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
