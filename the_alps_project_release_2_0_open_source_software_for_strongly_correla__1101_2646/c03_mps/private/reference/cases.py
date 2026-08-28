import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def rounded(value):
    return round(float(value), 12)


def spin_chain(length, anisotropy, dimerization, modulation, phase):
    bonds = []
    for site in range(length - 1):
        coupling = 1 + dimerization * (-1) ** site + modulation * math.sin(0.37 * site + phase)
        bonds.append({"sites": [site, site + 1], "jxy": rounded(coupling), "jz": rounded(coupling)})
    left = max(1, length // 4)
    distances = sorted(set([1, 2, min(4, length - left - 2), min(8, length - left - 2), length // 2]))
    observables = [{"kind": kind, "sites": [left, left + distance]} for kind in ["zz", "string"] for distance in distances]
    return {
        "family": "spin1_chain", "length": length, "spin": 1,
        "ground_sector": 0, "excited_sector": 2,
        "bonds": bonds,
        "single_ion": [rounded(anisotropy + 0.025 * math.cos(0.29 * site + phase)) for site in range(length)],
        "field": [rounded(0.012 * math.sin(0.53 * site + phase)) for site in range(length)],
        "observables": observables,
    }


def spin_ladder(rungs, rung_exchange, anisotropy, modulation, phase):
    length = 2 * rungs
    bonds = []
    for rung in range(rungs):
        exchange = rung_exchange * (1 + modulation * math.cos(0.47 * rung + phase))
        bonds.append({"sites": [2 * rung, 2 * rung + 1], "jxy": rounded(exchange), "jz": rounded(exchange * anisotropy)})
    for rung in range(rungs - 1):
        for leg in [0, 1]:
            exchange = 1 + modulation * math.sin(0.71 * rung + 0.4 * leg + phase)
            bonds.append({"sites": [2 * rung + leg, 2 * (rung + 1) + leg], "jxy": rounded(exchange), "jz": rounded(exchange * anisotropy)})
    center = rungs // 2
    pairs = [[2 * center, 2 * center + 1], [2 * (center - 1), 2 * center]]
    for distance in [2, 4, min(7, rungs - center - 1)]:
        if center + distance < rungs:
            pairs.extend([[2 * center, 2 * (center + distance)], [2 * center, 2 * (center + distance) + 1]])
    pairs = [list(pair) for pair in dict.fromkeys(tuple(pair) for pair in pairs)]
    return {
        "family": "spinhalf_ladder", "length": length, "spin": 0.5,
        "ground_sector": 0, "excited_sector": 1,
        "bonds": bonds, "single_ion": [0.0] * length,
        "field": [rounded(0.055 * (-1) ** (site // 2 + site % 2) + 0.015 * math.cos(0.23 * site + phase)) for site in range(length)],
        "observables": [{"kind": kind, "sites": pair} for kind in ["zz", "xx"] for pair in pairs],
    }


def boson_chain(length, cutoff, interaction, modulation, potential, phase):
    left = max(1, length // 4)
    distances = sorted(set([1, 2, min(4, length - left - 2), min(8, length - left - 2), length // 2]))
    return {
        "family": "bose_hubbard", "length": length, "nmax": cutoff, "particles": length,
        "bonds": [{"sites": [site, site + 1], "hopping": rounded(1 + modulation * math.sin(0.43 * site + phase))} for site in range(length - 1)],
        "interaction": [rounded(interaction * (1 + 0.04 * math.cos(0.31 * site + phase))) for site in range(length)],
        "potential": [rounded(potential * ((2 * site / (length - 1) - 1) ** 2 + 0.2 * math.cos(0.61 * site + phase))) for site in range(length)],
        "observables": [{"kind": kind, "sites": [left, left + distance]} for kind in ["one_body", "density_connected"] for distance in distances],
    }


def all_cases():
    return {
        "core": {
            "s1_40": spin_chain(40, 0.08, 0.04, 0.025, 0.3),
            "s1_56": spin_chain(56, 0.25, 0.10, 0.035, 1.1),
            "ladder_40": spin_ladder(20, 1.8, 1.0, 0.10, 0.4),
            "ladder_56": spin_ladder(28, 1.4, 1.1, 0.12, 1.3),
            "boson_32": boson_chain(32, 3, 6.0, 0.08, 0.45, 0.2),
            "boson_40": boson_chain(40, 4, 4.5, 0.06, 0.35, 1.0),
        },
        "challenge": {
            "s1_48": spin_chain(48, 0.42, 0.08, 0.05, 2.0),
            "s1_64": spin_chain(64, -0.15, 0.12, 0.04, 0.7),
            "ladder_48": spin_ladder(24, 1.6, 1.06, 0.15, 2.2),
            "ladder_64": spin_ladder(32, 1.2, 0.95, 0.12, 0.8),
            "boson_36": boson_chain(36, 3, 5.2, 0.10, 0.30, 2.3),
            "boson_48": boson_chain(48, 4, 7.0, 0.09, 0.50, 1.7),
        },
    }


def small_cases():
    return {
        "spin1_small_a": spin_chain(6, 0.15, 0.1, 0.04, 0.3),
        "spin1_small_b": spin_chain(6, -0.1, 0.05, 0.07, 1.1),
        "ladder_small_a": spin_ladder(3, 1.5, 1.08, 0.1, 0.5),
        "ladder_small_b": spin_ladder(4, 1.8, 0.96, 0.13, 1.2),
        "boson_small_a": boson_chain(4, 3, 5.0, 0.1, 0.3, 0.4),
        "boson_small_b": boson_chain(5, 4, 4.5, 0.08, 0.4, 1.0),
    }


def write_cases():
    manifest = {"schema_version": 1, "timeout_seconds": 600, "splits": {}}
    for split, cases in all_cases().items():
        manifest["splits"][split] = []
        folder = ROOT / "private" / "challenge_pool" / split
        folder.mkdir(parents=True, exist_ok=True)
        for case_id, case in cases.items():
            relative = f"challenge_pool/{split}/{case_id}.json"
            (ROOT / "private" / relative).write_text(json.dumps(case, indent=2) + "\n")
            manifest["splits"][split].append({"id": case_id, "family": case["family"], "input": relative, "reference": f"reference/data/{case_id}.json"})
    (ROOT / "private" / "challenge_pool" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    examples = {"example_spin1.json": small_cases()["spin1_small_a"], "example_boson.json": small_cases()["boson_small_a"]}
    for filename, case in examples.items():
        (ROOT / "participant" / "input" / filename).write_text(json.dumps(case, indent=2) + "\n")
    (ROOT / "attempt").mkdir(exist_ok=True)


if __name__ == "__main__":
    write_cases()
