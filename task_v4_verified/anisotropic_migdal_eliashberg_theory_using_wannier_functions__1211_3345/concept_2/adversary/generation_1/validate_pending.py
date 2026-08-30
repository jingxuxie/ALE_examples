import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np

from prepare_pending import PENDING, ROOT, SELECTED, hashes, json_write, protected_state, text_patch


def reporting_checks(result):
    assert isinstance(result["reason"], str) and result["reason"]
    assert np.isfinite(result["score"])
    assert result["score"] == result["core_score"] == result["worst_family_score"]
    assert "Minimum" in result["score_definition"]
    assert result["resources"]["wall_seconds"] >= 0
    assert result["resources"]["cpu_seconds"] >= 0
    assert result["resources"]["peak_rss_kib"] > 0


def save_pair(path, kernels, extra=False):
    with path.open("wb") as stream:
        if extra:
            np.savez_compressed(stream, kernels=kernels, extra=np.zeros(1))
        else:
            np.savez_compressed(stream, kernels=kernels)


def main():
    started = time.monotonic()
    validation = PENDING / "validation"
    artifacts = validation / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PENDING / "package_manifest.json").read_text())
    before = protected_state()
    assert before == manifest["protected_active_before"]
    assert hashes(PENDING / "participant") == manifest["public"]
    for filename in ("config.json", "reference.npz", "FORMAT.md"):
        public_bytes = (PENDING / "participant/input" / filename).read_bytes()
        assert public_bytes == (PENDING / "input" / filename).read_bytes()
        if filename != "FORMAT.md":
            assert public_bytes == (SELECTED / "input" / filename).read_bytes()
            assert public_bytes == (PENDING / "evaluator/hidden/frozen_input" / filename).read_bytes()
    for filename in ("_physics.py", "_audit.py"):
        assert (PENDING / "evaluator" / filename).read_bytes() == (PENDING / "archived_originals/evaluator" / filename).read_bytes()
    for relative in ("participant/TASK.md", "input/FORMAT.md", "evaluator/evaluate.py", "status.json"):
        assert (PENDING / relative).is_file()
    assert not any(path.is_symlink() for path in (PENDING / "participant").rglob("*"))
    sys.path.insert(0, str(PENDING / "evaluator"))
    spec = importlib.util.spec_from_file_location("pending_evaluator", PENDING / "evaluator/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from _physics import EliashbergSolver, load_instance
    instance = load_instance(PENDING / "evaluator/hidden/frozen_input")
    assert instance["config"]["target_ratio"] == 1.09
    results = {}

    def evaluate(name, path, expected_admissible, expected_valid):
        destination = validation / name
        result = module.evaluate(path, destination.with_suffix(".json"), destination.with_suffix(".audit.json"))
        reporting_checks(result)
        assert result["admissible"] == expected_admissible, (name, result)
        assert result["valid"] == expected_valid, (name, result)
        results[name] = result
        print(json.dumps({"case": name, "score": result["score"], "admissible": result["admissible"],
                          "valid": result["valid"], "reason": result["reason"]}), flush=True)
        return result

    baseline = artifacts / "baseline.npz"
    subprocess.run([sys.executable, "-B", str(PENDING / "participant/baseline/solve.py"),
                    "--output", str(baseline)], check=True)
    baseline_result = evaluate("baseline", baseline, True, False)
    assert baseline_result["score"] == 1.0
    private = PENDING / "evaluator/hidden/witness.npz"
    private_result = evaluate("private_witness", private, True, True)
    assert abs(private_result["score"] - 1.094955838159416) < 1e-10
    oracle = PENDING / "family_oracle/middle_cross_45/best_combined_witness.npz"
    oracle_result = evaluate("champion_oracle", oracle, True, False)
    assert abs(oracle_result["score"] - 1.0877026333364312) < 1e-10
    assert private_result["converged"] and private_result["independent_audit_passed"]
    assert oracle_result["converged"] and oracle_result["independent_audit_passed"]
    shutil.copy2(validation / "private_witness.json", PENDING / "evaluator/hidden/witness_result.json")
    shutil.copy2(validation / "private_witness.audit.json", PENDING / "evaluator/hidden/witness_audit.json")
    with np.load(baseline, allow_pickle=False) as archive:
        repeated = np.array(archive["kernels"], copy=True)
    malformed = {}
    malformed["shape"] = repeated[0]
    malformed["nonfinite"] = repeated.copy()
    malformed["nonfinite"][0, 0, 0, 0] = np.nan
    malformed["asymmetric"] = repeated.copy()
    malformed["asymmetric"][0, 0, 0, 1] += .01
    malformed["diagonal"] = repeated.copy()
    malformed["diagonal"][0, 0, 0, 0] += .01
    malformed["bounds"] = repeated.copy()
    malformed["bounds"][0, 0, 0, 0] = 10.
    malformed["static"] = repeated.copy()
    for first, second, sign in ((0, 1, 1), (1, 2, -1), (2, 3, 1), (3, 0, -1)):
        malformed["static"][0, 0, first, second] += sign * .01
        malformed["static"][0, 0, second, first] += sign * .01
    malformed["row_sums"] = repeated.copy()
    for mode, sign in ((0, 1), (1, -1)):
        malformed["row_sums"][0, mode, 0, 1] += sign * .01
        malformed["row_sums"][0, mode, 1, 0] += sign * .01
    malformed["object_dtype"] = repeated.astype(object)
    for name, kernels in malformed.items():
        path = artifacts / (name + ".npz")
        save_pair(path, kernels)
        evaluate(name, path, False, False)
    extra = artifacts / "extra_key.npz"
    save_pair(extra, repeated, extra=True)
    evaluate("extra_key", extra, False, False)
    evaluate("missing", artifacts / "not_present.npz", False, False)
    bad_zip = artifacts / "bad_zip.npz"
    bad_zip.write_bytes(b"not a zip archive")
    evaluate("bad_zip", bad_zip, False, False)
    oversize = artifacts / "oversize.npz"
    with oversize.open("wb") as stream:
        stream.truncate(instance["config"]["max_artifact_bytes"] + 1)
    evaluate("oversize", oversize, False, False)
    expanded = artifacts / "expanded_zip.npz"
    with zipfile.ZipFile(expanded, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("kernels.npy", bytes(instance["config"]["max_uncompressed_bytes"] + 1))
    evaluate("expanded_zip", expanded, False, False)
    header_buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(header_buffer, {
        "descr": "<f8", "fortran_order": False, "shape": (2, 3, 1000000000, 8),
    })
    bomb = artifacts / "oversize_header.npz"
    with zipfile.ZipFile(bomb, "w") as archive:
        archive.writestr("kernels.npy", header_buffer.getvalue())
    evaluate("oversize_header", bomb, False, False)
    symlink = artifacts / "symlink.npz"
    try:
        symlink.symlink_to(private)
        evaluate("symlink", symlink, False, False)
    finally:
        symlink.unlink(missing_ok=True)
    hardlink_source = artifacts / "hardlink_source.npz"
    shutil.copy2(baseline, hardlink_source)
    hardlink = artifacts / "hardlink.npz"
    try:
        os.link(hardlink_source, hardlink)
        evaluate("hardlink", hardlink, False, False)
    finally:
        hardlink.unlink(missing_ok=True)
        hardlink_source.unlink(missing_ok=True)
    directory_link = validation / "linked_directory"
    try:
        directory_link.symlink_to(artifacts, target_is_directory=True)
        evaluate("symlink_component", directory_link / "baseline.npz", False, False)
    finally:
        directory_link.unlink(missing_ok=True)
    public_output = validation / "public_check.json"
    public = subprocess.run([sys.executable, "-B", "workspace/check.py", str(private),
                             "--output", str(public_output)], cwd=PENDING / "participant",
                            text=True, capture_output=True, check=True)
    (validation / "public_check.stdout.log").write_text(public.stdout)
    public_result = json.loads(public_output.read_text())
    assert public_result["public_pass"] and public_result["admissible"]
    assert abs(public_result["score"] - private_result["score"]) < 1e-10
    with np.load(private, allow_pickle=False) as archive:
        pair = np.array(archive["kernels"], copy=True)
    nominal_solver = EliashbergSolver(instance["weights"], instance["row_sums"], instance["energies_mev"], instance["config"])
    nominal = [nominal_solver.critical_temperature(modes, 192)["tc_kelvin"] for modes in pair]
    high_index = int(np.argmax(nominal))
    extension = []
    for family in instance["config"]["families"]:
        energies = instance["energies_mev"] * np.asarray(family["energy_factors"])
        solver = EliashbergSolver(instance["weights"], instance["row_sums"], energies, instance["config"])
        temperatures = [solver.critical_temperature(modes, 384)["tc_kelvin"] for modes in pair]
        ratio = temperatures[high_index] / temperatures[1 - high_index]
        assert ratio >= 1.09
        extension.append({"family": family["name"], "positive_count": 384,
                          "temperatures_kelvin": temperatures, "ratio": ratio})
    json_write(validation / "extended_refinement.json", {
        "purpose": "Additional private evidence only; the published finite-grid numerical contract is unchanged.",
        "families": extension, "all_above_target": True,
    })
    assert before == protected_state()
    assert hashes(PENDING / "participant") == manifest["public"]
    summary = {
        "passed": True,
        "evaluated_cases": len(results),
        "negative_security_and_constraint_cases": len(results) - 3,
        "baseline": baseline_result,
        "private_witness": private_result,
        "champion_oracle": oracle_result,
        "public_check_matches_private": True,
        "all_family_384_private_margin_confirmed": True,
        "participant_has_no_symlinks": True,
        "active_package_unchanged": True,
        "wall_seconds": time.monotonic() - started,
        "no_fresh_model_launched": True,
    }
    json_write(validation / "summary.json", summary)
    manifest["trusted_evaluator"] = hashes(PENDING / "evaluator")
    manifest["compatibility_input"] = hashes(PENDING / "input")
    manifest["protected_active_after"] = protected_state()
    manifest["validated"] = True
    manifest["input_sha256"] = private_result["input_sha256"]
    manifest["validation_summary_sha256"] = hashlib.sha256((validation / "summary.json").read_bytes()).hexdigest()
    json_write(PENDING / "package_manifest.json", manifest)
    status = json.loads((PENDING / "status.json").read_text())
    status.update({
        "status": "ready_for_parent_review",
        "ready_for_parent_review": True,
        "ready_for_new_fresh_attempts": False,
        "parent_promotion_required": True,
        "recommended_for_promotion": False,
        "hardness_warning": "A new two-parameter interpolation search passes at 1.094290457685765 in 8.62 CPU seconds; the validated n=8 draft is not recommended as strong hardness evidence.",
        "input_sha256": private_result["input_sha256"],
        "baseline": baseline_result,
        "private_witness_result": private_result,
        "champion_oracle_result": oracle_result,
        "validation_summary": "validation/summary.json",
        "reason": "Pending package validated: private witness passes, stronger actual-champion endpoint oracle is admissible but misses the pre-fixed target. Parent review/promotion required before any fresh launch.",
    })
    json_write(PENDING / "status.json", status)
    text_patch(PENDING / "READY.md", """# Ready for parent review; not promoted

**Hardness warning:** a new two-parameter interpolation search passes at 1.094290457685765 in 8.62 CPU seconds. The n=8 draft is validated but not recommended as a hard ratchet; see `DECISION.md` and the separate `large_patch_probe/` follow-up before promoting anything.

- Pending public package: `participant/`; trusted checker: `evaluator/evaluate.py`; compatibility format: `input/FORMAT.md`.
- Frozen target: **1.09**, selected using private evidence before replay; same n=8, three-mode row/diagonal/static constraints.
- Baseline: admissible, score **1.0**, not valid.
- Private witness: **1.094955838159416**, valid, saved with independent signed-frequency and regular-row audits in `evaluator/hidden/`.
- Actual champion over every family, including cross-combination of every produced endpoint: **1.0877026333364312**, admissible and independently audited, not valid.
- Exact package validation and hostile-artifact probes: `validation/summary.json`; additional all-family M=384 private check: `validation/extended_refinement.json`.
- `DECISION.md` states the scientific interpretation, empirical gap, unchanged original contracts, reporting-only regression, and risk of an easy minimax-aware fresh solution.
- Active `concept_2/participant`, `evaluator`, and `status.json` are unchanged. No fresh launch or promotion occurred. Parent alone decides whether to promote this proposal.
""")
    print(json.dumps({"ready_for_parent_review": True, "target_ratio": 1.09,
                      "baseline_score": baseline_result["score"], "private_score": private_result["score"],
                      "champion_oracle_score": oracle_result["score"], "negative_cases": len(results) - 3,
                      "active_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
