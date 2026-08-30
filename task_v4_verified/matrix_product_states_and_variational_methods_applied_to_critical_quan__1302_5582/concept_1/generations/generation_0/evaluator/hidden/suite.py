"""Frozen instances and a private same-physics extension generator."""

import json
from pathlib import Path

import numpy as np


def expand(record):
    length = record["n"]
    request = {"version": 1, "case_id": record["id"], "seed": record["seed"],
               "n_sites": length, "local_dim": record["d"], "bond_cap": record["cap"],
               "sector": record["sector"]}
    if "profile" not in record:
        for key in ("mass2", "lambda4", "omega"):
            request[key] = [record[key]] * length
        request["field"] = [0.0] * length
        request["coupling"] = [record["coupling"]] * (length - 1)
    elif record["profile"] == "interface":
        request["mass2"] = [-1.85 if site < length // 2 else -0.25 for site in range(length)]
        request["lambda4"] = [1.65 + 0.35 * (site % 3) for site in range(length)]
        request["omega"] = [0.6 if site % 2 else 1.7 for site in range(length)]
        request["coupling"] = [0.35 if site == length // 2 - 1 else 1.2
                               for site in range(length - 1)]
        request["field"] = [0.002 * np.cos(site * np.pi / (length - 1)) for site in range(length)]
    else:
        request["mass2"] = [-2.15 if site % 7 < 4 else 0.15 for site in range(length)]
        request["lambda4"] = [1.8 + 0.25 * np.sin(site) for site in range(length)]
        request["omega"] = [0.55 + 1.3 * (site % 3) / 2 for site in range(length)]
        request["coupling"] = [0.06 if site % 6 == 3 else 1.1 for site in range(length - 1)]
        request["field"] = [0.003 * (-1 if site < length // 2 else 1) for site in range(length)]
    return request


def cases():
    records = json.loads(Path(__file__).with_name("cases.json").read_text())["cases"]
    return [(record["family"], expand(record)) for record in records]


def extension_cases(seed, count=16):
    generator = np.random.default_rng(seed)
    families = ("symmetric", "crossover", "double_well", "inhomogeneous")
    for index in range(count):
        family = families[index % 4]
        length = int(generator.choice([10, 12, 14, 16, 18, 20]))
        dimension = int(generator.choice([8, 10, 12, 14]))
        sector = str(generator.choice(["any", "even", "odd"])) if family == "double_well" else "any"
        mass = {"symmetric": generator.uniform(0.05, 0.8),
                "crossover": generator.uniform(-1.3, -0.5),
                "double_well": generator.uniform(-2.8, -1.8),
                "inhomogeneous": generator.uniform(-2.0, -0.6)}[family]
        request = expand({"id": "extension-%d-%d" % (seed, index), "seed": int(seed + index),
                          "n": length, "d": dimension, "cap": int(generator.choice([8, 10, 12])),
                          "sector": sector, "mass2": float(mass),
                          "lambda4": float(generator.uniform(1.4, 2.8)),
                          "omega": float(generator.uniform(0.55, 1.65)),
                          "coupling": float(generator.uniform(0.6, 1.5))})
        if family == "inhomogeneous":
            request["mass2"] = (mass + 0.65 * np.cos(np.linspace(0, 3 * np.pi, length))
                                + generator.uniform(-0.2, 0.2, length)).tolist()
            request["omega"] = generator.uniform(0.55, 1.8, length).tolist()
            request["coupling"] = generator.uniform(0.15, 1.5, length - 1).tolist()
            request["field"] = (generator.choice([-1.0, 1.0], length)
                                * generator.uniform(1e-5, 0.004, length)).tolist()
        yield family, request
