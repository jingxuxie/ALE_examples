"""Author-only baseline, never part of a fresh participant attempt."""

import numpy as np


def solve(case):
    fits = {}
    for track in case["tracks"]:
        time = np.asarray(track["time_ms"])
        signal = np.asarray(track["signal"])
        period = track["calibration"]["period_ms"]
        basis = (1 - np.cos(2 * np.pi * time / period)) / 2
        design = np.column_stack([np.ones(len(time)), basis])
        offset, amplitude = np.linalg.lstsq(design, signal, rcond=None)[0]
        error = np.mean(track["sigma"]) / np.sqrt(np.sum((basis - basis.mean()) ** 2))
        query = np.asarray(track["query_time_ms"])
        fits[track["id"]] = {
            "offset": float(offset), "amplitude": float(amplitude),
            "amplitude_se": float(error),
            "prediction": (offset + amplitude * (1 - np.cos(2 * np.pi * query / period)) / 2).tolist(),
        }
    density = {row["id"]: row for row in case["occupation"]["observations"] if "center" in row}
    matter = float(np.clip(density["matter_mean"]["center"], 0, 1))
    doublon = float(np.clip(density["link_doublon"]["center"], 0, 1))
    distribution = []
    for left, middle, right in case["occupation"]["states"]:
        left_probability = {0: 1 - doublon, 2: doublon}.get(left, 0)
        middle_probability = {0: 1 - matter, 1: matter}.get(middle, 0)
        right_probability = {0: 1 - doublon, 2: doublon}.get(right, 0)
        distribution.append(left_probability * middle_probability * right_probability)
    distribution = np.asarray(distribution)
    distribution /= distribution.sum()
    bounds, witnesses = {}, {}
    for target in case["occupation"]["targets"]:
        value = float(distribution @ target["coefficients"])
        bounds[target["id"]] = [value, value]
        witnesses[target["id"]] = {"lower": distribution.tolist(), "upper": distribution.tolist()}
    return {"fits": fits, "inflation": 0.0, "bounds": bounds, "witnesses": witnesses}
