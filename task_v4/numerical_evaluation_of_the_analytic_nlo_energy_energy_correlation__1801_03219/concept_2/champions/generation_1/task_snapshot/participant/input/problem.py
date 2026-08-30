"""Public, finite witness domain and stable EEC kernel."""

import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.chebyshev import chebval


BINS = {"collinear": (.02, .32), "central": (.08, .92), "backward": (.60, .98)}
FAMILIES = ("leading", "subleading", "fermion")
QUANTUM = 10**10
MODES = 12
COLOR = np.array([16 / 9, 4 / 9, 10 / 3])
ROOT = Path(__file__).resolve().parent


def validate(witness):
    if not isinstance(witness, dict) or set(witness) != {"version", "bin", "band_start", "tilt", "curvature", "cosine", "sine"}:
        raise ValueError("expected exactly version, bin, band_start, tilt, curvature, cosine, sine")
    for name, lower, upper in (("version", 1, 1), ("band_start", 1, 53), ("tilt", -4, 4), ("curvature", -4, 4)):
        if type(witness[name]) is not int or not lower <= witness[name] <= upper:
            raise ValueError("invalid integer " + name)
    if not isinstance(witness["bin"], str) or witness["bin"] not in BINS:
        raise ValueError("unknown bin")
    for name in ("cosine", "sine"):
        if not isinstance(witness[name], list) or len(witness[name]) != MODES:
            raise ValueError("each coefficient list must contain 12 integers")
        if any(type(value) is not int or abs(value) > QUANTUM for value in witness[name]):
            raise ValueError("coefficient is not an admissible lattice integer")
    coefficients = witness["cosine"] + witness["sine"]
    if sum(abs(value) for value in coefficients) > QUANTUM:
        raise ValueError("coefficient l1 norm exceeds one")
    if sum(value * value for value in coefficients) < QUANTUM**2 // 50:
        raise ValueError("Fourier RMS is below 0.1")
    return witness


def response(points, witness):
    coordinate = 2 * np.asarray(points) - 1
    return (1 + witness["tilt"] / 16 * coordinate
            + witness["curvature"] / 16 * (coordinate**2 - 1 / 3)) / 1.5


def basis(points, witness):
    frequencies = np.arange(witness["band_start"], witness["band_start"] + MODES)
    angles = 2 * np.pi * np.asarray(points)[..., None] * frequencies
    return np.concatenate((np.cos(angles), np.sin(angles)), axis=-1)


def weight(points, witness):
    coefficients = np.array(witness["cosine"] + witness["sine"], dtype=float) / QUANTUM
    return response(points, witness) * (basis(points, witness) @ coefficients)


class Kernel:
    def __init__(self, path=None):
        with open(path or ROOT / "kernel.json", encoding="utf-8") as stream:
            data = json.load(stream)
        self.edges = np.array(data["edges"], dtype=float)
        self.coefficients = np.array(data["coefficients"], dtype=float)

    def __call__(self, points):
        points = np.asarray(points, dtype=float)
        if np.any(points < self.edges[0]) or np.any(points > self.edges[-1]):
            raise ValueError("kernel evaluation outside calibrated finite domain")
        indices = np.clip(np.searchsorted(self.edges, points, side="right") - 1, 0, len(self.edges) - 2)
        result = np.empty(points.shape + (3,))
        for index in np.unique(indices):
            mask = indices == index
            coordinate = (2 * points[mask] - self.edges[index] - self.edges[index + 1]) / (self.edges[index + 1] - self.edges[index])
            result[mask] = chebval(coordinate, self.coefficients[index].T).T
        return result

    def integrand(self, witness, family):
        left, right = BINS[witness["bin"]]
        channel = FAMILIES.index(family)

        def function(points):
            return 2 * (right - left) * COLOR[channel] * self(left + (right - left) * points)[..., channel] * weight(points, witness)

        return function


def load_witness(path):
    path = Path(path)
    if path.is_dir():
        path = path / "witness.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise ValueError("witness.json must be a regular, non-symlink file of at most 16 KiB")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    with path.open(encoding="utf-8") as stream:
        return validate(json.load(stream, object_pairs_hook=unique_pairs))
