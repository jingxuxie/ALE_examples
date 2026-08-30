import json
from pathlib import Path

import numpy as np
from numpy.polynomial import chebyshev, legendre
from local_bins import bin_average_local


QUADRATURE_NODES, QUADRATURE_WEIGHTS = legendre.leggauss(40)


def load_model(path, enforce_budget=True):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 200000:
        raise ValueError("model must be a regular JSON file below 200000 bytes")
    artifact = json.loads(path.read_text())
    if not isinstance(artifact["knots"],list) or any(type(value) not in (int,float) for value in artifact["knots"]):
        raise ValueError("knots must be real JSON numbers")
    knots = np.asarray(artifact["knots"], dtype=float)
    if knots.ndim != 1 or not 2 <= len(knots) <= 21:
        raise ValueError("need 1 through 20 intervals")
    if not np.isfinite(knots).all() or knots[0] != -24 or knots[-1] != 24:
        raise ValueError("knots must span [-24,24]")
    if np.any(np.diff(knots) <= 0):
        raise ValueError("knots must increase strictly")
    coefficients = artifact["coefficients"]
    if len(coefficients) != len(knots) - 1:
        raise ValueError("one coefficient block per interval required")
    parsed = []
    scalar_count = len(knots)
    for block in coefficients:
        if len(block) != 3:
            raise ValueError("three channels required")
        channels = []
        for values in block:
            if not isinstance(values,list) or any(type(value) not in (int,float) for value in values):
                raise ValueError("coefficients must be real JSON numbers")
            values = np.asarray(values, dtype=float)
            if values.ndim != 1 or not 1 <= len(values) <= 65 or not np.isfinite(values).all():
                raise ValueError("finite coefficient list of degree at most 64 required")
            scalar_count += len(values)
            channels.append(values)
        parsed.append(channels)
    if enforce_budget and scalar_count > 320:
        raise ValueError(f"deployment uses {scalar_count} scalars, maximum 320")
    return {"knots": knots, "coefficients": parsed, "scalar_count": scalar_count}


def evaluate(model, coordinates, derivative=False):
    coordinates = np.asarray(coordinates, dtype=float)
    flat = coordinates.reshape(-1)
    knots = model["knots"]
    intervals = np.clip(np.searchsorted(knots, flat, side="right") - 1, 0, len(knots)-2)
    result = np.empty((len(flat), 3))
    for interval, channels in enumerate(model["coefficients"]):
        selected = intervals == interval
        if not np.any(selected):
            continue
        left, right = knots[interval:interval+2]
        transformed = (2 * flat[selected] - left - right) / (right - left)
        for channel, values in enumerate(channels):
            if derivative:
                values = chebyshev.chebder(values) * (2 / (right-left))
            result[selected, channel] = chebyshev.chebval(transformed, values)
    return result.reshape(coordinates.shape + (3,))


def bin_average(model, lower, upper):
    return bin_average_local(model,lower,upper)
