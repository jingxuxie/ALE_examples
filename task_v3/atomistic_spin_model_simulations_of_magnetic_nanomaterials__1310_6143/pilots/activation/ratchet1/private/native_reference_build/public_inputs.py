import copy
import os

import build


directory = build.ROOT / "public_inputs_preparation"
directory.mkdir(parents=True, exist_ok=True)
os.chdir(directory)
small, _, preparation = build.prepared_case("coherent_control", 92914001, 8, "public", directory)
long = build.load(build.SIDECAR / "exploration/heldout/boundary_826802/N1536/case.json")
destination = build.SIDECAR / "public_inputs"
for name, original in [("small", small), ("long", long)]:
    case = copy.deepcopy(original)
    case["case_id"] = f"public_{name}"
    case["family"] = "unlabeled"
    case["seed"] = 0
    build.reference.write_json(destination / f"{name}.json", case)
build.reference.write_json(directory / "provenance.json", {"public_small_parameter_seed": 92914001, "public_small_native_preparation": preparation, "public_long_input_source": "authoring/activation_scale_probe/exploration/heldout/boundary_826802/N1536/case.json", "public_long_source_sha256": build.digest(build.SIDECAR / "exploration/heldout/boundary_826802/N1536/case.json"), "public_input_sha256": {name: build.digest(destination / f"{name}.json") for name in ["small", "long"]}, "contains_solutions": False, "overlaps_ratchet1_heldout_parameters": False})
