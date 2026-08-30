import argparse
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np

ASSETS = Path(__file__).resolve().parents[2] / "participant"
sys.path.insert(0, str(ASSETS / "workspace"))
from shapes import SHAPE_NAMES, calculate

OBSERVABLES = SHAPE_NAMES + ("y34", "y45")


def norm(vector):
    return math.sqrt(math.fsum(float(component) ** 2 for component in vector))


def dot(first, second):
    return math.fsum(float(left) * float(right) for left, right in zip(first, second))


def independent(event):
    energy = math.fsum(event[:, 0])
    candidates = []
    for count in (1, 2):
        for subset in itertools.combinations(range(5), count):
            vector = np.sum(event[list(subset), 1:], axis=0)
            candidates.append((2 * norm(vector) / energy, vector))
    candidates.sort(key=lambda candidate: candidate[0])
    thrust, direction = candidates[-1]
    axis = direction / norm(direction)
    projections = np.array([dot(row[1:], axis) for row in event])
    hemisphere_masses = []
    hemisphere_broadenings = []
    counts = []
    for sign in (1, -1):
        members = [row for row, projection in zip(event, projections) if sign * projection > 0]
        counts.append(len(members))
        total = np.sum(members, axis=0)
        hemisphere_masses.append((total[0] ** 2 - dot(total[1:], total[1:])) / energy ** 2)
        hemisphere_broadenings.append(math.fsum(norm(np.cross(row[1:], axis)) for row in members) / (2 * energy))
    tensor = sum(np.outer(row[1:], row[1:]) / row[0] for row in event) / energy
    eigenvalues = np.linalg.eigvalsh(tensor)
    c_parameter = 3 * sum(eigenvalues[left] * eigenvalues[right] for left, right in itertools.combinations(range(3), 2))
    result = {"tau": 1 - thrust, "C": c_parameter,
              "rho_H": max(hemisphere_masses),
              "B_T": sum(hemisphere_broadenings),
              "B_W": max(hemisphere_broadenings),
              "thrust_gap": thrust - candidates[-2][0],
              "hemisphere_margin": min(abs(projections)),
              "hemisphere_occupancy": min(counts)}
    jets = [row.copy() for row in event]
    gaps = []
    minimum_norm = float("inf")
    for count in (5, 4, 3):
        lengths = [norm(jet[1:]) for jet in jets]
        minimum_norm = min(minimum_norm, min(lengths))
        distances = []
        for left, right in itertools.combinations(range(count), 2):
            cosine = dot(jets[left][1:], jets[right][1:]) / (lengths[left] * lengths[right])
            distance = 2 * min(jets[left][0], jets[right][0]) ** 2 * max(0.0, min(2.0, 1 - cosine)) / energy ** 2
            distances.append((distance, left, right))
        distances.sort()
        distance, left, right = distances[0]
        result[f"y{count - 1}{count}"] = distance
        gaps.append(distances[1][0] - distance)
        merged = jets[left] + jets[right]
        jets = [jet for index, jet in enumerate(jets) if index not in (left, right)] + [merged]
    result["merge_gap"] = min(gaps)
    result["pseudojet_norm"] = minimum_norm
    return result


def physical(event):
    assert event.shape == (5, 4) and np.isfinite(event).all()
    assert abs(event).max() <= 1 + 1e-10
    energy_error = abs(math.fsum(event[:, 0]) - 1)
    cm_error = norm(np.sum(event[:, 1:], axis=0))
    mass_error = max(abs(row[0] - norm(row[1:])) for row in event)
    energy_min = min(event[:, 0])
    invariant_min = min(2 * (event[left, 0] * event[right, 0] - dot(event[left, 1:], event[right, 1:]))
                        for left, right in itertools.combinations(range(5), 2))
    assert energy_error <= 1e-10 and cm_error <= 1e-10 and mass_error <= 1e-10
    assert energy_min >= 0.03 and invariant_min >= 1e-4
    return {"energy_error": energy_error, "cm_error": cm_error,
            "massless_error": mass_error, "energy_min": energy_min,
            "sij_min": invariant_min}


def regular(values):
    limits = {"y45": 1e-4, "thrust_gap": 1e-7, "hemisphere_margin": 1e-6,
              "merge_gap": 1e-8, "pseudojet_norm": 1e-8, "hemisphere_occupancy": 2}
    for name, minimum in limits.items():
        assert values[name] >= minimum, (name, values[name], minimum)


def rotation(quaternion):
    quaternion = np.array(quaternion, dtype=float)
    quaternion /= norm(quaternion)
    scalar = quaternion[0]
    vector = quaternion[1:]
    horizontal, vertical, depth = vector
    skew = np.array([[0, -depth, vertical], [depth, 0, -horizontal], [-vertical, horizontal, 0]])
    matrix = (scalar ** 2 - dot(vector, vector)) * np.eye(3) + 2 * np.outer(vector, vector) + 2 * scalar * skew
    assert np.max(abs(matrix.T @ matrix - np.eye(3))) < 1e-14
    assert abs(np.linalg.det(matrix) - 1) < 1e-14
    return matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path, nargs="?", default=Path(__file__).with_name("submission.json"))
    parser.add_argument("--report", type=Path, default=Path(__file__).with_name("validation.json"))
    args = parser.parse_args()
    assert args.submission.stat().st_size <= 16384
    payload = json.loads(args.submission.read_text())
    assert set(payload) == {"events"} and len(payload["events"]) == 2
    for rows in payload["events"]:
        assert len(rows) == 5
        for row in rows:
            assert len(row) == 4 and all(type(value) in (float, int) for value in row)
    events = np.array(payload["events"], dtype=float)
    reports = []
    values = []
    for event in events:
        diagnostics = physical(event)
        reference = independent(event)
        regular(reference)
        public = calculate(event)
        agreement = max(abs(reference[name] - public[name]) for name in OBSERVABLES)
        assert agreement <= 2e-10
        invariance_error = 0.0
        checks = 0
        transforms = [event[list(permutation)] for permutation in itertools.permutations(range(5))]
        for quaternion in ([1, 2, 3, 4], [3, -1, 4, 2], [2, 5, -3, 1]):
            rotated = event.copy()
            rotated[:, 1:] = event[:, 1:] @ rotation(quaternion).T
            transforms.extend([rotated, rotated[[2, 0, 4, 1, 3]]])
        for transformed in transforms:
            physical(transformed)
            observed = independent(transformed)
            regular(observed)
            invariance_error = max(invariance_error, max(abs(observed[name] - reference[name]) for name in OBSERVABLES))
            checks += 1
        assert checks == 126 and invariance_error <= 2e-10
        values.append(reference)
        reports.append({**diagnostics, "observables": reference,
                        "public_agreement_error": agreement,
                        "invariance_checks": checks, "invariance_error": invariance_error})
    mismatch = {name: abs(values[0][name] - values[1][name]) for name in SHAPE_NAMES}
    ratio = max(value["y45"] for value in values) / min(value["y45"] for value in values)
    assert max(mismatch.values()) <= 1e-7
    assert ratio >= 3
    report = {"passed": True, "shape_errors": mismatch, "y45_ratio": ratio, "events": reports}
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
