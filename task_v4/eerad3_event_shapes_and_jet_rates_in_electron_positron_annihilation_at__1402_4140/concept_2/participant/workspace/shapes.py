"""Reusable NumPy observables for five massless CM partons; no search required."""

import itertools

import numpy as np


SHAPE_NAMES = ("tau", "C", "rho_H", "B_T", "B_W", "y23")
SIGNS = np.array([(1,) + tail for tail in itertools.product((-1, 1), repeat=4)])
PAIRS = {count: np.triu_indices(count, 1) for count in (3, 4, 5)}


def from_coordinates(coordinates):
    """Map 12 real coordinates to exactly momentum-balanced, Q=1 partons."""
    first = np.asarray(coordinates, dtype=float).reshape(4, 3)
    spatial = np.vstack((first, -first.sum(axis=0)))
    energies = np.linalg.norm(spatial, axis=1)
    if energies.min() <= 0 or not np.isfinite(energies.sum()):
        raise ValueError("zero or nonfinite momentum")
    return np.column_stack((energies, spatial)) / energies.sum()


def random_event(rng):
    """A simple CM sampler, not a claim of uniform Lorentz-invariant sampling."""
    return from_coordinates(rng.normal(size=(4, 3)))


def invariants(event):
    event = np.asarray(event, dtype=float)
    left, right = PAIRS[5]
    return 2 * (event[left, 0] * event[right, 0]
                - np.einsum("ij,ij->i", event[left, 1:], event[right, 1:]))


def durham(event):
    """Raw E-scheme transition distances, never a running maximum."""
    jets = np.array(event, dtype=float, copy=True)
    total_energy = jets[:, 0].sum()
    scales = {}
    gaps = []
    norm_min = float("inf")
    for count in (5, 4, 3):
        norms = np.linalg.norm(jets[:, 1:], axis=1)
        norm_min = min(norm_min, float(norms.min()))
        if norms.min() <= 0:
            raise ValueError("zero spatial pseudojet")
        directions = jets[:, 1:] / norms[:, None]
        left, right = PAIRS[count]
        cosines = np.einsum("ij,ij->i", directions[left], directions[right])
        distances = (2 * np.minimum(jets[left, 0], jets[right, 0]) ** 2
                     * np.clip(1 - cosines, 0, 2) / total_energy ** 2)
        order = np.argsort(distances, kind="stable")
        selected = order[0]
        scales[f"y{count - 1}{count}"] = float(distances[selected])
        gaps.append(float(distances[order[1]] - distances[selected]))
        keep, remove = left[selected], right[selected]
        jets[keep] += jets[remove]
        jets = np.delete(jets, remove, axis=0)
    return scales, min(gaps), norm_min


def calculate(event):
    """Return six shapes, y45/y34 and numerical-regularity diagnostics."""
    event = np.asarray(event, dtype=float)
    if event.shape != (5, 4) or not np.isfinite(event).all():
        raise ValueError("expected finite (5,4) [E,px,py,pz] array")
    energies = event[:, 0]
    if energies.min() <= 0:
        raise ValueError("energies must be positive")
    spatial = event[:, 1:]
    total_energy = energies.sum()
    signed = SIGNS @ spatial
    norms = np.linalg.norm(signed, axis=1)
    order = np.argsort(norms)
    axis = signed[order[-1]] / norms[order[-1]]
    projections = spatial @ axis
    transverse = np.linalg.norm(np.cross(spatial, axis), axis=1)
    masses = []
    broadenings = []
    for mask in (projections > 0, projections <= 0):
        hemisphere = event[mask].sum(axis=0)
        masses.append((hemisphere[0] ** 2 - hemisphere[1:] @ hemisphere[1:])
                      / total_energy ** 2)
        broadenings.append(transverse[mask].sum() / (2 * total_energy))
    tensor = (spatial.T / energies) @ spatial / total_energy
    c_parameter = 1.5 * (np.trace(tensor) ** 2 - np.trace(tensor @ tensor))
    scales, merge_gap, pseudojet_norm = durham(event)
    return {
        "tau": float(1 - norms[order[-1]] / total_energy),
        "C": float(c_parameter),
        "rho_H": float(max(masses)),
        "B_T": float(sum(broadenings)),
        "B_W": float(max(broadenings)),
        **scales,
        "thrust_gap": float((norms[order[-1]] - norms[order[-2]]) / total_energy),
        "hemisphere_margin": float(np.abs(projections).min()),
        "hemisphere_occupancy": int(min(np.count_nonzero(projections > 0), np.count_nonzero(projections <= 0))),
        "merge_gap": merge_gap,
        "pseudojet_norm": pseudojet_norm,
    }


def shape_vector(event):
    result = calculate(event)
    return np.array([result[name] for name in SHAPE_NAMES])
