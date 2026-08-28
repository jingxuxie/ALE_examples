import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import reference
from spirit import chain, simulation, state, system
from spirit.parameters import llg

ORIGINAL_BUILDER = reference.extended_case
FAMILIES = {
    "boundary": "initial_domain_wall_01_731101",
    "interface": "initial_exchange_spring_01_731201",
}


def build_variant(family, seed, count):
    generator = np.random.default_rng(seed)
    parameters = {"exchange_scale": float(generator.uniform(0.94, 1.06)), "easy_anisotropy_scale": float(generator.uniform(0.93, 1.07)), "transverse_field_scale": float(generator.uniform(0.95, 1.05)), "longitudinal_field_scale": float(generator.uniform(0.94, 1.06))}
    reference.TRUSTED = reference.PRIVATE / "reference/initial" / FAMILIES[family]
    reference.ROOT = ROOT / "heldout" / f"{family}_{seed}"
    reference.ROOT.mkdir(parents=True, exist_ok=True)
    preparation = {}

    def prepare(size):
        started = time.perf_counter()
        case, original_saddle = ORIGINAL_BUILDER(size)
        original_minimum = np.asarray(case["minimum_a"])
        deviation = np.arctan2(original_saddle[:, 0], original_saddle[:, 2]) - np.arctan2(original_minimum[:, 0], original_minimum[:, 2])
        deviation = np.arctan2(np.sin(deviation), np.cos(deviation))
        case["case_id"] = f"scale_{family}_{seed}_N{size}"
        case["seed"] = seed
        case["exchange_meV"] = (np.asarray(case["exchange_meV"]) * parameters["exchange_scale"]).tolist()
        tensors = np.asarray(case["anisotropy_meV"])
        tensors[:, 0, 0] *= parameters["easy_anisotropy_scale"]
        tensors[:, 2, 2] *= parameters["easy_anisotropy_scale"]
        case["anisotropy_meV"] = tensors.tolist()
        case["field_meV"][0] *= parameters["transverse_field_scale"]
        case["field_meV"][2] *= parameters["longitudinal_field_scale"]
        directory = reference.ROOT / f"N{size}"
        directory.mkdir(exist_ok=True)
        config = directory / "minimum_preparation.cfg"
        config.write_text(reference.spirit_config(case))
        with state.State(str(config), quiet=True) as pointer:
            chain.image_to_clipboard(pointer)
            chain.set_length(pointer, 2)
            for image, name in enumerate(["minimum_a", "minimum_b"]):
                reference.set_spins(pointer, np.asarray(case[name]), image)
                llg.set_convergence(pointer, 1e-11, idx_image=image)
                simulation.start(pointer, simulation.METHOD_LLG, simulation.SOLVER_LBFGS_OSO, n_iterations=20000, idx_image=image)
                case[name] = system.get_spin_directions(pointer, idx_image=image).copy().tolist()
        minimum = np.asarray(case["minimum_a"])
        angle = np.arctan2(minimum[:, 0], minimum[:, 2]) + deviation
        saddle = np.column_stack((np.sin(angle), np.zeros(size), np.cos(angle)))
        preparation[size] = time.perf_counter() - started
        return case, saddle

    reference.extended_case = prepare
    os.chdir(reference.ROOT)
    records = []
    for size in [128, count]:
        started = time.perf_counter()
        reference.build(size)
        path = reference.ROOT / f"N{size}/validation.json"
        validation = json.loads(path.read_text())
        validation["native_preparation_seconds"] = preparation[size]
        validation["full_warm_continuation_seconds"] = time.perf_counter() - started
        validation["seed_family"] = family
        validation["parameter_perturbations"] = parameters
        validation["provisional_not_frozen"] = True
        if validation["full_warm_continuation_seconds"] >= 90:
            raise RuntimeError("warm native reference exceeds advertised computational budget")
        reference.write_json(path, validation)
        records.append({"size": size, "validation": str(path.relative_to(ROOT)), "warm_seconds": validation["full_warm_continuation_seconds"], "barrier_meV": validation["barrier_meV"]})
    small = json.loads((reference.ROOT / "N128/validation.json").read_text())
    large = json.loads((reference.ROOT / f"N{count}/validation.json").read_text())
    case_path = reference.ROOT / f"N{count}/case.json"
    artifact = {"family": family, "seed": seed, "n_spins": count, "parameters": parameters, "case": str(case_path.relative_to(ROOT)), "case_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(), "records": records, "barrier_size_difference_meV": abs(small["barrier_meV"] - large["barrier_meV"]), "log_omega0_size_difference": abs(small["log_omega0"] - large["log_omega0"])}
    print(f"HELDOUT CERTIFIED {family} seed={seed} N={count} seconds={large['full_warm_continuation_seconds']:.3f}", flush=True)
    return artifact


if __name__ == "__main__":
    cases = []
    for family, seeds in [("boundary", [826801, 826802, 826803]), ("interface", [826804, 826805, 826806])]:
        for seed, count in zip(seeds, [1024, 1536, 2048]):
            cases.append(build_variant(family, seed, count))
    reference.write_json(ROOT / "heldout/manifest.json", {"provisional_not_frozen": True, "native_cold_search_timing": None, "method": "Native LLG prepares perturbed minima; localized seed angular deviation is transported from the trusted frozen family and refined by native climbing GNEB. Native dense HTST at N128, native sparse HTST at each size, independent full spectra/FD, energy-rounding checks and both native downhill descents certify every case. Warm timing includes preparation. No exhaustive global-lowest-saddle proof is claimed.", "cases": cases})
