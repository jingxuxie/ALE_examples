import argparse
import ctypes
import importlib.util
import json
from pathlib import Path
import time

from common import SIDE, private_path, tree_inventory, write_json

import numpy as np
from diagnostics import residual_report
from harness import load_suite
from models import load_model


VARIANTS = {
    "champion": (40, 40, 1, False),
    "native_compiler": (40, 40, 1, False),
    "half_ensemble": (40, 40, 0.5, False),
    "double_ensemble": (40, 40, 2, False),
    "quad_ensemble": (40, 40, 4, False),
    "long_bp": (80, 40, 1, False),
    "wide_osd": (40, 80, 1, False),
    "all_list": (40, 40, 1, True),
    "local_marginal": (40, 40, 1, False),
    "local_marginal_double": (40, 40, 2, False),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--cases")
    parser.add_argument("--variants", default="champion")
    parser.add_argument("--shots", type=int, default=32)
    parser.add_argument("--cpu-limit", type=float, default=300)
    parser.add_argument("--diagnostics-lib", type=Path)
    args = parser.parse_args()
    output = private_path(SIDE / "private_sweeps" / args.name)
    if output.exists():
        raise ValueError("Use a new private experiment name")
    output.mkdir(parents=True)
    snapshot = SIDE / "snapshots/confirmed_generation_1"
    identity = json.loads((snapshot / "manifest.json").read_text())
    if identity.get("main_confirmed") is not True or tree_inventory(snapshot / "code")["sha256"] != identity["inventory"]["sha256"]:
        raise ValueError("A stable, confirmed champion snapshot is required")
    specification = importlib.util.spec_from_file_location("confirmed_champion", snapshot / "code/submission.py")
    champion = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(champion)
    native = champion._native
    if args.diagnostics_lib:
        native = ctypes.CDLL(str(private_path(args.diagnostics_lib)))
        native.create.argtypes = champion._native.create.argtypes
        native.create.restype = ctypes.c_void_p
        native.destroy.argtypes = [ctypes.c_void_p]
        native.destroy.restype = None
        native.run_diagnostics.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        native.run_diagnostics.restype = None
    suite, manifest = load_suite(args.suite)
    selected = set(args.cases.split(",")) if args.cases else None
    variants = args.variants.split(",")
    if any(variant not in VARIANTS for variant in variants):
        raise ValueError("Unknown private knob control")
    if "all_list" in variants and not args.diagnostics_lib:
        raise ValueError("all_list requires the explicitly instrumented private library")
    records = []
    total_cpu = 0.0
    for case in manifest["cases"]:
        spec = case["spec"]
        case_id = spec["case_id"]
        if selected is not None and case_id not in selected:
            continue
        model = load_model(suite / "models" / case_id)
        with np.load(suite / "private" / (case_id + ".npz"), allow_pickle=False) as data:
            syndromes, labels, matching = data["syndromes"][:args.shots], data["labels"][:args.shots], data["baseline"][:args.shots]
        with np.load(suite / "private" / (case_id + "_features.npz"), allow_pickle=False) as data:
            features = {name: data[name][:args.shots] for name in data.files}
        for variant in variants:
            if total_cpu >= args.cpu_limit:
                write_json(output / "summary.json", dict(complete=False, reason="Private CPU budget exhausted", cpu_seconds=total_cpu, records=records))
                return
            iterations, order, multiplier, force_list = VARIANTS[variant]
            ensemble = max(1, int((2 if model["rounds"] > 1 else 8) * multiplier))
            matrix = np.ascontiguousarray(model["detector_matrix"], dtype=np.uint8)
            logical = np.ascontiguousarray(model["observable_matrix"], dtype=np.uint8)
            probabilities = np.ascontiguousarray(model["probabilities"], dtype=np.float64)
            started = time.process_time()
            handle = native.create(*matrix.shape, matrix.ctypes.data, logical.ctypes.data, probabilities.ctypes.data)
            if variant.startswith("local_marginal"):
                if not hasattr(native, "set_triplets"):
                    raise ValueError("Marginal portfolio library is required")
                indices = np.flatnonzero(model["mechanism_kind"] == "X")
                triplets = np.ascontiguousarray(np.column_stack([indices, indices + 1, indices + 2]), dtype=np.int32)
                if not ((model["mechanism_kind"][indices + 1] == "Z").all() and (model["mechanism_kind"][indices + 2] == "Y").all()):
                    raise ValueError("Triplet order assumption violated")
                if np.any(matrix[:, indices] ^ matrix[:, indices + 1] ^ matrix[:, indices + 2]) or np.any(logical[:, indices] ^ logical[:, indices + 1] ^ logical[:, indices + 2]):
                    raise ValueError("Proposed marginalization is not a detector/logical gauge")
                native.set_triplets.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
                native.set_triplets.restype = None
                native.set_triplets(handle, len(triplets), triplets.ctypes.data)
            predictions = np.empty((len(labels), 4), dtype=np.uint8)
            metrics = np.zeros((len(labels), 5), dtype=np.float64)
            try:
                for offset in range(0, len(labels), 8):
                    batch = np.ascontiguousarray(syndromes[offset:offset + 8])
                    output_batch = predictions[offset:offset + 8]
                    if args.diagnostics_lib:
                        native.run_diagnostics(handle, len(batch), batch.ctypes.data, output_batch.ctypes.data,
                                               metrics[offset:offset + 8].ctypes.data, iterations, order, ensemble, int(force_list))
                    else:
                        native.run(handle, len(batch), batch.ctypes.data, output_batch.ctypes.data, iterations, order, ensemble)
            finally:
                native.destroy(handle)
            elapsed = time.process_time() - started
            total_cpu += elapsed
            if not np.isin(predictions, [0, 1]).all():
                raise ValueError("Native predictions are not binary; check output buffer layout")
            failure = np.any(predictions != labels, axis=1)
            record = dict(case_id=case_id, stress_group=spec["stress_group"], variant=variant, shots=len(labels),
                          failures=int(failure.sum()), cpu_seconds=elapsed, iterations=iterations, order=order, ensemble=ensemble)
            if args.diagnostics_lib:
                fast = metrics[:, 0] > 0
                record.update(fast_shots=int(fast.sum()), fast_failures=int((fast & failure).sum()),
                              list_failures=int((~fast & failure).sum()),
                              mean_truncated_gap_on_list_failures=float(metrics[~fast & failure, 1].mean()) if (~fast & failure).any() else None)
            if variant == "champion":
                reference = champion.Decoder(model).decode(syndromes)
                record["reference_disagreements"] = int(np.any(reference != predictions, axis=1).sum())
                if record["reference_disagreements"]:
                    raise ValueError("Private native call differs from the promoted Python API")
            np.savez_compressed(output / (case_id + "__" + variant + ".npz"), predictions=predictions, diagnostics=metrics)
            write_json(output / (case_id + "__" + variant + "_residuals.json"), residual_report(model, syndromes, labels, matching, predictions, features))
            records.append(record)
            write_json(output / "summary.json", dict(complete=False, cpu_seconds=total_cpu, records=records,
                       source_tree_sha256=identity["inventory"]["sha256"], exploratory=True, official_score=False))
            print(json.dumps(record), flush=True)
    write_json(output / "summary.json", dict(complete=True, cpu_seconds=total_cpu, records=records,
               source_tree_sha256=identity["inventory"]["sha256"], exploratory=True, official_score=False))


if __name__ == "__main__":
    main()
