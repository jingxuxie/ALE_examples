"""Public waveform constraints and deterministic robustness families."""

import json
import itertools
from pathlib import Path

import numpy as np


def load_spec():
    return json.loads((Path(__file__).resolve().parents[1] / "input" / "target.json").read_text())


def drift_vectors(spec):
    result = [("zero", np.zeros(spec["knot_count"]))]
    for index, signs in enumerate(itertools.product((-1.0, 1.0), repeat=spec["knot_count"])):
        result.append((f"corner_{index:02d}", spec["knot_drift"] * np.asarray(signs)))
    return result


def waveforms(witness, spec, include_corners=True):
    if not isinstance(witness, dict) or set(witness) != {"schema_version", "depth", "knots", "observable"}:
        raise ValueError("expected exactly schema_version, depth, knots, observable")
    if type(witness["schema_version"]) is not int or witness["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    depth = witness["depth"]
    if type(depth) is not int or not spec["depth_min"] <= depth <= spec["depth_max"]:
        raise ValueError("depth must be an integer within the public bounds")
    if witness["observable"] != spec["observable"]:
        raise ValueError("unsupported observable")
    knots = witness["knots"]
    if not isinstance(knots, list) or len(knots) != spec["knot_count"]:
        raise ValueError("wrong number of control knots")
    if any(type(value) not in (int, float) or not np.isfinite(value) for value in knots):
        raise ValueError("knots must be finite real JSON numbers, not booleans")
    knots = np.asarray(knots, dtype=float)
    if np.min(knots) < spec["knot_min"] or np.max(knots) > spec["knot_max"]:
        raise ValueError("control knots outside the public bounds")
    grid = np.linspace(0, 1, depth)
    epsilon = spec["perturbation"]
    families = {}
    for label, drift in drift_vectors(spec) if include_corners else [("zero", np.zeros(len(knots)))]:
        nominal = np.interp(grid, np.linspace(0, 1, len(knots)), knots + drift)
        original = {"nominal": nominal, "offset_minus": nominal - epsilon,
                    "offset_plus": nominal + epsilon,
                    "tilt_minus": nominal - epsilon * (2 * grid - 1),
                    "tilt_plus": nominal + epsilon * (2 * grid - 1)}
        for family, angles in original.items():
            name = family if label == "zero" else label + "/" + family
            families[name] = angles
    for angles in families.values():
        if np.min(angles) <= 0.1 or np.max(angles) >= 1.47:
            raise ValueError("every physical pulse must lie strictly between 0.1 and 1.47")
        if np.max(np.abs(np.diff(angles))) > spec["max_slew"] + 1e-12:
            raise ValueError("pulse-to-pulse slew exceeds the public bound")
    return families


def metrics(exact, estimates, spec):
    spread = max(abs(estimates[index + 1] - estimates[index]) for index in range(len(estimates) - 1))
    error = abs(estimates[-1] - exact)
    margin = min(error / spec["error_min"], spec["spread_max"] / max(spread, 1e-15))
    return {"exact": float(exact), "estimates": [float(value) for value in estimates],
            "spread": float(spread), "error": float(error), "margin": float(margin),
            "score": float(100 * min(1, margin)),
            "heuristic_converged": bool(spread <= spec["spread_max"]),
            "overconfidence": float(error / max(spread, spec["confidence_floor"])),
            "passed": bool(error >= spec["error_min"] and spread <= spec["spread_max"])}
