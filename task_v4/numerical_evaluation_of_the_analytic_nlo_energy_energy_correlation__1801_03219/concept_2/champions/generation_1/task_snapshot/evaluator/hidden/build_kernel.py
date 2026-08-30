"""Reproducible high-precision source calibration; not run by submissions."""

import hashlib
import json
import subprocess
import time
from pathlib import Path

import mpmath as mp

from native_kernel import _components


ROOT = Path(__file__).resolve().parents[2]
EDGES = [".02", ".04", ".08", ".16", ".32", ".50", ".70", ".85", ".93", ".98"]
LEVELS = [(40, 60), (64, 85), (88, 110)]


def write_json(relative, data):
    destination = ROOT / relative
    text = json.dumps(data, indent=2) + "\n"
    if destination.exists():
        patch = "*** Begin Patch\n*** Delete File: " + str(destination) + "\n*** End Patch\n"
        subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, stdout=subprocess.DEVNULL)


def clenshaw(coefficients, coordinate):
    previous = mp.mpf(0)
    current = mp.mpf(0)
    for coefficient in reversed(coefficients[1:]):
        previous, current = current, coefficient + 2 * coordinate * current - previous
    return coefficients[0] + coordinate * current - previous


def make_level(degree, precision):
    panels = []
    residual = mp.mpf(0)
    with mp.workdps(precision):
        for panel_index, (left_text, right_text) in enumerate(zip(EDGES[:-1], EDGES[1:])):
            left, right = mp.mpf(left_text), mp.mpf(right_text)
            count = degree + 1
            angles = [mp.pi * (node + mp.mpf(".5")) / count for node in range(count)]
            values = []
            for angle in angles:
                coordinate = mp.cos(angle)
                position = (left + right) / 2 + (right - left) / 2 * coordinate
                values.append([4 * position * (1 - position) * component for component in _components(position)])
            channels = []
            for channel in range(3):
                coefficients = [2 * mp.fsum(values[node][channel] * mp.cos(order * angles[node]) for node in range(count)) / count for order in range(count)]
                coefficients[0] /= 2
                channels.append(coefficients)
            for check in range(17):
                coordinate = -1 + mp.mpf(2) * (check + mp.mpf(".2718281828459045235")) / 17
                position = (left + right) / 2 + (right - left) / 2 * coordinate
                exact = [4 * position * (1 - position) * component for component in _components(position)]
                for channel in range(3):
                    residual = max(residual, abs(exact[channel] - clenshaw(channels[channel], coordinate)))
            panels.append([[mp.nstr(value, precision - 5) for value in channel] for channel in channels])
            print(json.dumps({"degree": degree, "precision": precision, "panel": panel_index, "off_grid_max": str(residual)}), flush=True)
    return {"edges": EDGES, "degree": degree, "dps": precision,
            "coefficients": panels, "source_off_grid_max": str(residual)}


def main():
    started = time.monotonic()
    levels = [make_level(degree, precision) for degree, precision in LEVELS]
    with mp.workdps(110):
        differences = []
        tails = []
        for coarse, fine in zip(levels[:-1], levels[1:]):
            difference = mp.mpf(0)
            for coarse_panel, fine_panel in zip(coarse["coefficients"], fine["coefficients"]):
                for coarse_channel, fine_channel in zip(coarse_panel, fine_panel):
                    padded = coarse_channel + ["0"] * (len(fine_channel) - len(coarse_channel))
                    difference = max(difference, mp.fsum(abs(mp.mpf(first) - mp.mpf(second)) for first, second in zip(padded, fine_channel)))
            differences.append(str(difference))
        for level in levels:
            tails.append(str(max(mp.fsum(abs(mp.mpf(value)) for value in channel[-8:]) for panel in level["coefficients"] for channel in panel)))
        if mp.mpf(differences[0]) > mp.mpf("1e-16") or mp.mpf(differences[1]) > mp.mpf("1e-26"):
            raise RuntimeError("source expansion did not converge sufficiently")
        public = {"edges": EDGES, "degree": levels[1]["degree"],
                  "quantity": "4*z*(1-z) times each uncolored B component",
                  "coefficients": [[[float(value) for value in channel] for channel in panel] for panel in levels[1]["coefficients"]]}
        write_json("participant/input/kernel.json", public)
        for level in levels:
            write_json("evaluator/hidden/kernel_" + str(level["degree"]) + ".json", level)
        audit = {"levels": LEVELS, "uniform_polynomial_difference_bounds": differences,
                 "last_eight_coefficient_l1": tails,
                 "off_grid_source_max": [level["source_off_grid_max"] for level in levels],
                 "off_grid_checks_per_level": 17 * (len(EDGES) - 1),
                 "native_sha256": hashlib.sha256((ROOT / "evaluator/hidden/native_kernel.py").read_bytes()).hexdigest(),
                 "seconds": time.monotonic() - started,
                 "interpretation": "Uniform bounds compare polynomials, not the exact EEC. Source residuals and degree/precision refinement are convergence evidence, not rigorous interval enclosures."}
        write_json("evaluator/hidden/calibration_audit.json", audit)


if __name__ == "__main__":
    main()
