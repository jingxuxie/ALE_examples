"""Exact local sector compiler and quantized protection schedule optimizer."""

import ctypes
import json
import os
import time
from collections import defaultdict

import numpy as np


MATTER = {
    "I": ((1, 0), (0, 1)),
    "raise": ((0, 0), (1, 0)),
    "lower": ((0, 1), (0, 0)),
    "n": ((0, 0), (0, 1)),
    "x": ((0, 1), (1, 0)),
    "y": ((0, 1j), (-1j, 0)),
    "z": ((-1, 0), (0, 1)),
}
ELECTRIC = {
    "I": MATTER["I"],
    "x": ((-1, 0), (0, 1)),
    "z": ((0, 1), (1, 0)),
    "y": ((0, -1j), (1j, 0)),
    "raise": ((-0.5, 0.5), (-0.5, 0.5)),
    "lower": ((-0.5, -0.5), (0.5, 0.5)),
}


def _paths(channel, model, length):
    groups = defaultdict(list)
    for term in channel["terms"]:
        amplitude = complex(*term["amplitude"])
        branches = [((), (), amplitude)]
        for kind, offset, name in term["ops"]:
            site = offset % length
            matrix = ELECTRIC[name] if model == "z2" and kind == "l" else MATTER[name]
            choices = []
            for flip in (0, 1):
                values = (matrix[flip][0], matrix[1 ^ flip][1])
                if values != (0, 0):
                    choices.append((flip, values))
            updated = []
            for flips, factors, coefficient in branches:
                for flip, values in choices:
                    new_flips = flips + ((kind, site),) if flip else flips
                    new_factors = factors if values == (1, 1) else factors + ((kind, site, values),)
                    updated.append((new_flips, new_factors, coefficient))
            branches = updated
        for flips, factors, coefficient in branches:
            if flips and coefficient:
                groups[tuple(sorted(flips))].append((coefficient, factors))
    return groups


def _local_transfers(groups, model, length, target):
    result = set()
    for flips, terms in groups.items():
        flipped_matter = {site for kind, site in flips if kind == "m"}
        flipped_links = {site for kind, site in flips if kind == "l"}
        affected = flipped_matter | flipped_links | {(site + 1) % length for site in flipped_links}
        matter_sites = set(affected)
        link_sites = set(flipped_links)
        for coefficient, factors in terms:
            for kind, site, values in factors:
                (matter_sites if kind == "m" else link_sites).add(site)
        for site in matter_sites:
            link_sites.update(((site - 1) % length, site))
        link_sites = sorted(link_sites)
        positions = {site: index for index, site in enumerate(link_sites)}
        count = 1 << len(link_sites)
        for start in range(0, count, 65536):
            states = np.arange(start, min(start + 65536, count), dtype=np.uint64)
            bits = {site: ((states >> index) & 1).astype(np.int8) for site, index in positions.items()}
            valid = np.ones(len(states), dtype=bool)
            if model == "u1":
                for site in link_sites:
                    following = (site + 1) % length
                    if following in bits:
                        valid &= (bits[site] + bits[following] < 2)
            if not np.any(valid):
                continue
            bits = {site: values[valid] for site, values in bits.items()}
            matter = {}
            for site in matter_sites:
                left, right = bits[(site - 1) % length], bits[site]
                if model == "u1":
                    matter[site] = 1 - left - right
                else:
                    matter[site] = (1 - target[site] * (2 * left - 1) * (2 * right - 1)) // 2
            amplitudes = np.zeros(np.count_nonzero(valid), dtype=np.complex128)
            for coefficient, factors in terms:
                values = np.full(len(amplitudes), coefficient, dtype=np.complex128)
                for kind, site, entries in factors:
                    inputs = matter[site] if kind == "m" else bits[site]
                    values *= entries[0] + (entries[1] - entries[0]) * inputs
                amplitudes += values
            reachable = np.abs(amplitudes) > 1e-12
            if not np.any(reachable):
                continue
            sites = sorted(affected)
            sectors, penalties = [], []
            for site in sites:
                occupation = matter[site][reachable]
                left = bits[(site - 1) % length][reachable]
                right = bits[site][reachable]
                output_n = 1 - occupation if site in flipped_matter else occupation
                output_left = 1 - left if (site - 1) % length in flipped_links else left
                output_right = 1 - right if site in flipped_links else right
                if model == "u1":
                    sector = (1 if site % 2 == 0 else -1) * (output_n + output_left + output_right - 1)
                    penalty = sector
                else:
                    product = (2 * output_left - 1) * (2 * output_right - 1)
                    sector = (1 - 2 * output_n) * product - target[site]
                    penalty = product + 2 * target[site] * output_n - target[site]
                sectors.append(sector)
                penalties.append(penalty)
            rows = np.unique(np.stack(sectors + penalties, axis=1), axis=0)
            for row in rows:
                sector = tuple((site, int(value)) for site, value in zip(sites, row[:len(sites)]) if value)
                if sector:
                    penalty = tuple((site, int(value)) for site, value in zip(sites, row[len(sites):]) if value)
                    result.add((sector, penalty))
    return sorted(result)


def compile_certificate(case):
    length, model = case["length"], case["model"]
    certificate, penalty_rows = [], set()
    for channel in case["channels"]:
        groups = _paths(channel, model, length)
        relevant = set()
        for flips, terms in groups.items():
            for kind, site in flips:
                relevant.add(site)
                if kind == "l":
                    relevant.add((site + 1) % length)
            for coefficient, factors in terms:
                relevant.update(site for kind, site, values in factors if kind == "m")
        relevant = sorted(relevant)
        cache = {}
        for anchor in channel["anchors"]:
            signature = tuple(case["target"][(anchor + site) % length] for site in relevant) if model == "z2" else ()
            if signature not in cache:
                target = dict(zip(relevant, signature))
                cache[signature] = _local_transfers(groups, model, length, target)
            transfers = []
            sign = -1 if model == "u1" and anchor % 2 else 1
            for sector, penalty in cache[signature]:
                sector = sorted(((site + anchor) % length, sign * value) for site, value in sector)
                penalty = sorted(((site + anchor) % length, sign * value) for site, value in penalty)
                transfers.append({"sector": [[site, value] for site, value in sector],
                                  "penalty": [[site, value] for site, value in penalty]})
                canonical_sign = -1 if penalty and penalty[0][1] < 0 else 1
                penalty_rows.add(tuple((site, canonical_sign * value) for site, value in penalty))
            certificate.append({"channel": channel["id"], "anchor": anchor, "transfers": transfers})
    rows = np.zeros((len(penalty_rows), length), dtype=np.int32)
    for index, row in enumerate(sorted(penalty_rows)):
        for site, value in row:
            rows[index, site] = value
    return certificate, rows


def margins(rows, ticks, hardware, phase_tick=None):
    gaps = np.sum(rows * np.asarray(ticks, dtype=float), axis=1) / hardware["denominator"]
    errors = np.sum(np.abs(rows) * np.asarray(hardware["uncertainty"]), axis=1)
    if phase_tick is None:
        return np.maximum(0, np.abs(gaps) - errors) / hardware["bandwidth"]
    phase = phase_tick / hardware["phase_denominator"]
    return np.maximum(0, np.abs((phase * gaps + 1) % 2 - 1) - abs(phase) * errors)


def _quality(values):
    return 0.75 * np.min(values) + 0.25 * np.mean(values) if len(values) else 1.0


def _fallback(rows, hardware, budget):
    rng = np.random.default_rng(7243)
    caps = np.asarray(hardware["caps"], dtype=np.int32)
    length = len(caps)
    phases = [None] + hardware["phase_ticks"]
    end = time.monotonic() + budget
    errors = np.sum(np.abs(rows) * np.asarray(hardware["uncertainty"]), axis=1)
    affected = [np.flatnonzero(rows[:, site]) for site in range(length)]
    domains = [np.arange(-cap, cap + 1, dtype=np.int32) for cap in caps]
    base_ticks = caps * (np.arange(length) % 2 == 0)
    best = [(_quality(margins(rows, base_ticks, hardware, phase)), base_ticks.copy(), phase) for phase in phases]

    def row_margins(gaps, indices, phase):
        values = gaps / hardware["denominator"]
        correction = errors[indices]
        if values.ndim == 2:
            correction = correction[:, None]
        if phase is None:
            return np.maximum(0, np.abs(values) - correction) / hardware["bandwidth"]
        scale = phase / hardware["phase_denominator"]
        return np.maximum(0, np.abs((scale * values + 1) % 2 - 1) - abs(scale) * correction)

    iteration = 0
    while time.monotonic() < end:
        if iteration < len(phases):
            phase_index = iteration
        elif rng.random() < 0.4:
            phase_index = 0
        elif time.monotonic() > end - budget / 2:
            leaders = sorted(range(1, len(phases)), key=lambda index: best[index][0], reverse=True)[:3]
            phase_index = int(rng.choice(leaders))
        else:
            phase_index = int(rng.integers(1, len(phases)))
        phase = phases[phase_index]
        if iteration < len(phases):
            ticks = base_ticks.copy()
        else:
            ticks = best[phase_index][1].copy()
            selected = rng.choice(length, max(1, length // 6), replace=False)
            ticks[selected] = rng.integers(-caps[selected], caps[selected] + 1, dtype=np.int32)
        best_values = row_margins(rows @ best[phase_index][1], slice(None), phase)
        step = 1 / (hardware["denominator"] * hardware["bandwidth"]) if phase is None else 0.04
        threshold = max(0, best_values.min() + step * rng.uniform(-0.3, 1.5))
        gaps = rows @ ticks
        values = row_margins(gaps, slice(None), phase)
        for sweep in range(5):
            changed = False
            for site in rng.permutation(length):
                if time.monotonic() >= end:
                    break
                indices = affected[site]
                if not len(indices):
                    continue
                candidates = domains[site]
                candidate_gaps = gaps[indices, None] + rows[indices, site, None] * (candidates - ticks[site])
                candidate_values = row_margins(candidate_gaps, indices, phase)
                scores = 0.25 / len(rows) * candidate_values.sum(axis=0) - 0.75 * np.maximum(0, threshold - candidate_values).sum(axis=0)
                choice = int(np.argmax(scores))
                old_choice = int(ticks[site] + caps[site])
                if scores[choice] > scores[old_choice] + 1e-12:
                    ticks[site] = candidates[choice]
                    gaps[indices] = candidate_gaps[:, choice]
                    values[indices] = candidate_values[:, choice]
                    changed = True
            score = _quality(values)
            if score > best[phase_index][0]:
                best[phase_index] = (score, ticks.copy(), phase)
            if not changed or time.monotonic() >= end:
                break
        iteration += 1
    digital = max(best[1:], key=lambda entry: entry[0])
    return best[0][1].tolist(), digital[1].tolist(), digital[2]


def solve(case):
    start = time.monotonic()
    certificate, rows = compile_certificate(case)
    hardware = case["hardware"]
    if not len(rows):
        analog = digital = [0] * case["length"]
        phase_tick = hardware["phase_ticks"][0]
    else:
        analog, digital, phase_tick = _optimize(rows, hardware, max(0.1, 52.0 - (time.monotonic() - start)))
    return {"certificate": certificate, "analog": {"ticks": analog},
            "digital": {"ticks": digital, "phase_tick": phase_tick}}


def _optimize(rows, hardware, budget):
    try:
        library = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "optimizer.so"))
    except OSError:
        return _fallback(rows, hardware, budget)
    function = library.optimize_schedule
    int_pointer = ctypes.POINTER(ctypes.c_int)
    double_pointer = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [ctypes.c_int, ctypes.c_int, int_pointer, int_pointer, int_pointer,
                         double_pointer, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, ctypes.c_double, ctypes.c_uint, int_pointer]
    function.restype = ctypes.c_double
    rows = np.ascontiguousarray(rows, dtype=np.int32)
    caps = np.ascontiguousarray(hardware["caps"], dtype=np.int32)
    errors = np.ascontiguousarray(hardware["uncertainty"], dtype=np.float64)
    positive = np.ones(len(caps), dtype=np.int32)
    sparse_rows = [tuple((int(site), int(row[site])) for site in np.flatnonzero(row)) for row in rows]
    row_set = set(sparse_rows)
    for row in sparse_rows:
        for site, coefficient in row:
            if not positive[site]:
                continue
            flipped = tuple((position, -value if position == site else value) for position, value in row)
            if flipped[0][1] < 0:
                flipped = tuple((position, -value) for position, value in flipped)
            if flipped not in row_set:
                positive[site] = 0
    end = time.monotonic() + budget
    def run(phase, seconds, seed, initial=None):
        if phase == 0:
            return 0.0, np.zeros(len(caps), dtype=np.int32), 0
        ticks = np.ascontiguousarray(initial if initial is not None else caps * (np.arange(len(caps)) % 2 == 0), dtype=np.int32)
        score = function(len(caps), len(rows), rows.ctypes.data_as(int_pointer), caps.ctypes.data_as(int_pointer),
                         positive.ctypes.data_as(int_pointer), errors.ctypes.data_as(double_pointer),
                         hardware["denominator"], hardware["bandwidth"], 0 if phase is None else phase, hardware["phase_denominator"],
                         max(0.001, min(seconds, end - time.monotonic())), seed, ticks.ctypes.data_as(int_pointer))
        return score, ticks, phase
    analog = run(None, budget * 0.43, 8193)
    candidates = []
    screening_budget = budget * 0.23 / len(hardware["phase_ticks"])
    for phase in hardware["phase_ticks"]:
        candidates.append(run(phase, screening_budget, 10427 + phase))
    candidates.sort(key=lambda entry: entry[0], reverse=True)
    remaining = max(0.001, end - time.monotonic())
    for index in range(min(3, len(candidates))):
        candidate = candidates[index]
        candidates[index] = run(candidate[2], remaining * (0.5 if index == 0 else 0.25), 28103 + candidate[2], candidate[1])
    digital = max(candidates, key=lambda entry: entry[0])
    return analog[1].tolist(), digital[1].tolist(), int(digital[2])


if __name__ == "__main__":
    import sys
    print(json.dumps(solve(json.load(sys.stdin)), separators=(",", ":")))
