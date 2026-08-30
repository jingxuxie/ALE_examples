import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
import json
from pathlib import Path

import numpy as np

from trusted.audit import independent_audit
from trusted.physics import EliashbergSolver, constraint_report, json_write, load_instance, physics_report, read_artifact


POOL = Path(__file__).resolve().parent


def within_pool(path):
    path = Path(path)
    if not path.is_absolute():
        path = POOL / path
    path = path.resolve()
    if path != POOL and POOL not in path.parents:
        raise ValueError("all sidecar outputs and instances must stay under ratchet_pool")
    return path


def logical_hash(instance):
    digest = hashlib.sha256(json.dumps(instance["config"], sort_keys=True).encode())
    for name in sorted(key for key in instance if key not in ("config", "input_sha256")):
        values = np.asarray(instance[name], dtype="<f8")
        digest.update(name.encode())
        digest.update(str(values.shape).encode())
        digest.update(values.tobytes())
    return digest.hexdigest()


def audit_pair(kernels, instance):
    constraints, canonical = constraint_report(kernels, instance)
    report = {
        "admissible": constraints["admissible"], "valid": False, "score": 0.,
        "target_ratio": instance["config"]["target_ratio"], "constraints": constraints,
        "logical_instance_sha256": logical_hash(instance),
    }
    if not report["admissible"]:
        return report
    physics = physics_report(canonical, instance)
    independent = independent_audit(canonical, instance, physics, EliashbergSolver)
    report.update({
        "score": physics["score"], "physics": physics, "independent": independent,
        "valid": physics["target_met"] and physics["converged"] and independent["passed"],
    })
    total_rows = instance["row_sums"].sum(axis=0)
    scale = np.sqrt(instance["weights"] / (1 + total_rows))
    eigenvalues = [np.linalg.eigvalsh(modes.sum(axis=0) * np.outer(scale, scale)) for modes in canonical]
    report["static_normalized_spectrum_max_difference"] = float(np.max(np.abs(eigenvalues[0] - eigenvalues[1])))
    return report


def save_instance(folder, instance):
    folder = within_pool(folder)
    folder.mkdir(parents=True, exist_ok=True)
    json_write(folder / "config.json", instance["config"])
    with (folder / "reference.npz").open("xb") as stream:
        np.savez_compressed(stream, **{name: values for name, values in instance.items() if name not in ("config", "input_sha256")})


def verify_snapshot():
    manifest = json.loads((POOL / "snapshot_manifest.json").read_text())
    for name, expected in manifest["files"].items():
        actual = hashlib.sha256((POOL / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("trusted sidecar snapshot changed: " + name)
    return manifest
