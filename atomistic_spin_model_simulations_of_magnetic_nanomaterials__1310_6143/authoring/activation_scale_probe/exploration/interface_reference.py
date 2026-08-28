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


reference.TRUSTED = reference.PRIVATE / "reference/initial/initial_exchange_spring_01_731201"
reference.ROOT = ROOT / "interface"
reference.ROOT.mkdir(parents=True, exist_ok=True)
original_builder = reference.extended_case
preparation = {}


def prepare(count):
    started = time.perf_counter()
    case, original_saddle = original_builder(count)
    case["case_id"] = f"interface_scale_N{count}"
    directory = reference.ROOT / f"N{count}"
    directory.mkdir(exist_ok=True)
    config = directory / "minimum_preparation.cfg"
    config.write_text(reference.spirit_config(case))
    original_minimum = np.asarray(case["minimum_a"])
    delta = np.arctan2(original_saddle[:, 0], original_saddle[:, 2]) - np.arctan2(original_minimum[:, 0], original_minimum[:, 2])
    delta = np.arctan2(np.sin(delta), np.cos(delta))
    with state.State(str(config), quiet=True) as pointer:
        chain.image_to_clipboard(pointer)
        chain.set_length(pointer, 2)
        for image, name in enumerate(["minimum_a", "minimum_b"]):
            reference.set_spins(pointer, np.asarray(case[name]), image)
            llg.set_convergence(pointer, 1e-11, idx_image=image)
            simulation.start(pointer, simulation.METHOD_LLG, simulation.SOLVER_LBFGS_OSO, n_iterations=20000, idx_image=image)
            case[name] = system.get_spin_directions(pointer, idx_image=image).copy().tolist()
    minimum = np.asarray(case["minimum_a"])
    angle = np.arctan2(minimum[:, 0], minimum[:, 2]) + delta
    saddle = np.column_stack((np.sin(angle), np.zeros(count), np.cos(angle)))
    preparation[count] = time.perf_counter() - started
    return case, saddle


reference.extended_case = prepare
os.chdir(reference.ROOT)
for count in [128, 512, 2048]:
    started = time.perf_counter()
    reference.build(count)
    path = reference.ROOT / f"N{count}/validation.json"
    validation = json.loads(path.read_text())
    validation["native_preparation_seconds"] = preparation[count]
    validation["full_warm_continuation_seconds"] = time.perf_counter() - started
    validation["seed_family"] = "Cartesian x-easy/z-easy exchange-spring interface"
    validation["source_minimum_preparation"] = "Native LLG relaxes both padded minima before transporting the localized seed's angular deviation."
    reference.write_json(path, validation)
    print(f"INTERFACE VALIDATED N={count} total={validation['full_warm_continuation_seconds']:.3f}s", flush=True)
