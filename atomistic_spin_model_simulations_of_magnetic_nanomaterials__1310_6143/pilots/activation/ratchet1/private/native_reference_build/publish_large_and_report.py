import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RATCHET = ROOT.parents[1]
TASK = RATCHET.parents[2]


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def verified_manifest(path):
    manifest = read(path)
    for relative, expected in manifest["sha256"].items():
        if digest(RATCHET / relative) != expected:
            raise RuntimeError(f"frozen artifact changed: {relative}")
    return manifest


initial_path = RATCHET / "private/reference/initial/manifest.json"
challenge_path = RATCHET / "private/challenge_pool/challenge/manifest.json"
initial_hash = digest(initial_path)
if initial_hash != read(ROOT / "initial_provenance.json")["manifest_sha256"]:
    raise RuntimeError("initial manifest changed since native certification")
initial = verified_manifest(initial_path)
challenge = verified_manifest(challenge_path)
previous_challenge_hash = digest(challenge_path)
extensions = []
for identifier in ["ratchet1_challenge_boundary_localized_90544001", "ratchet1_challenge_soft_interface_90544002"]:
    directory = ROOT / "challenge" / identifier
    record = read(directory / "manifest_record.json")
    validation = read(RATCHET / record["validation_file"])
    provenance = read(directory / "extension_provenance.json")
    if not validation["validated"] or validation["reference_runtime_seconds"] >= 90:
        raise RuntimeError("large native certification missing or outside runtime contract")
    if provenance["generator_sha256"] != digest(ROOT / "large_extension.py"):
        raise RuntimeError("large build generator changed after execution")
    for kind in ["case", "solution", "validation"]:
        if provenance[kind + "_sha256"] != digest(RATCHET / record[kind + "_file"]):
            raise RuntimeError("large artifact provenance mismatch")
    extensions.append(record)
existing = {record["case_id"] for record in challenge["cases"]}
for record in extensions:
    if record["case_id"] not in existing:
        challenge["cases"].append(record)
if len(initial["cases"]) != 6 or len(challenge["cases"]) != 5:
    raise RuntimeError("unexpected reference counts")
challenge["sha256"] = {record[name]: digest(RATCHET / record[name]) for record in challenge["cases"] for name in ["case_file", "solution_file", "validation_file"]}
challenge["additional_seed_stream"] = {"seeds": [90544001, 90544002], "n_spins": [3072, 4096], "parameter_ranges": "Same independent exchange/easy-anisotropy/field perturbations and boundary/interface modifications as the certified initial stream; no new interaction or mechanism."}
challenge["large_extension_completed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
temporary = challenge_path.with_name("manifest.pending.json")
write(temporary, challenge)
temporary.replace(challenge_path)
if digest(initial_path) != initial_hash:
    raise RuntimeError("initial manifest unexpectedly changed")
verified_manifest(initial_path)
verified_manifest(challenge_path)
provenance_path = ROOT / "challenge_provenance.json"
provenance = read(provenance_path)
provenance.setdefault("pre_large_extension_manifest_sha256", previous_challenge_hash)
provenance["manifest_sha256"] = digest(challenge_path)
provenance["large_extension_generator_sha256"] = digest(ROOT / "large_extension.py")
provenance["large_extension_report_generator_sha256"] = digest(Path(__file__))
provenance["artifact_sha256"] = {str(path.relative_to(RATCHET)): digest(path) for path in sorted((ROOT / "challenge").rglob("*")) if path.is_file()}
write(provenance_path, provenance)

selected = [(record["case_id"], read(RATCHET / record["validation_file"])) for record in initial["cases"] + challenge["cases"]]
certificates = [(str(path.relative_to(RATCHET)), read(path)) for split in ["initial", "challenge"] for path in sorted((ROOT / split).rglob("validation.json"))]
metrics = {
    "saddle_residual_meV": lambda data: data["saddle_residual_meV"],
    "minimum_A_residual_meV": lambda data: data["minimum_residual_meV"],
    "native_sparse_log_omega_error": lambda data: data["native_sparse_log_omega_error"],
    "hessian_fd_max_error_meV": lambda data: data["hessian_fd_max_error"],
    "native_barrier_absolute_difference_meV": lambda data: abs(data["native_barrier_meV"] - data["barrier_meV"]),
    "native_barrier_error_fraction_of_rounding_bound": lambda data: abs(data["native_barrier_meV"] - data["barrier_meV"]) / data["native_barrier_rounding_bound_meV"],
    "native_downhill_endpoint_max_distance": lambda data: max(min(branch["endpoint_distances"]) for branch in data["downhill_branches"]),
    "native_downhill_residual_meV": lambda data: max(branch["residual_meV"] for branch in data["downhill_branches"]),
    "native_dense_minimum_spectrum_max_error_meV": lambda data: data["dense_crosscheck"]["minimum_spectrum_max_error"],
    "native_dense_saddle_spectrum_max_error_meV": lambda data: data["dense_crosscheck"]["saddle_spectrum_max_error"],
}


def maxima(records):
    result = {}
    for name, function in metrics.items():
        values = []
        for identifier, data in records:
            try:
                values.append((float(function(data)), identifier))
            except (KeyError, TypeError):
                pass
        if values:
            maximum, identifier = max(values)
            result[name] = {"maximum": maximum, "case_or_certificate": identifier}
    return result


mechanisms = []
for identifier, data in selected:
    compared = data["competing_mechanisms"]
    if data["family"] != "coherent_control":
        barriers = {record["mechanism"]: record["barrier_meV"] for record in compared}
        mechanisms.append({"case_id": identifier, "family": data["family"], "right_minus_left_barrier_meV": barriers["right_nucleation"] - barriers["left_nucleation"]})
report = {"source_revision": initial["source_revision"], "initial_count": 6, "challenge_count": 5, "initial_manifest_unchanged_sha256": initial_hash, "challenge_manifest_sha256": digest(challenge_path), "selected_reference_maxima": maxima(selected), "all_native_certificate_maxima": maxima(certificates), "mechanism_comparisons": mechanisms, "minimum_positive_saddle_eigenvalue_meV": min(data["saddle_first_eigenvalues_meV"][1] for _, data in selected), "smallest_unstable_eigenvalue_magnitude_meV": min(abs(data["saddle_first_eigenvalues_meV"][0]) for _, data in selected), "minimum_barrier_over_kBT_at_0p5K": min(data["barrier_over_kBT_at_0p5K"] for _, data in selected), "reference_runtime_seconds_max": max(data["reference_runtime_seconds"] for _, data in selected), "large_cases": [{"case_id": identifier, "n_spins": data["n_spins"], "reference_runtime_seconds": data["reference_runtime_seconds"], "native_sparse_htst_seconds": data["stage_seconds"]["native_sparse_htst"], "peak_rss_kib": data["peak_rss_kib_process"]} for identifier, data in selected if data["n_spins"] >= 3072], "physical_caveats": ["Warm localized continuation and three-image native saddle refinement, not equal-budget cold global path search.", "Lowest among compared native-certified mechanisms, not an exhaustive global-minimum proof.", "No zero modes in stored cases; no zero-mode-volume or general symmetry-degenerate rate treatment is tested.", "Close boundary channels can both contribute to physical escape rates; output is the selected saddle's fluctuation factor, not a summed dynamical rate.", "Cartesian tensors avoid the pinned rotated-anisotropy native Hessian defect; no upstream patch and no rotated native HTST claim.", "Float32 native getters limit scalar energy and returned spectrum comparisons; total-energy rounding bounds are retained without tightening physical tolerances."], "no_fresh_agent_launch": True, "no_initial_reference_changes": True}
write(ROOT / "native_error_report.json", report)
frozen = {**initial["sha256"], **challenge["sha256"], str(initial_path.relative_to(RATCHET)): initial_hash, str(challenge_path.relative_to(RATCHET)): digest(challenge_path)}
write(ROOT / "frozen_reference_hashes.json", {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_revision": initial["source_revision"], "sha256": frozen})

lines = ["# Native reference handoff: READY and frozen", "", "Six initial and five challenge cases are certified. The six initial case/solution/validation files and manifest are unchanged; only two newly seeded challenge cases were appended. No public, grader or upstream implementation is modified.", "", "## Source and runtime", "", f"Spirit revision: `{initial['source_revision']}`.", f"Native library SHA256: `{digest(TASK / 'authoring/spirit/core/python/spirit/libSpirit.so')}`.", "", "The original nine builds use `build.py`; the two largest use `large_extension.py`. The latter reuses one native state, certifies both mechanisms, then calculates full-size native sparse HTST only for the lower saddle. Both mechanisms also receive matching N128 native dense/sparse checks. This removes duplicate work, not a scientific check on the selected reference. Total warm time includes small calibration, preparation, both GNEB saddles, independent spectra/FD, four downhill descents and selected native HTST. All runs impose2GiB; the two largest also have external90s timeouts.", ""]
for data in report["large_cases"]:
    lines.append(f"- N{data['n_spins']}: {data['reference_runtime_seconds']:.9f}s total; sparse HTST {data['native_sparse_htst_seconds']:.9f}s; peak RSS {data['peak_rss_kib']}KiB.")
lines += ["", "## Exact maximum errors", "", "Values are binary64 results printed to17 significant digits. The machine-readable report identifies every maximizer. 'All certificates' also includes small calibrations and competing mechanisms; missing full-size HTST for a higher large-case competitor is not treated as a zero error.", "", "| Metric | Selected11 references | All native certificates |", "|---|---:|---:|"]
for name in metrics:
    selected_maximum = report["selected_reference_maxima"].get(name, {}).get("maximum")
    all_maximum = report["all_native_certificate_maxima"].get(name, {}).get("maximum")
    lines.append(f"| {name} | {selected_maximum:.17g} | {all_maximum:.17g} |")
lines += ["", "The native Python getters use `ctypes.c_float` for energies, HTST scalars and returned eigenvalues even with the double engine. Full dense-spectrum discrepancies are therefore reported at getter precision. Native barrier differences are bounded using float32 total-energy rounding; all observed differences remain inside that bound. Full output spectra and cancellation-resistant barrier sums use double precision. Native LLG's stopping metric is not asserted to equal the independently recomputed maximum Cartesian tangent norm; both measured downhill residuals and final endpoint distances are reported above.", "", "## Mechanisms and scientific caveats", ""]
for item in mechanisms:
    lines.append(f"- `{item['case_id']}`: right-minus-left barrier = {item['right_minus_left_barrier_meV']:.17g}meV; both saddles have native GNEB and distinct-basin descents.")
lines += ["", f"All stored saddles have exactly one negative mode and no zero modes. The smallest positive saddle eigenvalue is {report['minimum_positive_saddle_eigenvalue_meV']:.17g}meV; the smallest unstable magnitude is {report['smallest_unstable_eigenvalue_magnitude_meV']:.17g}meV. Minimum barrier/kBT at0.5K is {report['minimum_barrier_over_kBT_at_0p5K']:.17g}.", "", "Coherent controls also have two cold21-image native GNEB paths that recover the same saddle. Long-chain references use trusted localized continuation, independently refined on the full chain. This is a warm author-reference construction, not a cold global-search timing claim. Left/right comparisons include the close boundary barriers, but do not prove global optimality over every possible saddle. Close channels can both matter to a physical escape rate; the contract deliberately reports one selected saddle and its static Omega0, not a sum over channels or a full dynamical/experimental rate. No zero-mode-volume, quantum correction or rotated-native-Hessian capability is claimed.", "", "## Freeze and reproduction", "", "`frozen_reference_hashes.json` covers all33 case/solution/validation files plus both manifests. `native_error_report.json` contains exact maxima and case identifiers. Existing build-time source hashes are retained in split provenance; extension provenance records new seeds90544001/90544002 and independently changed exchange, easy anisotropy, fields and boundary/interface parameters within the existing ranges.", "", "Use pinned `authoring/python_runtime` on PYTHONPATH and single-thread BLAS/OpenMP. Rebuild commands are `python -B private/native_reference_build/build.py --split initial`, `--split challenge`, then `python -B private/native_reference_build/large_extension.py boundary_localized` and `soft_interface`, then the append/report script. Do not rerun builders against frozen directories during grading. Historical `handoff.json` records the pre-extension9-case state; this report and current manifests supersede its counts.", "", "No active authoring jobs or fresh agent launches remain when this report is published. Main owns independent auditing, scorer calibration and agent launch."]
(ROOT / "FINAL_NATIVE_REPORT.md").write_text("\n".join(lines) + "\n")
print("READY: initial6 unchanged; challenge5 certified and hashed; final native report and35-file freeze snapshot written", flush=True)
