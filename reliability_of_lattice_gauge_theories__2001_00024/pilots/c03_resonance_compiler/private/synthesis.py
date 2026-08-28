import math

import numpy as np

from scoring import evaluate_controls


U1_COMPLIANT_SIX = np.asarray([-115, 116, -118, 122, -130, 146], dtype=float) / 146
Z2_LOCAL_TWO = np.asarray([1, -1 / 11], dtype=float)


def quantize(case, values):
    hardware = case["hardware"]
    return np.clip(np.rint(np.asarray(values) * hardware["denominator"]),
                   -np.asarray(hardware["caps"]), hardware["caps"]).astype(int)


def weak_controls(case):
    length = case["length"]
    pattern = np.asarray([1, -1]) if case["model"] == "u1" else Z2_LOCAL_TWO
    ticks = quantize(case, np.resize(pattern, length)).tolist()
    return {"analog": {"ticks": ticks},
            "digital": {"ticks": ticks, "phase_tick": case["hardware"]["phase_ticks"][-1]}}


def synthesize(case, matrix, seed, restarts=7):
    randomizer = np.random.default_rng(seed)
    hardware, length = case["hardware"], case["length"]
    denominator = hardware["denominator"]
    uncertainty = np.abs(matrix) @ np.asarray(hardware["uncertainty"])
    adjacency = [np.flatnonzero(matrix[:, site]) for site in range(length)]
    alphabets = [np.arange(-cap, cap + 1) for cap in hardware["caps"]]
    base = weak_controls(case)
    pattern = U1_COMPLIANT_SIX if case["model"] == "u1" else Z2_LOCAL_TWO
    seeds = [np.asarray(base["analog"]["ticks"]), quantize(case, np.resize(pattern, length))]
    for restart in range(restarts - 2):
        if restart % 2:
            values = randomizer.uniform(-1, 1, length)
        else:
            period = (4, 6, 8)[restart % 3]
            values = np.resize(randomizer.uniform(-1, 1, period), length)
        seeds.append(quantize(case, values))
    solution = {}
    for digital in (False, True):
        name = "digital" if digital else "analog"
        best_schedule = base[name]
        best_quality = evaluate_controls(case, matrix, best_schedule, digital)["quality"]

        def margins(detunings, errors, phase_tick):
            if not digital:
                return np.maximum(0, np.abs(detunings) - errors) / hardware["bandwidth"]
            phase = math.pi * phase_tick / hardware["phase_denominator"]
            distances = np.abs((phase * detunings + math.pi) % (2 * math.pi) - math.pi)
            return np.maximum(0, distances - phase * errors) / math.pi

        for restart, initial in enumerate(seeds):
            ticks = initial.copy()
            detuning = matrix @ (ticks / denominator)
            phase_tick = hardware["phase_ticks"][restart % len(hardware["phase_ticks"])]
            for temperature in (0.15, 0.06, 0.02, 0.006):
                for sweep in range(3):
                    if digital:
                        candidates = np.array([margins(detuning, uncertainty, phase)
                                               for phase in hardware["phase_ticks"]])
                        losses = np.exp(-candidates / temperature).mean(axis=1)
                        phase_tick = hardware["phase_ticks"][int(np.argmin(losses))]
                    for site in randomizer.permutation(length):
                        rows = adjacency[site]
                        if not len(rows):
                            continue
                        alphabet = alphabets[site]
                        alternatives = (detuning[rows][None, :] + matrix[rows, site][None, :]
                                        * (alphabet[:, None] - ticks[site]) / denominator)
                        candidate_margins = margins(alternatives, uncertainty[rows][None, :], phase_tick)
                        shift = float(margins(detuning[rows], uncertainty[rows], phase_tick).min())
                        losses = np.exp(np.clip((shift - candidate_margins) / temperature, -700, 700)).sum(axis=1)
                        lowest = losses.min()
                        finalists = np.flatnonzero(losses <= lowest + 1e-12)
                        chosen = finalists[int(np.argmax(candidate_margins[finalists].mean(axis=1)))]
                        detuning[rows] = alternatives[chosen]
                        ticks[site] = alphabet[chosen]
                    schedule = {"ticks": ticks.tolist()}
                    if digital:
                        schedule["phase_tick"] = int(phase_tick)
                    quality = evaluate_controls(case, matrix, schedule, digital)["quality"]
                    if quality > best_quality:
                        best_quality, best_schedule = quality, schedule
        solution[name] = best_schedule
    return solution
