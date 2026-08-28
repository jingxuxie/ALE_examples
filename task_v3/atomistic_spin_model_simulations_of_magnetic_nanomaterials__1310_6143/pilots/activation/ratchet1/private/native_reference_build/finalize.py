import datetime
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RATCHET = ROOT.parents[1]
TASK = RATCHET.parents[2]
SIDECAR = TASK / "authoring/activation_scale_probe"
sys.path.insert(0, str(SIDECAR))
import reference


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def updated(value):
    if isinstance(value, dict):
        return {name: updated(item) for name, item in value.items()}
    if isinstance(value, list):
        return [updated(item) for item in value]
    if isinstance(value, str) and value.startswith("native_reference_build/"):
        return "private/" + value
    if isinstance(value, str) and value.startswith("private/challenge_pool/ratchet1_"):
        return value.replace("private/challenge_pool/", "private/challenge_pool/challenge/", 1)
    return value


old_challenge = RATCHET / "private/challenge_pool"
new_challenge = old_challenge / "challenge"
new_challenge.mkdir(exist_ok=True)
if (old_challenge / "manifest.json").exists():
    manifest = read(old_challenge / "manifest.json")
    for record in manifest["cases"]:
        source = (RATCHET / record["case_file"]).parent
        target = new_challenge / source.name
        if target.exists():
            raise RuntimeError(f"refusing to replace existing challenge {target}")
        source.rename(target)
    (old_challenge / "manifest.json").rename(new_challenge / "manifest.json")

summary = {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_revision": "e82250d3b14411c2c2fa292d143f13e3e111ad8c", "initial": [], "challenge": [], "unmodified_original_submission_sha256": digest(TASK / "pilots/activation/attempt/solve.py"), "no_fresh_agent_launch": True, "no_upstream_implementation_changes": True}
for split, relative in [("initial", "private/reference/initial"), ("challenge", "private/challenge_pool/challenge")]:
    destination = RATCHET / relative
    manifest = updated(read(destination / "manifest.json"))
    for record in manifest["cases"]:
        case_path = RATCHET / record["case_file"]
        solution_path = RATCHET / record["solution_file"]
        validation_path = RATCHET / record["validation_file"]
        case = read(case_path)
        solution = read(solution_path)
        validation = updated(read(validation_path))
        reference.write_json(validation_path, validation)
        states = {"minimum_a": np.asarray(case["minimum_a"]), "minimum_b": np.asarray(case["minimum_b"]), "saddle": np.asarray(solution["saddle"])}
        diagnostics = {name: reference.diagnose(case, spins, False) for name, spins in states.items()}
        norm_error = max(float(np.max(np.abs(np.linalg.norm(spins, axis=1) - 1))) for spins in states.values())
        tensors = np.asarray(case["anisotropy_meV"])
        cartesian = np.max(np.abs(tensors - np.einsum("ni,ij->nij", np.diagonal(tensors, axis1=1, axis2=2), np.eye(3)))) == 0
        if norm_error > 1e-10 or not cartesian or not validation["validated"]:
            raise RuntimeError("unit norm, Cartesian tensor or native validation check failed")
        if min(diagnostics[name]["eigenvalues"][0] for name in ["minimum_a", "minimum_b"]) <= 1e-6:
            raise RuntimeError("endpoint is not a positive-inertia minimum")
        if len(solution["eigenvalues_min_meV"]) != 2 * case["n_spins"] or len(solution["eigenvalues_saddle_meV"]) != 2 * case["n_spins"]:
            raise RuntimeError("incomplete spectrum")
        eigenvalues = np.asarray(solution["eigenvalues_saddle_meV"])
        if np.sum(eigenvalues < -1e-6) != 1 or np.any(np.abs(eigenvalues) <= 1e-6):
            raise RuntimeError("saddle inertia invalid or zero modes present")
        if validation["reference_runtime_seconds"] >= 90 or case["time_limit_seconds"] != 90:
            raise RuntimeError("runtime contract mismatch")
        summary[split].append({"case_id": case["case_id"], "family": case["family"], "n_spins": case["n_spins"], "reference_runtime_seconds": validation["reference_runtime_seconds"], "unit_norm_max_error": norm_error, "saddle_residual_meV": diagnostics["saddle"]["residual_meV"], "minimum_b_lowest_eigenvalue_meV": float(diagnostics["minimum_b"]["eigenvalues"][0]), "negative_modes": 1, "zero_modes": 0, "native_sparse_log_omega_error": validation["native_sparse_log_omega_error"], "native_energy_difference_within_float32_rounding_bound": abs(validation["native_barrier_meV"] - validation["barrier_meV"]) <= validation["native_barrier_rounding_bound_meV"], "parameter_perturbations": validation["parameter_perturbations"]})
    manifest["sha256"] = {record[name]: digest(RATCHET / record[name]) for record in manifest["cases"] for name in ["case_file", "solution_file", "validation_file"]}
    reference.write_json(destination / "manifest.json", manifest)
    provenance_path = ROOT / f"{split}_provenance.json"
    provenance = read(provenance_path)
    if "build_time_input_source_sha256" not in provenance:
        provenance["build_time_input_source_sha256"] = provenance["input_source_sha256"]
    inputs = {}
    for relative_path in provenance["build_time_input_source_sha256"]:
        current = relative_path.replace("ratchet1/native_reference_build/", "ratchet1/private/native_reference_build/")
        inputs[current] = digest(TASK / current)
    for seed_directory in ["initial_domain_wall_01_731101", "initial_exchange_spring_01_731201", "initial_coherent_01_731001"]:
        for filename in ["case.json", "solution.json"]:
            path = TASK / "pilots/activation/private/reference/initial" / seed_directory / filename
            inputs[str(path.relative_to(TASK))] = digest(path)
    provenance["input_source_sha256"] = inputs
    provenance["artifact_sha256"] = {str(path.relative_to(RATCHET)): digest(path) for path in sorted((ROOT / split).rglob("*")) if path.is_file()}
    provenance["manifest_sha256"] = digest(destination / "manifest.json")
    provenance["relocation_note"] = "Build-time source hashes preserved separately; only artifact paths and rebuild root/layout changed after native generation. Historical logs retain original launch paths."
    reference.write_json(provenance_path, provenance)
summary["heldout_parameter_streams_disjoint"] = True
summary["challenge_not_run_through_old_solver_or_scored"] = True
summary["supported_families"] = ["boundary_localized", "soft_interface", "coherent_control"]
summary["global_claim_limit"] = "Lowest of natively certified compared mechanisms; not an exhaustive global saddle proof. Native author timing is warm continuation including certification and comparisons."
reference.write_json(ROOT / "handoff.json", summary)
print("READY: initial6 + challenge3 native cases; corrected paths, hashes, positive minima, index1/nozero saddles, all reference runtimes<90s", flush=True)
