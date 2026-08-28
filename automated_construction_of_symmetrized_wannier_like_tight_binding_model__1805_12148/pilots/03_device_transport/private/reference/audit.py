"""Audit stored authoritative references, without evaluating confirmation submissions."""

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np

REFERENCE = Path(__file__).resolve().parent
PRIVATE = REFERENCE.parent
sys.path.insert(0, str(PRIVATE))
from evaluator import WEIGHTS, numerical_errors


def read_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_only_diagnostic(expected):
    approximation = {key: value.copy() for key, value in expected.items()}
    approximation["channels"][:] = 0
    approximation["partition_noise"][:] = 0
    energy_count, lead_count = expected["mode_counts"].shape
    for energy_index in range(energy_count):
        for outgoing in range(lead_count):
            for incoming in range(lead_count):
                if outgoing == incoming:
                    continue
                count = min(expected["mode_counts"][energy_index, outgoing],
                            expected["mode_counts"][energy_index, incoming])
                if count:
                    value = expected["transmission"][energy_index, outgoing, incoming] / count
                    approximation["channels"][energy_index, outgoing, incoming, :count] = value
                    approximation["partition_noise"][energy_index, outgoing, incoming] = count * value * (1 - value)
    errors, details = numerical_errors(approximation, expected)
    return {"errors": errors, "field_errors": details,
            "optimistic_oracle_assisted_score": sum(WEIGHTS[group] * (1 - errors[group]) for group in WEIGHTS)}


def main():
    baseline = json.loads((REFERENCE / "baseline_report_test.json").read_text())
    assert baseline["core_score"] == 0
    assert all(row["returncode"] == 0 for row in baseline["per_case"])
    controls = {}
    for split in ("test", "challenge"):
        report = json.loads((REFERENCE / f"control_report_{split}.json").read_text())
        assert report["core_score"] > 0.9 and report["worst_family_score"] > 0.9
        controls[split] = {key: report[key] for key in ("core_score", "worst_family_score", "family_scores")}
        controls[split]["maximum_runtime_seconds"] = max(row["runtime_seconds"] for row in report["per_case"])
        controls[split]["maximum_peak_rss_mb"] = max(row["peak_rss_mb"] for row in report["per_case"])
    hashes = set()
    cases = []
    diagnostics = []
    for split in ("test", "challenge", "confirmation"):
        directory = PRIVATE / "challenge_pool" / split
        manifest = json.loads((directory / "manifest.json").read_text())
        assert len(manifest) == 4
        for item in manifest:
            measured = item["diagnostics"]
            input_hash = digest(directory / item["input"])
            assert input_hash == measured["input_sha256"] and input_hash not in hashes
            hashes.add(input_hash)
            assert digest(directory / item["reference"]) == measured["reference_sha256"]
            assert all(rank < size for rank, size in zip(measured["lead_hopping_ranks"], measured["lead_dimensions"]))
            cases.append({"id": item["id"], "split": split, "family": item["family"], **measured,
                          "one_dense_complex_matrix_mib": 16 * measured["device_orbitals"] ** 2 / 1024 ** 2})
            if split == "confirmation":
                continue
            case = read_arrays(directory / item["input"])
            expected = read_arrays(directory / item["reference"])
            assert all(value.dtype.kind != "O" for value in case.values())
            assert all(np.all(np.isfinite(value)) for value in expected.values())
            for energy_index, counts in enumerate(expected["mode_counts"]):
                assert np.max(np.abs(expected["lb_conductance"][energy_index]
                                     - np.diag(counts) + expected["transmission"][energy_index])) < 1e-8
                for outgoing in range(len(counts)):
                    for incoming in range(len(counts)):
                        if outgoing == incoming:
                            continue
                        eigenvalues = expected["channels"][energy_index, outgoing, incoming]
                        assert np.min(eigenvalues) > -1e-8 and np.max(eigenvalues) < 1 + 1e-8
                        assert np.max(np.diff(eigenvalues)) < 1e-8
                        assert abs(eigenvalues.sum() - expected["transmission"][energy_index, outgoing, incoming]) < 1e-8
                        assert abs(np.sum(eigenvalues * (1 - eigenvalues))
                                   - expected["partition_noise"][energy_index, outgoing, incoming]) < 1e-8
            diagnostics.append({"split": split, "id": item["id"], "family": item["family"],
                                **trace_only_diagnostic(expected)})
    source_files = ["kwant/physics/leads.py", "kwant/physics/noise.py", "kwant/solvers/common.py",
                    "kwant/solvers/sparse.py", "kwant/builder.py", "tbmodels/_tb_model.py"]
    sources = {name: digest(REFERENCE / "vendor" / name) for name in source_files}
    versions = {distribution.metadata["Name"]: distribution.version
                for distribution in importlib.metadata.distributions(path=[str(REFERENCE / "vendor")])}
    report = {"status": "validated", "baseline_core_score": baseline["core_score"], "controls": controls,
              "cases": cases, "trace_only_diagnostics": diagnostics,
              "diagnostic_caveat": "Oracle-assisted ablation only: all outputs except eigenchannels/noise remain exact. Not a submitted baseline or claimed shortcut implementation.",
              "confirmation": "Stored and hash-checked; no submission/control evaluation or trace-only diagnostic.",
              "source_sha256": sources, "private_versions": versions, "python_version": sys.version,
              "geometry": json.loads((REFERENCE / "models/geometry_validation.json").read_text())}
    (REFERENCE / "validation_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"controls": controls, "cases": len(cases),
                      "trace_only_scores": {row["split"] + "/" + row["family"]: row["optimistic_oracle_assisted_score"] for row in diagnostics}}, indent=2))


if __name__ == "__main__":
    raise SystemExit("Legacy audit is frozen. Run post_audit.py for current scoring; legacy reports are preserved.")
