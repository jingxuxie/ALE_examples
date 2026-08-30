import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

from collections import Counter
import json
from pathlib import Path
import time
import zipfile

import numpy as np

from focused_search import CONCEPT, FAMILIES, OLD, ROOT, atomic_json, concept_path, read_json, stamp, validate_request
from harness import load_mps, measure, sha256, write_json
from trusted_contractor import local_operators


def main():
    started = time.monotonic()
    proposal = read_json(ROOT / "PROPOSAL.json")
    prior_manifests = {}
    for tranche in ("tranche_1", "tranche_2"):
        manifest_path = OLD / tranche / "ARTIFACT_MANIFEST.json"
        entries = read_json(manifest_path)
        mismatches = [relative for relative, entry in entries.items()
                      if sha256(OLD / relative) != entry["sha256"]]
        assert not mismatches, mismatches
        prior_manifests[tranche] = {"path": concept_path(manifest_path), "sha256": sha256(manifest_path),
                                    "entries_verified_unchanged": len(entries)}
    sources = read_json(ROOT / "SOURCE_HASHES.json")
    for relative, expected in sources.items():
        assert sha256(ROOT / relative) == expected, relative
    allocation_sources = read_json(ROOT / "ALLOCATION_SOURCE_HASHES.json") if (ROOT / "ALLOCATION_SOURCE_HASHES.json").exists() else {}
    for relative, expected in allocation_sources.items():
        assert sha256(ROOT / relative) == expected, relative
    quota_sources = read_json(ROOT / "QUOTA_SOURCE_HASHES.json") if (ROOT / "QUOTA_SOURCE_HASHES.json").exists() else {}
    for relative, expected in quota_sources.items():
        assert sha256(ROOT / relative) == expected, relative
    origins = read_json(ROOT / "SOURCE_ORIGINS.json")
    for relative, entry in origins.items():
        assert sha256(ROOT / relative) == entry["sha256"] == sha256(Path(entry["copied_from"])), relative
    previous_origins = read_json(OLD / "SOURCE_ORIGINS.json")
    for relative, entry in previous_origins.items():
        assert sha256(ROOT / relative) == entry["snapshot_sha256"], relative

    operator_errors = []
    operator_parameters = sorted({(record["request"]["local_dim"], omega)
                                  for record in proposal["cases"] for omega in record["request"]["omega"]})
    for dimension, omega in operator_parameters:
        padded = dimension + 8
        lowering = np.diag(np.sqrt(np.arange(1, padded)), 1)
        position = (lowering + lowering.T) / np.sqrt(2 * omega)
        momentum = -1j * np.sqrt(omega / 2) * (lowering - lowering.T)
        independent = {"q": position, "q2": position @ position,
                       "q4": np.linalg.matrix_power(position, 4), "p2": momentum @ momentum}
        trusted = local_operators(dimension, omega)
        discrepancies = {key: float(np.max(np.abs(trusted[key] - matrix[:dimension, :dimension])))
                         for key, matrix in independent.items()}
        assert max(discrepancies.values()) < 1e-10
        operator_errors.append({"dimension": dimension, "omega": omega, "errors": discrepancies,
                                "naive_projected_q_fourth_power_disagreement":
                                float(np.max(np.abs(np.linalg.matrix_power(trusted["q"], 4) - trusted["q4"])))})

    runs = []
    for result_path in sorted((ROOT / "runs").glob("*/*/result.json")):
        result = read_json(result_path)
        request = read_json(result_path.parent / "request.json")
        validate_request(request)
        entry = {"result": concept_path(result_path), "physical_validity": result["physical_validity"],
                 "resource_observation_valid": result["resource_observation_valid"],
                 "cpu_seconds": result["cpu_seconds"], "wall_seconds": result["wall_seconds"]}
        if result["physical_validity"]:
            state_path = result_path.parent / "state.npz"
            measured = measure(load_mps(state_path, request), request)
            assert abs(measured["energy"] - result["measurement"]["energy"]) < 1e-10
            assert sha256(state_path) == result["state_sha256"]
            with zipfile.ZipFile(state_path) as archive:
                expanded = sum(member.file_size for member in archive.infolist())
            assert expanded <= 8 * 1024 ** 2 and state_path.stat().st_size <= 8 * 1024 ** 2
            entry.update(remeasurement=measured, compressed_bytes=state_path.stat().st_size,
                         uncompressed_bytes=expanded, state_sha256=result["state_sha256"])
        runs.append(entry)

    records = []
    for family in FAMILIES:
        for record in proposal["cases"]:
            if record["family"] != family:
                continue
            root = OLD if record["provenance"]["source_scope"] == "immutable_prior_tranche" else ROOT
            case = record["source_case_id"]
            request = read_json(root / "requests" / (case + ".json"))
            validate_request(request)
            assert "budget_seconds" not in record["request"] and "wall_seconds" not in record["request"]
            reference_path = CONCEPT / record["reference_state"]
            reference = measure(load_mps(reference_path, request), request)
            assert abs(reference["energy"] - record["reference_energy"]) < 1e-10
            portfolio_path = root / "runs" / case / "v3_40/result.json"
            portfolio = read_json(portfolio_path)
            portfolio_state = portfolio_path.parent / "state.npz"
            checked_portfolio = measure(load_mps(portfolio_state, request), request)
            assert abs(checked_portfolio["energy"] - portfolio["measurement"]["energy"]) < 1e-10
            record["provenance"]["v3_portfolio"] = {
                "result": concept_path(portfolio_path), "state": concept_path(portfolio_state),
                "result_sha256": sha256(portfolio_path), "state_sha256": sha256(portfolio_state),
                "measurement": checked_portfolio,
                "cpu_seconds": portfolio["cpu_seconds"], "wall_seconds": portfolio["wall_seconds"],
                "resource_observation_valid": portfolio["resource_observation_valid"],
                "energy_above_reference": checked_portfolio["energy"] - reference["energy"],
            }
            if root == ROOT:
                old_request = read_json(OLD / "requests" / (FAMILIES[family][0] + ".json"))
                differences = {}
                for key in ("omega", "mass2", "lambda4", "coupling", "field"):
                    change = np.asarray(request[key]) - np.asarray(old_request[key])
                    differences[key] = {"changed_entries": int(np.count_nonzero(change)),
                                        "maximum_absolute_change": float(np.max(np.abs(change)))}
                record["provenance"]["physical_changes_from_original"] = differences
                record["provenance"]["request_generation"] = concept_path(root / "requests" / (case + ".provenance.json"))
            records.append(record)
    counts = dict(Counter(record["family"] for record in records))
    assert all(count <= 2 for count in counts.values())
    assert all(record["baseline_gaps"]["minimum_screen_ratio"] >= 2 for record in records)
    assert len({record["source_case_id"] for record in records}) == len(records)
    search_accounting = read_json(ROOT / "SEARCH_ACCOUNTING.json")
    allocation_accounting = read_json(ROOT / "ALLOCATION_ACCOUNTING.json") if (ROOT / "ALLOCATION_ACCOUNTING.json").exists() else {}
    quota_accounting = read_json(ROOT / "QUOTA_ACCOUNTING.json") if (ROOT / "QUOTA_ACCOUNTING.json").exists() else {}
    child_total = search_accounting["child_cpu_seconds"] + allocation_accounting.get("child_cpu_seconds", 0.0) + quota_accounting.get("child_cpu_seconds", 0.0)
    assert abs(sum(entry["cpu_seconds"] for entry in runs) - child_total) < 1e-3
    audit_accounting = {"cpu_seconds": time.process_time(), "wall_seconds": time.monotonic() - started}
    total_recorded = search_accounting["total_cpu_seconds"] + allocation_accounting.get("total_cpu_seconds", 0.0) + quota_accounting.get("total_cpu_seconds", 0.0) + audit_accounting["cpu_seconds"]
    assert total_recorded < 1200
    audit = {
        "passed": True, "timestamp_utc": stamp(), "formal_admission_run": False,
        "prior_immutable_manifests": prior_manifests,
        "search_source_files_verified": len(sources), "allocation_source_files_verified": len(allocation_sources),
        "quota_source_files_verified": len(quota_sources),
        "byte_identical_snapshot_files_verified": len(origins),
        "operator_convention": "P q^k P: independently compare d+8 oscillator powers with trusted d+4 projection",
        "operator_checks": operator_errors, "previous_dense_validation": concept_path(OLD / "validation/projected_convention.json"),
        "previous_dense_validation_sha256": sha256(OLD / "validation/projected_convention.json"),
        "previous_dense_validation_result": read_json(OLD / "validation/projected_convention.json"),
        "new_run_remeasurements": runs, "family_counts": counts, "audit_accounting": audit_accounting,
        "search_plus_audit_recorded_cpu_seconds": total_recorded,
        "note": "Source inspection, shell housekeeping and report serialization CPU outside the timed Python processes is not in this counter; search retained a conservative reserve.",
    }
    write_json(ROOT / "AUDIT.json", audit)
    proposal.update(cases=records, audit=concept_path(ROOT / "AUDIT.json"), family_counts=counts,
                    search_plus_audit_recorded_cpu_seconds=total_recorded,
                    scope="private measured proposal, not formal admission or solver grading")
    atomic_json(ROOT / "PROPOSAL.json", proposal)
    checkpoint = read_json(ROOT / "CHECKPOINT.json")
    checkpoint.update(actual_proposal_records=records, audit_passed=True, audit=concept_path(ROOT / "AUDIT.json"),
                      proposal=concept_path(ROOT / "PROPOSAL.json"), active=None, controller_running=False,
                      family_counts=counts, search_plus_audit_recorded_cpu_seconds=total_recorded, updated_utc=stamp())
    atomic_json(ROOT / "CHECKPOINT.json", checkpoint)

    lines = ["# Tranche 3 measured proposal", "", f"Selected records: {len(records)}; new physical variants actually run: {search_accounting['configuration_count']}.",
             "No formal admission, full privileged grade, public changes, or fresh launch was performed.",
             "All candidates use N64, d14, zero fields and fixed even/odd parity within unchanged bounds.", "",
             "| Family | Case | Reference energy | Minimum repeated v4 gap | Screen multiple |", "|---|---|---:|---:|---:|"]
    for record in records:
        gap = min(record["baseline_gaps"]["v4_40"], record["baseline_gaps"]["repeat_v4_40"])
        lines.append(f"| {record['family']} | {record['source_case_id']} | {record['reference_energy']:.14f} | {gap:.10g} | {record['baseline_gaps']['minimum_screen_ratio']:.5f} |")
    lines.extend(["", "## Interpretation", "",
                  "The v4 baseline and repeat are byte-identical production code, each independently initialized at a 40-second CPU request. All selected baseline/repeat states passed trusted physical and observed resource checks.",
                  "References are attained same-cap MPS, not exact ground energies. Most use the v3 portfolio followed by the corrected warm teacher; any controlled v4-seed single-cut reallocation is explicitly labeled in provenance. The teacher/v3 differences and parity-resolved bond counts are recorded per case.",
                  "The original disordered case has a separate controlled reallocation experiment in immutable prior evidence. New baseline/portfolio charge-count differences support the same failure cluster but alone are not causal interventions; separately labeled quota-teacher runs are actual prescribed-allocation interventions on existing Hamiltonians.",
                  "The Hamiltonian is the fixed finite projected oscillator problem, with padded-operator powers before projection. No continuum-critical or continuum-exact claim is made.",
                  "Marginal screens and negative variants remain in SUMMARY.json but are excluded from the proposal. Uniform size/timing controls are neither used nor inspected.", "",
                  "## Accounting", "",
                  f"Search child CPU: {search_accounting['child_cpu_seconds']:.6f} s; search controller CPU: {search_accounting['controller_cpu_seconds']:.6f} s; audit CPU: {audit_accounting['cpu_seconds']:.6f} s.",
                  f"Additional existing-case allocation search CPU: {allocation_accounting.get('total_cpu_seconds', 0.0):.6f} s; wall: {allocation_accounting.get('wall_seconds', 0.0):.6f} s.",
                  f"Additional existing-case quota search CPU: {quota_accounting.get('total_cpu_seconds', 0.0):.6f} s; wall: {quota_accounting.get('wall_seconds', 0.0):.6f} s.",
                  f"Recorded search plus audit CPU: {total_recorded:.6f} / 1200 s. Search wall: {search_accounting['wall_seconds']:.6f} s; audit wall: {audit_accounting['wall_seconds']:.6f} s.",
                  f"Portfolio stop reason: {search_accounting['stop_reason']}; allocation search: {allocation_accounting.get('stop_reason', 'not performed')}.",
                  f"Quota search stop reason: {quota_accounting.get('stop_reason', 'not performed')}.",
                  "Old artifact manifests and source snapshots were verified unchanged. Every write is confined to tranche_3.", ""])
    (ROOT / "REPORT.md").write_text("\n".join(lines))
    artifacts = {str(path.relative_to(ROOT)): {"sha256": sha256(path), "bytes": path.stat().st_size}
                 for path in sorted(ROOT.rglob("*")) if path.is_file()
                 and path.name not in ("ARTIFACT_MANIFEST.json", "audit.log")}
    write_json(ROOT / "ARTIFACT_MANIFEST.json", artifacts)
    print(json.dumps({"audit_passed": True, "records": len(records), "family_counts": counts,
                      "recorded_cpu_seconds": total_recorded, "old_manifests": prior_manifests}), flush=True)


if __name__ == "__main__":
    main()
