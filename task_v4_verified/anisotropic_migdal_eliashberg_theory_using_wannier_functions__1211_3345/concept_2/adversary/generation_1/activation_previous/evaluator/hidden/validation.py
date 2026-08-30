import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import io
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))
from physics import constraint_report, json_write, load_instance, read_artifact


def main():
    instance = load_instance()
    reference_pair = np.stack([instance["reference"], instance["reference"]])
    results = []
    with tempfile.TemporaryDirectory(prefix="concept2_validation_") as directory:
        folder = Path(directory)

        def rejection(name, payload):
            artifact = folder / (name + ".npz")
            with artifact.open("wb") as stream:
                np.savez_compressed(stream, kernels=payload)
            try:
                kernels = read_artifact(artifact, instance["config"])
                report, canonical = constraint_report(kernels, instance)
                passed = not report["admissible"]
                error = report.get("errors", [])
            except Exception as problem:
                passed = True
                error = str(problem)
            results.append({"name": name, "passed": passed, "rejection": error})

        rejection("wrong_shape", reference_pair[:, :, :-1])
        for name, value in (("nan", np.nan), ("infinity", np.inf), ("negative", -.1), ("above_bound", 6.)):
            altered = reference_pair.copy()
            altered[0, 0, 0, 0] = value
            rejection(name, altered)
        altered = reference_pair.copy()
        altered[0, 0, 1, 2] += .01
        rejection("asymmetry", altered)
        altered = reference_pair.copy()
        altered[0, 0, 1, 2] += .01
        altered[0, 0, 2, 1] += .01
        rejection("row_and_static", altered)
        altered = reference_pair.copy()
        altered[0, 0, 0, 0] += .01
        altered[0, 1, 0, 0] -= .01
        rejection("diagonal", altered)
        cycle = np.zeros((8, 8))
        for left, right, sign in ((0, 1, 1), (2, 3, 1), (0, 3, -1), (1, 2, -1)):
            cycle[left, right] = cycle[right, left] = sign
        altered = reference_pair.copy()
        altered[0, 0] += .001 * cycle
        rejection("static_only", altered)
        altered = reference_pair.copy()
        altered[0, 0, 1, 2] += .001
        altered[0, 0, 2, 1] += .001
        altered[0, 1, 1, 2] -= .001
        altered[0, 1, 2, 1] -= .001
        rejection("mode_rows_only", altered)
        laplacian = np.zeros((8, 8))
        laplacian[0, 0] = laplacian[1, 1] = 1
        laplacian[0, 1] = laplacian[1, 0] = -1
        altered = reference_pair.copy()
        altered[0, 0] += .001 * laplacian
        altered[0, 1] -= .001 * laplacian
        rejection("diagonal_only", altered)
        rejection("object", np.array([object()], dtype=object))
        rejection("complex", reference_pair.astype(complex))
        rejection("boolean", reference_pair.astype(bool))
        original = folder / "original.npz"
        np.savez_compressed(original, kernels=reference_pair)
        extra = folder / "extra_key.npz"
        np.savez_compressed(extra, kernels=reference_pair, extra=np.zeros(1))
        try:
            read_artifact(extra, instance["config"])
            passed = False
        except Exception:
            passed = True
        results.append({"name": "extra_key", "passed": passed})
        links = (("symlink", folder / "symbolic.npz"), ("hardlink", folder / "hard.npz"))
        for name, link in links:
            if name == "symlink":
                link.symlink_to(original)
            else:
                os.link(original, link)
            try:
                read_artifact(link, instance["config"])
                passed = False
            except Exception:
                passed = True
            results.append({"name": name, "passed": passed})
            link.unlink()
        parent_link = folder / "linked_directory"
        parent_link.symlink_to(folder, target_is_directory=True)
        try:
            read_artifact(parent_link / "original.npz", instance["config"])
            passed = False
        except Exception:
            passed = True
        results.append({"name": "symlink_parent", "passed": passed})
        for name, compressed in (("zip_expansion", True), ("file_size", False)):
            artifact = folder / (name + ".npz")
            if compressed:
                with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("kernels.npy", b"0" * (instance["config"]["max_uncompressed_bytes"] + 1))
            else:
                artifact.write_bytes(b"0" * (instance["config"]["max_artifact_bytes"] + 1))
            try:
                read_artifact(artifact, instance["config"])
                passed = False
            except Exception:
                passed = True
            results.append({"name": name, "passed": passed})
        huge_header = io.BytesIO()
        np.lib.format.write_array_header_1_0(huge_header, {"descr": "<f8", "fortran_order": False, "shape": (2 ** 50,)})
        artifact = folder / "oversized_array_header.npz"
        with zipfile.ZipFile(artifact, "w") as archive:
            archive.writestr("kernels.npy", huge_header.getvalue())
        try:
            read_artifact(artifact, instance["config"])
            passed = False
        except Exception:
            passed = True
        results.append({"name": "oversized_array_header", "passed": passed})
        roundtrip = read_artifact(original, instance["config"])
        results.append({"name": "baseline_roundtrip", "passed": constraint_report(roundtrip, instance)[0]["admissible"]})
        feasible = reference_pair.copy()
        feasible[0, 0] += .0001 * cycle
        feasible[0, 2] -= .0001 * cycle
        results.append({"name": "feasible_nonzero_direction", "passed": constraint_report(feasible, instance)[0]["admissible"]})
    summary = {"passed": all(result["passed"] for result in results), "probes": results}
    json_write(ROOT / "attempts" / "adversary" / "validation.json", summary)
    print(summary, flush=True)
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
