"""Bounded equivalent-principal-layer probes of the valid initial03 solver."""

import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import structural_rank

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent
PRIVATE = REFERENCE.parent
PILOT = PRIVATE.parent
sys.path.insert(0, str(PRIVATE))
sys.path.insert(0, str(REFERENCE))
from build import check_geometry_contract
from evaluator import WEIGHTS, numerical_errors, run_submission, score_components


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def regroup(original, period_cells):
    case = {key: value.copy() for key, value in original.items()}
    old_period = original["lead_period_0"]
    step = -old_period // np.gcd.reduce(np.abs(old_period))
    basis = np.eye(3, dtype=np.int64)
    basis[0] = step
    inverse = np.rint(np.linalg.inv(basis)).astype(np.int64)
    assert np.array_equal(basis @ inverse, np.eye(3, dtype=np.int64))
    grid = original["cells"] @ inverse
    lower, upper = int(grid[:, 0].min()), int(grid[:, 0].max())
    assert 2 * period_cells < upper - lower + 1
    for lead_index in (0, 1):
        old_grid = original[f"lead_cells_{lead_index}"] @ inverse
        cross_section = sorted({tuple(tag[1:]) for tag in old_grid})
        span = range(lower, lower + period_cells) if lead_index == 0 else range(upper - period_cells + 1, upper + 1)
        tags = [[longitudinal, *transverse] for longitudinal, transverse in itertools.product(span, cross_section)]
        case[f"lead_cells_{lead_index}"] = np.asarray(tags, dtype=np.int64) @ basis
        case[f"lead_period_{lead_index}"] = (-1 if lead_index == 0 else 1) * period_cells * step
    changed = {"lead_cells_0", "lead_cells_1", "lead_period_0", "lead_period_1"}
    assert all(np.array_equal(original[key], case[key]) for key in original if key not in changed)
    check_geometry_contract(case)
    return case


def support_diagnostics(case, lead_index):
    orbital_count = case["h_matrices"].shape[1]
    tags = case[f"lead_cells_{lead_index}"]
    period = case[f"lead_period_{lead_index}"]
    hoppings = {tuple(vector): matrix for vector, matrix in zip(case["h_R"], case["h_matrices"])}
    entries = []
    for row_index, row_tag in enumerate(tags):
        for column_index, column_tag in enumerate(tags):
            block = hoppings.get(tuple(column_tag - row_tag - period))
            if block is not None:
                rows, columns = np.nonzero(block)
                entries.extend(zip(row_index * orbital_count + rows, column_index * orbital_count + columns,
                                   block[rows, columns]))
    active_rows = sorted({int(row) for row, column, value in entries})
    active_columns = sorted({int(column) for row, column, value in entries})
    row_map = {value: index for index, value in enumerate(active_rows)}
    column_map = {value: index for index, value in enumerate(active_columns)}
    support = np.zeros((len(active_rows), len(active_columns)), dtype=complex)
    for row, column, value in entries:
        support[row_map[row], column_map[column]] += value
    bound = min(len(active_rows), len(active_columns), structural_rank(csr_matrix(support)))
    return {"dimension": len(tags) * orbital_count, "active_rows": len(active_rows),
            "active_columns": len(active_columns), "numerical_rank": int(np.linalg.matrix_rank(support, tol=1e-10)),
            "submitted_structural_rank_bound": int(bound), "submitted_reduced_pencil_dimension": 2 * int(bound)}


def equivalence(original_case, regrouped_case, original_reference, regrouped_reference):
    errors = {}
    for key in ("mode_counts", "transmission", "partition_noise", "lb_conductance"):
        errors[key] = float(np.max(np.abs(original_reference[key] - regrouped_reference[key])))
    original_width = original_reference["channels"].shape[-1]
    errors["channels"] = float(np.max(np.abs(original_reference["channels"]
                                            - regrouped_reference["channels"][..., :original_width])))
    tail = regrouped_reference["channels"][..., original_width:]
    errors["channel_padding"] = float(np.max(np.abs(tail))) if tail.size else 0.0
    orbitals = original_case["h_matrices"].shape[1]
    for lead_index in range(int(original_case["lead_count"])):
        lookup = {tuple(tag): index for index, tag in enumerate(regrouped_case[f"lead_cells_{lead_index}"])}
        mapping = np.asarray([lookup[tuple(tag)] * orbitals + orbital
                              for tag in original_case[f"lead_cells_{lead_index}"] for orbital in range(orbitals)])
        key = f"sigma_{lead_index}"
        original = original_reference[key]
        enlarged = regrouped_reference[key]
        selected = enlarged[:, mapping[:, None], mapping[None, :]]
        errors[key] = float(np.max(np.abs(original - selected)))
        added = np.ones(enlarged.shape[1], dtype=bool)
        added[mapping] = False
        errors[key + "_added_rows"] = float(np.max(np.abs(enlarged[:, added]))) if np.any(added) else 0.0
        errors[key + "_added_columns"] = float(np.max(np.abs(enlarged[:, :, added]))) if np.any(added) else 0.0
    return errors


def main():
    frozen = json.loads((REFERENCE / "participant_freeze.json").read_text())
    participant = PILOT / "participant"
    current_files = {path.relative_to(participant).as_posix(): digest(path)
                     for path in sorted(participant.rglob("*")) if path.is_file()}
    prior_freeze_changes = {name: {"initial": expected, "current": current_files.get(name)}
                           for name, expected in frozen["files"].items() if current_files.get(name) != expected}
    source_hashes = {name: digest(PILOT / "attempt" / name) for name in ("solve.py", "transport.py", "leads.py")}
    initial = PRIVATE / "challenge_pool/test"
    originals = {item["family"]: item for item in json.loads((initial / "manifest.json").read_text())}
    grid = [("si_2terminal", 44), ("inas_3terminal", 26),
            ("si_2terminal", 72), ("inas_3terminal", 40),
            ("si_2terminal", 100), ("inas_3terminal", 56)]
    reports = []
    calibration = json.loads((REFERENCE / "baseline_errors.json").read_text())["errors"]
    for family, period_cells in grid:
        identifier = f"{family}_p{period_cells:03d}"
        directory = HERE / identifier
        directory.mkdir(exist_ok=True)
        report_path = directory / "report.json"
        if report_path.exists():
            saved = json.loads(report_path.read_text())
            if saved.get("complete"):
                assert saved["submitted_source_sha256"] == source_hashes, "Cached probe belongs to different submitted code"
                reports.append(saved)
                continue
        origin = originals[family]
        original_case = arrays(initial / origin["input"])
        original_reference = arrays(initial / origin["reference"])
        case = regroup(original_case, period_cells)
        input_path = directory / "input.npz"
        np.savez_compressed(input_path, **case)
        support = [support_diagnostics(case, index) for index in range(int(case["lead_count"]))]
        old_support = [support_diagnostics(original_case, index) for index in range(int(case["lead_count"]))]
        assert all(before["numerical_rank"] == after["numerical_rank"] for before, after in zip(old_support, support))
        row = {"id": identifier, "family": family, "period_cells": period_cells,
               "input_sha256": digest(input_path), "original_input_sha256": digest(initial / origin["input"]),
               "original_id": origin["id"], "device_orbitals": len(case["cells"]) * case["h_matrices"].shape[1],
               "lead_support": support, "original_lead_support": old_support,
               "only_changed_keys": ["lead_cells_0", "lead_cells_1", "lead_period_0", "lead_period_1"],
               "timeout_seconds": 90, "memory_mb": 1024, "reference_valid": False,
               "meaningful_counterexample": False, "submitted_source_sha256": source_hashes}
        reference_output = directory / "official/result.npz"
        reference_output.parent.mkdir(exist_ok=True)
        execution = run_submission(REFERENCE, input_path, reference_output, 90, 1024, trusted_reference=True)
        row["reference_execution"] = execution
        if execution["returncode"] == 0 and not execution["timed_out"] and reference_output.exists():
            reference = arrays(reference_output)
            for line in reversed(execution["log_tail"].splitlines()):
                if line.startswith("{"):
                    row["official_physics_checks"] = json.loads(line)
                    break
            comparison = equivalence(original_case, case, original_reference, reference)
            row["regrouping_equivalence_max_abs_errors"] = comparison
            row["reference_valid"] = max(comparison.values()) < 2e-5 and "official_physics_checks" in row
        write_json(report_path, row)
        print(json.dumps({"id": identifier, "stage": "official", "valid": row["reference_valid"], **execution}), flush=True)
        if row["reference_valid"]:
            attempt_output = directory / "submitted/result.npz"
            attempt_output.parent.mkdir(exist_ok=True)
            attempt_execution = run_submission(PILOT / "attempt", input_path, attempt_output, 90, 1024)
            row["submitted_execution"] = attempt_execution
            prediction = {}
            if attempt_execution["returncode"] == 0 and not attempt_execution["timed_out"] and attempt_output.exists():
                prediction = arrays(attempt_output)
            errors, details = numerical_errors(prediction, reference)
            components = score_components(errors, details, calibration[family])
            score = sum(WEIGHTS[group] * components[group] for group in WEIGHTS)
            row.update({"score": score, "errors": errors, "field_errors": details, "component_scores": components})
            row["meaningful_counterexample"] = (attempt_execution["returncode"] != 0
                                                  or attempt_execution["timed_out"] or score < 0.9)
            print(json.dumps({"id": identifier, "stage": "submitted", "score": score,
                              "meaningful_counterexample": row["meaningful_counterexample"], **attempt_execution}), flush=True)
            del prediction, reference
        row["complete"] = True
        reports.append(row)
        write_json(report_path, row)
        summary = {"status": "bounded_probe_search", "grid": grid, "reports": reports,
                   "counterexamples": [item["id"] for item in reports if item["meaningful_counterexample"]],
                   "participant_sha256": frozen["participant_sha256"], "submitted_source_sha256": source_hashes,
                   "participant_files_at_probe_start": current_files,
                   "preexisting_changes_since_initial_freeze": prior_freeze_changes,
                   "official_source_sha256": digest(REFERENCE / "vendor/kwant/physics/leads.py"),
                   "public_and_scored_cases_changed": False,
                   "reference": "Existing unchanged official Kwant smatrix oracle, including causality/current/unitarity/Dyson checks.",
                   "search_limit": "Three predefined increasing groupings in each of two real-material/contact families; no energy tuning or random edge-case search."}
        write_json(HERE / "summary.json", summary)
        if row["meaningful_counterexample"]:
            print("MEANINGFUL REGION FOUND: stop for review before any ratchet construction", flush=True)
            break
    assert {path.relative_to(participant).as_posix(): digest(path)
            for path in sorted(participant.rglob("*")) if path.is_file()} == current_files
    assert all(digest(PILOT / "attempt" / name) == expected for name, expected in source_hashes.items())
    summary = json.loads((HERE / "summary.json").read_text())
    summary["status"] = "complete_counterexample_found" if summary["counterexamples"] else "complete_no_natural_counterexample"
    summary["reference_valid_cases"] = [row["id"] for row in reports if row["reference_valid"]]
    summary["reference_ineligible_cases"] = [row["id"] for row in reports if not row["reference_valid"]]
    summary["initial_participant_freeze_sha256"] = summary.pop("participant_sha256", frozen["participant_sha256"])
    summary["participant_sha256_at_probe_start"] = hashlib.sha256(
        json.dumps(current_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    summary["decision"] = ("Review genuine counterexample before a separately authorized ratchet." if summary["counterexamples"]
                           else "No admissible failure in the bounded real-material regrouping search; stop without a ratchet.")
    write_json(HERE / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("status", "reference_valid_cases", "reference_ineligible_cases", "decision")}), flush=True)


if __name__ == "__main__":
    main()
