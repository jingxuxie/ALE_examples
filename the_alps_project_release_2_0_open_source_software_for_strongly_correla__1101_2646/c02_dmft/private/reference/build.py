import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


oracle = load_module("oracle", HERE / "oracle.py")
strong = load_module("strong", HERE / "strong.py")
weak = load_module("weak", ROOT / "participant/workspace/solve.py")
evaluator = load_module("evaluator", HERE.parent / "evaluator.py")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")


def make_fourier(seed, beta, count, intervals, size=4):
    generator = np.random.default_rng(seed)
    hamiltonian = np.diag(generator.uniform(-0.8, 0.8, size))
    for index in range(size - 1):
        hopping = generator.uniform(0.45, 1.1) * (-1 if index % 2 else 1)
        hamiltonian[index, index + 1] = hopping
        hamiltonian[index + 1, index] = hopping
    square = hamiltonian @ hamiltonian
    frequencies = 1j * (2 * np.arange(count) + 1) * np.pi / beta
    resolvent = np.linalg.inv(frequencies[:, None, None] * np.eye(size) - hamiltonian)
    entries = [(0, 0), (size - 1, size - 1), (0, 1), (0, 2), (0, 3), (1, 3)]
    return {"family": "fourier", "beta": beta, "n_tau": intervals,
            "channels": [{"sites": [row, column],
                          "moments": [float(row == column), float(hamiltonian[row, column]), float(square[row, column])],
                          "iw": oracle.pack(resolvent[:, row, column])} for row, column in entries]}


def make_afm(seed, beta, bands, count, intervals, nodes=96, duplicate=False):
    generator = np.random.default_rng(seed)
    chemical, field = generator.uniform(-0.35, 0.35), generator.uniform(0.1, 0.4)
    frequencies = 1j * (2 * np.arange(count) + 1) * np.pi / beta
    coordinates, quadrature = np.polynomial.legendre.leggauss(nodes)
    densities = []
    weiss = []
    impurity = []
    for band in range(bands):
        width = 0.6 + 0.32 * band + generator.uniform(0.1, 0.6)
        weights = quadrature * (1 + generator.uniform(0, 2) * coordinates**2 + 0.2 * np.cos(np.pi * coordinates))
        weights /= weights.sum()
        densities.append({"energy": (width * coordinates).tolist(), "weight": weights.tolist()})
        for spin in range(2):
            staggered = -field if spin == 0 else field
            delta = generator.uniform(0.15, 0.65) / (frequencies - generator.uniform(-0.4, 0.4))
            self_energy = generator.uniform(-0.2, 0.5) + generator.uniform(0.3, 1.2) / (frequencies - generator.uniform(-0.7, 0.7))
            initial = 1 / (frequencies + chemical + staggered - delta)
            weiss.append(initial)
            impurity.append(1 / (1 / initial - self_energy))
    if duplicate:
        densities[1] = densities[0]
        weiss[2:4] = weiss[0:2]
        impurity[2:4] = impurity[0:2]
    return {"family": "afm", "beta": beta, "mu": chemical, "h": field, "n_tau": intervals,
            "g0_iw": oracle.pack(weiss), "g_iw": oracle.pack(impurity), "dos": densities}


def make_legendre(seed, beta, degree, frequencies, count, low_sign=False):
    generator = np.random.default_rng(seed)
    configurations = []
    for index in range(count):
        size = 2 + index % 5
        annihilation = generator.uniform(0, beta, size)
        creation = generator.uniform(0, beta, size)
        if index % 4 == 0:
            creation[0] = annihilation[0]
        if index % 5 == 0:
            annihilation[1], creation[1] = 0.0, beta * (1 - 1e-9)
        matrix = generator.normal(0.0, 0.3, (size, size)) + np.diag(generator.uniform(0.5, 1.3, size))
        sign = -1 if index % 3 == 1 else 1
        configurations.append({"sign": sign, "weight": float(generator.uniform(1.4, 2.4) if sign > 0 else generator.uniform(0.6, 1.3)),
                               "c_times": annihilation.tolist(), "cdagger_times": creation.tolist(),
                               "matrix": matrix.tolist(), "f_prefactor": generator.uniform(-0.3, 1.8, size).tolist()})
    if low_sign:
        positive = sum(config["weight"] for config in configurations if config["sign"] > 0)
        negative = sum(config["weight"] for config in configurations if config["sign"] < 0)
        for config in configurations:
            if config["sign"] < 0:
                config["weight"] *= 0.72 * positive / negative
    return {"family": "legendre", "beta": beta, "n_legendre": degree, "n_iw": frequencies, "configurations": configurations}


def extract_function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    ending = opening + 1
    while depth:
        depth += (source[ending] == "{") - (source[ending] == "}")
        ending += 1
    return source[start:ending], source[:start].count("\n") + 1


def sources():
    records = [
        ("fourier", "C", "applications/dmft/qmc/fouriertransform.C", "73b3310067a2a332bab1a4da871874f3cf71d3a8", "e2e9e16e18f3e54855e438274d463f5c046d9651", "void FourierTransformer::backward_ft", "f2582554309e5aa4849bcb5d24838df3f41c86ca83be6fd3899384e40497316c", "aa617f9d4947a3d4f603b726fd1df4c8b11eb555b89c569f437baefc7cd5bbd9"),
        ("hilbert", "C", "applications/dmft/qmc/hilberttransformer.C", "18d8474e9150a5d8a4cdccf32c538471dc9f7b17", "2fa76e234a64cefa0ccb00a7b82b0d85a2f3023e", "matsubara_green_function_t GeneralFSHilbertTransformer::operator()", "e81399bda37f09206115507f76216de6c9218f7bd1c3ca50bb1f36fc6a11bd85", "e368c2adc59cab16e26783edaf898bae24f1c1ac42908f3d4294c6d5cb590f0f"),
        ("legendre", "cpp", "applications/dmft/qmc/hybridization/hybmatrix.cpp", "73b3310067a2a332bab1a4da871874f3cf71d3a8", "272d6e3531c2b0d2a60f3e53b0898b74b72aa698", "void hybmatrix::measure_Gl", "ebdb55064ffeb5d520c34a5095075741ffcc39dc28a6382b63d9361095ecaf6b", "6857e3f82162cdc5175a9c6761c158aaa20b9f26e96022198d732b24c8468f32"),
    ]
    public = []
    private = []
    target = ROOT / "participant/workspace/historical"
    target.mkdir(parents=True, exist_ok=True)
    for name, extension, path, before, after, signature, before_hash, after_hash in records:
        pre_bytes = (HERE / "upstream" / (name + "_before." + extension)).read_bytes()
        post_bytes = (HERE / "upstream" / (name + "_after." + extension)).read_bytes()
        assert hashlib.sha256(pre_bytes).hexdigest() == before_hash
        assert hashlib.sha256(post_bytes).hexdigest() == after_hash
        text = pre_bytes.decode()
        function, line = extract_function(text, signature)
        notice = text[:text.index("*/") + 2]
        excerpt = notice + "\n\n" + function + "\n"
        filename = name + "_before.cpp.txt"
        (target / filename).write_text(excerpt)
        record = {"repository": "ALPSim/ALPS", "revision": before, "path": path, "function_start_line": line,
                  "full_source_sha256": before_hash, "excerpt": filename, "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest()}
        public.append(record)
        private.append(dict(record, fix_revision=after, fixed_source_sha256=after_hash))
    save(target / "SOURCE_MAP.json", public)
    save(HERE / "source_manifest.json", private)


def main():
    sources()
    (ROOT / "attempt").mkdir(exist_ok=True)
    suites = {
        "core": [make_fourier(1103, 4.5, 14, 96), make_fourier(1129, 12.0, 20, 128, 5),
                 make_afm(2017, 7.0, 2, 10, 80, duplicate=True), make_afm(2027, 14.0, 3, 16, 128),
                 make_legendre(3011, 5.0, 10, 8, 8), make_legendre(3019, 11.0, 18, 12, 12)],
        "challenge": [make_fourier(4001, 16.0, 24, 192, 5), make_fourier(4013, 27.0, 30, 256), make_fourier(4019, 38.0, 36, 384, 6),
                      make_afm(5003, 24.0, 4, 20, 160, 128), make_afm(5009, 8.0, 5, 24, 192, 128), make_afm(5011, 34.0, 6, 32, 256, 192),
                      make_legendre(6007, 17.0, 24, 18, 16), make_legendre(6011, 29.0, 30, 24, 18, True), make_legendre(6029, 37.0, 32, 32, 24, True)],
    }
    manifest = {}
    checks = []
    for split, cases in suites.items():
        manifest[split] = []
        for index, case in enumerate(cases, 1):
            identifier = split + "_" + str(index).zfill(2)
            expected = oracle.solve(case)
            crosscheck = evaluator.errors_for(case, strong.solve(case), expected)
            baseline = evaluator.errors_for(case, weak.solve(case), expected)
            assert max(crosscheck.values()) < 2e-9, (identifier, crosscheck)
            assert max(baseline.values()) > 1e-5, (identifier, baseline)
            if case["family"] == "legendre":
                assert np.min(np.abs(oracle.unpack(expected["g_iw"]))) > 1e-5
            input_path = Path("reference/core" if split == "core" else "challenge_pool") / (identifier + ".json")
            reference_path = Path("reference/answers") / (identifier + ".json")
            save(HERE.parent / input_path, case)
            save(HERE.parent / reference_path, expected)
            record = {"id": identifier, "family": case["family"], "input": str(input_path), "reference": str(reference_path),
                      "scales": {key: max(baseline[key] / 4, 1e-8, 100 * crosscheck[key]) for key in baseline}}
            manifest[split].append(record)
            checks.append({"id": identifier, "strong_crosscheck_errors": crosscheck, "weak_errors": baseline})
    save(HERE / "manifest.json", manifest)
    save(HERE / "reference_checks.json", checks)
    sample = make_fourier(17, 3.0, 3, 12)
    sample["channels"] = [sample["channels"][index] for index in (0, 3, 4)]
    save(ROOT / "participant/input/sample_01.json", sample)
    sample = {"family": "legendre", "beta": 3.0, "n_legendre": 4, "n_iw": 3,
              "configurations": [{"sign": 1, "weight": 3, "c_times": [0.4], "cdagger_times": [2.3], "matrix": [[0.8]], "f_prefactor": [0.6]},
                                 {"sign": -1, "weight": 1, "c_times": [1.7], "cdagger_times": [0.2], "matrix": [[0.5]], "f_prefactor": [1.1]}]}
    save(ROOT / "participant/input/sample_02.json", sample)
    print(json.dumps({"core_cases": len(manifest["core"]), "challenge_cases": len(manifest["challenge"]),
                      "max_reference_crosscheck_error": max(max(check["strong_crosscheck_errors"].values()) for check in checks)}))


if __name__ == "__main__":
    main()
