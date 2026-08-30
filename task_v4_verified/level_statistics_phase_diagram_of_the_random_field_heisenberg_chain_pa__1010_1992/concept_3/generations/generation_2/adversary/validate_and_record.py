import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
GENERATION_ONE = ROOT.parent.parent
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np
import scipy
import exact
import evaluate


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_report(report):
    required = {"core_score", "worst_family_score", "passed", "valid", "evaluator_valid",
                "reason", "resource_score", "runtime_seconds", "resource"}
    assert required <= set(report)
    assert report["core_score"] == report["core"]
    assert report["worst_family_score"] == report["worst_family"]
    assert report["passed"] == report["pass"]
    assert report["runtime_seconds"] == report["resource"]["wall_seconds"]
    assert "members" not in report


def run_evaluator(witness, output, cwd=None):
    environment = os.environ.copy()
    if cwd is not None:
        environment["PYTHONPATH"] = str(cwd)
    process = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "evaluator" / "evaluate.py"),
                              str(witness), "--output", str(output)],
                             capture_output=True, text=True, timeout=200, env=environment, cwd=cwd)
    if process.returncode:
        raise AssertionError(process.stderr)
    report = json.loads(process.stdout)
    assert report == load(output)
    check_report(report)
    return report


def vector_set(protocol):
    return {tuple(offset) for family in protocol["families"] for offset in family["offsets"]}


def summary(report):
    return {"core_score": report["core"], "worst_family_score": report["worst_family"],
            "valid": report["valid"], "passed": report["pass"], "reason": report["reason"]}


def main():
    started = time.monotonic()
    commitment = load(ROOT / "participant" / "input" / "commitment.json")
    public = load(ROOT / "participant" / "input" / "protocol.json")
    private = load(ROOT / "evaluator" / "hidden" / "protocol.json")
    seeds = load(ROOT / "adversary" / "seed_manifest.json")
    assert fingerprint(ROOT / "evaluator" / "hidden" / "protocol.json") == commitment["private_protocol_sha256"]
    assert fingerprint(ROOT / "participant" / "input" / "protocol.json") == commitment["public_protocol_sha256"]
    assert commitment == load(ROOT / "evaluator" / "hidden" / "commitment.json")
    assert seeds["public_seed_hex"] != seeds["private_seed_hex"]
    assert len(seeds["private_seed_hex"]) == 64 and seeds["generated_before_any_scoring"]
    exact.validate_protocol(public)
    exact.validate_protocol(private)
    public_vectors, private_vectors = vector_set(public), vector_set(private)
    assert len(public_vectors) == len(private_vectors) == 128
    assert not public_vectors.intersection(private_vectors)
    old_vectors = vector_set(load(GENERATION_ONE / "participant" / "input" / "protocol.json"))
    for old in load(GENERATION_ONE / "adversary" / "private_replication_protocols.json"):
        old_vectors.update(vector_set(old))
    assert not old_vectors.intersection(public_vectors | private_vectors)
    primary_files = [path for directory in ("participant", "evaluator")
                     for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    for path in primary_files:
        if path.suffix == ".py":
            ast.parse(path.read_text(), filename=str(path))
        if "participant" in path.relative_to(ROOT).parts:
            assert seeds["private_seed_hex"].encode() not in path.read_bytes()
    task_words = len((ROOT / "participant" / "TASK.md").read_text().split())
    assert 200 <= task_words <= 300, task_words
    assert (ROOT / "participant" / "workspace" / "exact.py").read_bytes() == (ROOT / "evaluator" / "hidden" / "exact.py").read_bytes()
    baseline_path = ROOT / "adversary" / "baseline_witness.json"
    reference_path = ROOT / "adversary" / "privileged_reference" / "witness.json"
    print("Scoring baseline and unchanged old privileged reference on the committed private bank.", flush=True)
    baseline = run_evaluator(baseline_path, ROOT / "adversary" / "baseline_private_report.json")
    reference = run_evaluator(reference_path, ROOT / "adversary" / "privileged_reference" / "private_report.json")
    for report in (baseline, reference):
        assert report["evaluator_valid"] and report["protocol_commitment_verified"]
        assert report["protocol_sha256"] == commitment["private_protocol_sha256"]
        if report["valid"]:
            assert report["resource"]["diagonalizations"] == 129 and report["resource_score"] == 1.0
        assert seeds["private_seed_hex"] not in json.dumps(report)
    reference_witness = load(reference_path)
    reference_public = exact.assess(reference_witness, public)
    save(ROOT / "adversary" / "privileged_reference" / "public_report.json", reference_public)
    controls = ROOT / "adversary" / "controls"
    outputs = controls / "reports"
    outputs.mkdir(exist_ok=True)
    invalid = {
        "empty_object": "{}",
        "extra_score": json.dumps({**reference_witness, "core_score": 1.0}),
        "code_payload": json.dumps({**reference_witness, "code": "__import__('os').system('false')"}),
        "bool_orientation": json.dumps({**reference_witness, "orientation": True}),
        "float_version": json.dumps({**reference_witness, "schema_version": 1.0}),
        "short_fields": json.dumps({**reference_witness, "fields": [0.0] * 10}),
        "zero_fields": json.dumps({**reference_witness, "fields": [0.0] * 12}),
        "bool_field": json.dumps({**reference_witness, "fields": [False] + reference_witness["fields"][1:]}),
        "duplicate_key": '{"fields":[],"fields":[],"schema_version":1,"orientation":1}',
        "nan": '{"fields":[NaN],"schema_version":1,"orientation":1}',
        "oversized": " " * 16385,
        "malformed": "not JSON"
    }
    rejected = []
    for name, contents in invalid.items():
        path = controls / (name + ".json")
        path.write_text(contents)
        report = run_evaluator(path, outputs / (name + ".json"))
        assert not report["valid"] and not report["passed"] and report["evaluator_valid"], name
        assert report["resource"]["diagonalizations"] == 0 and report["resource_score"] == 0.0
        rejected.append(name)
    sidecar_path = controls / "sidecars" / "witness.json"
    sidecar_path.write_text("{}")
    sidecar_report = run_evaluator(sidecar_path, outputs / "sidecars_ignored.json", cwd=sidecar_path.parent)
    assert sidecar_report["evaluator_valid"] and not sidecar_report["valid"]
    rejected.append("sidecars_ignored")
    link = controls / "linked.json"
    link.symlink_to(reference_path)
    linked = run_evaluator(link, outputs / "symlink.json")
    link.unlink()
    assert linked["evaluator_valid"] and not linked["valid"] and linked["resource"]["diagonalizations"] == 0
    rejected.append("symlink")
    directory = run_evaluator(controls, outputs / "directory.json")
    assert directory["evaluator_valid"] and not directory["valid"] and directory["resource"]["diagonalizations"] == 0
    rejected.append("directory")
    tampered = controls / "tampered_evaluator"
    (tampered / "hidden").mkdir(parents=True, exist_ok=True)
    save(tampered / "hidden" / "protocol.json", public)
    save(tampered / "hidden" / "commitment.json", commitment)
    trusted_root = evaluate.ROOT
    evaluate.ROOT = tampered
    try:
        mismatch = evaluate.evaluate(reference_path)
        check_report(mismatch)
        assert not mismatch["evaluator_valid"] and not mismatch["valid"]
        assert mismatch["resource"]["diagonalizations"] == 0 and not mismatch["protocol_commitment_verified"]
        save(outputs / "commitment_mismatch.json", mismatch)
        changed_commitment = {**commitment, "private_protocol_sha256": fingerprint(tampered / "hidden" / "protocol.json")}
        save(tampered / "hidden" / "commitment.json", changed_commitment)
        fallback = evaluate.evaluate(reference_path)
        check_report(fallback)
        assert not fallback["evaluator_valid"] and fallback["resource"]["diagonalizations"] == 0
        save(outputs / "public_bank_rejected_as_grading.json", fallback)
    finally:
        evaluate.ROOT = trusted_root
    fields = np.asarray(reference_witness["fields"])
    samples = [fields] + [family["scale"] * fields + np.asarray(family["offsets"][0]) for family in private["families"]]
    lapack = []
    for index, profile in enumerate(samples):
        energies_evr = exact.spectrum(profile, driver="evr")
        energies_evd = exact.spectrum(profile, driver="evd")
        statistics_evr, statistics_evd = exact.proxy_statistics(energies_evr), exact.proxy_statistics(energies_evd)
        eigen_error = float(np.max(np.abs(energies_evr - energies_evd)))
        statistic_error = max(abs(statistics_evr[key] - statistics_evd[key]) for key in ("rank_r", "proxy_r", "difference"))
        assert eigen_error < 1e-10 and statistic_error < 1e-8
        lapack.append({"sample": index, "eigenvalue_max_error": eigen_error, "statistic_max_error": statistic_error})
    ladder = exact.proxy_statistics(np.arange(924, dtype=float))
    assert ladder["rank_r"] == ladder["proxy_r"] == 1.0 and ladder["rank_ratio_count"] == 306
    assert [window["nearest_rank"] for window in ladder["windows"]] == [452, 461, 471]
    assert all(window["ratio_count"] == 126 for window in ladder["windows"])
    assert fingerprint(ROOT / "evaluator" / "hidden" / "protocol.json") == commitment["private_protocol_sha256"]
    baseline_public = load(ROOT / "adversary" / "baseline_witness.search.json")
    validation = {"passed": True, "task_words": task_words, "controls": rejected,
                  "invalid_static_controls": len(rejected), "commitment_mismatch_rejected": True,
                  "public_bank_rejected_as_grading": True, "banks_disjoint_from_each_other_and_old_cases": True,
                  "private_seed_bits": 256, "private_seed_absent_from_participant_and_reports": True,
                  "private_seed_generated_by_secrets_token_hex": True, "aliases_checked_including_errors": True,
                  "lapack_samples": lapack, "window_indexing_check": True,
                  "public_private_helper_identical": True, "seconds": time.monotonic() - started,
                  "python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
                  "baseline_private": summary(baseline), "old_privileged_private": summary(reference)}
    save(ROOT / "adversary" / "validation.json", validation)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest = {"prepared_at_utc": timestamp, "main_owns_final_freeze": True,
                "private_protocol_sha256": commitment["private_protocol_sha256"],
                "sha256": {str(path.relative_to(ROOT)): fingerprint(path) for path in sorted(primary_files)}}
    save(ROOT / "ready_manifest.json", manifest)
    status = {"schema_version": 1, "concept": "concept_3", "generation": 2, "ratchet": 1,
              "mode": "B", "task_type": "COUNTEREXAMPLE/FALSIFICATION", "claim_id": "C3-G2-v1",
              "status": "ready_for_main_freeze_and_launch", "valid_package": True, "frozen": False,
              "freeze_owner": "main_runner", "criteria_fixed": True, "probe_banks_committed": True,
              "prepared_at_utc": timestamp, "primary_targets": public["targets"],
              "families": 4, "members_per_family": 32, "public_perturbations": 128, "private_perturbations": 128,
              "commitment": commitment, "public_protocol": "participant/input/protocol.json",
              "private_protocol": "evaluator/hidden/protocol.json", "exact_protocol": "participant/input/PROTOCOL.md",
              "evaluator_command": "python -I -B evaluator/evaluate.py WITNESS_JSON --output REPORT_JSON",
              "resource_limits": {"participant_seconds": 3600, "generator_workers_max": 8, "blas_threads": 1,
                                  "evaluator_seconds": 180, "evaluator_workers": 1, "evaluator_address_space_bytes": 2147483648,
                                  "diagonalizations": 129, "witness_byte_limit": 16384},
              "baseline": {"source": "original PUBLIC unstructured search", "public": summary(baseline_public),
                           "private": summary(baseline), "witness": "adversary/baseline_witness.json",
                           "evaluation": "adversary/baseline_private_report.json", "reference_seeded": False},
              "old_privileged_reference": {"public": summary(reference_public), "private": summary(reference),
                                           "witness": "adversary/privileged_reference/witness.json",
                                           "evaluation": "adversary/privileged_reference/private_report.json", "fresh_champion": False},
              "g2_passing_witness_established": bool(baseline["pass"] or reference["pass"]),
              "stronger_reference_search": "not_run; no delay for a new solution",
              "solvability": "passing_reference_available" if baseline["pass"] or reference["pass"] else "open; no passing generation-two witness established",
              "validation": {"report": "adversary/validation.json", "passed": True,
                             "invalid_static_controls": len(rejected), "lapack_sample_count": len(lapack),
                             "max_lapack_statistic_error": max(row["statistic_max_error"] for row in lapack),
                             "commitment_error_distinguished_from_invalid_input": True},
              "privacy": {"expose_only": "participant", "private_seed_bits": 256,
                          "previous_fresh_code_or_witness_in_participant": False,
                          "private_cases_or_seed_in_participant": False, "detailed_private_members_in_report": False},
              "ready_manifest": "ready_manifest.json", "private_records": "adversary",
              "fresh_agents_launched": 0, "original_tree_modified": False,
              "all_writes_within": "concept_3/generations/generation_2"}
    save(ROOT / "status.json", status)
    report = f"""# Generation-two private author report

All writes are confined to concept_3/generations/generation_2. No fresh
agents were launched and no previous fresh solver or witness was copied.
The baseline derives only from the original PUBLIC unstructured-search code.
The unchanged initial privileged author witness is retained privately as a
reference, not a fresh champion.

## Independent replication

Four families now have 32 members each. Required coverage is 24/32 (75%).
The numeric core, worst-family, base, and member-floor targets remain
0.060, 0.050, 0.055, and 0.025. Public and private banks have different
independent 256-bit OS-entropy seeds. Both were fixed and the private bank
committed before any scoring. No bank was resampled or selected by scores.
Private protocol SHA-256: `{commitment['private_protocol_sha256']}`.

## Recorded scores

| Witness | Bank | Core | Worst family | Valid | Pass |
|---|---|---:|---:|---|---|
| Unstructured baseline | Public | {baseline_public['core']:.12f} | {baseline_public['worst_family']:.12f} | {baseline_public['valid']} | {baseline_public['pass']} |
| Unstructured baseline | Private | {baseline['core']} | {baseline['worst_family']} | {baseline['valid']} | {baseline['pass']} |
| Old privileged reference | Public | {reference_public['core']:.12f} | {reference_public['worst_family']:.12f} | {reference_public['valid']} | {reference_public['pass']} |
| Old privileged reference | Private | {reference['core']} | {reference['worst_family']} | {reference['valid']} | {reference['pass']} |

Generation-two solvability status: {status['solvability']}. No stronger-witness
search was run; no reference-solution search delays readiness.

## Validation and resources

{len(rejected)} malformed/static controls passed, plus separate checks for
commitment mismatch and rejection of a public bank as grading data. Both
commitment faults return evaluator_valid=false, whereas invalid witnesses
return evaluator_valid=true and valid=false. All report aliases were checked.
The evaluator does not expose private per-member diagnostics or seeds.

Independent evr/evd checks covered the base and one member per family:
maximum statistic disagreement {max(row['statistic_max_error'] for row in lapack):.3g}.
Private evaluations took {baseline['runtime_seconds']:.3f} seconds for the
baseline and {reference['runtime_seconds']:.3f} seconds for the old reference.
The 180-second limit is retained for 129 full spectra with one worker and
one BLAS thread; the memory ceiling remains 2 GiB.

The main runner owns final package freeze and launch. ready_manifest.json
hashes all participant/evaluator assets. The private seed, old reference,
ratchet stress summary, and all validation artifacts stay under adversary/
or evaluator/hidden/, never in the tested participant bundle.
"""
    (ROOT / "adversary" / "REPORT.md").write_text(report)
    print(json.dumps({"status": status["status"], "private_protocol_sha256": commitment["private_protocol_sha256"],
                      "baseline_public": summary(baseline_public), "baseline_private": summary(baseline),
                      "old_privileged_public": summary(reference_public), "old_privileged_private": summary(reference),
                      "validation_passed": True, "invalid_static_controls": len(rejected),
                      "max_lapack_statistic_error": max(row["statistic_max_error"] for row in lapack),
                      "private_runtimes_seconds": [baseline["runtime_seconds"], reference["runtime_seconds"]],
                      "solvability": status["solvability"]}, indent=2))


if __name__ == "__main__":
    main()
