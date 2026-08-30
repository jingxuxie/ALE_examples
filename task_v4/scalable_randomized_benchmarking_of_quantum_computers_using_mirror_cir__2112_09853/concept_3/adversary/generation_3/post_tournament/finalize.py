import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from audit import ATTEMPTS, ROOT, WORK, digest, fingerprint_audit, parse_text_circuit, write


def circuit_objects(value):
    if isinstance(value, dict):
        if "family" in value and "layers" in value:
            yield value
        for child in value.values():
            yield from circuit_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from circuit_objects(child)


def compact(identifier, candidate):
    fields = candidate["screen"]["fields"]
    return {
        "candidate_sha256": identifier,
        "ideal_score": candidate["ideal_score"],
        "core_score_rounded_native": candidate["screen"]["core_score_rounded_native"],
        "failed_omission_scenarios_up_to_three": int(fields["failed_scenarios"]),
        "total_omission_scenarios_up_to_three": int(fields["scenarios"]),
        "passed": candidate["screen"]["passed"],
        "sources": candidate["sources"],
    }


def main():
    inventory = json.loads((WORK / "candidate_inventory.json").read_text())
    summary = json.loads((WORK / "summary.json").read_text())
    candidates = inventory["candidates"]
    spec = json.loads((ROOT / "participant/input/spec.json").read_text())
    canonical = {json.dumps(candidate["circuit"], sort_keys=True, separators=(",", ":"))
                 for candidate in candidates.values()}
    already_inspected = set(inventory["inspected_fresh_files"])
    coverage = Counter()
    extra_candidates = []
    for attempt in ATTEMPTS:
        for path in sorted((ROOT / "attempts" / attempt).rglob("*")):
            if not path.is_file():
                continue
            relative = str(path.relative_to(ROOT))
            if relative in already_inspected:
                coverage["previously_inspected_candidate_or_json_files"] += 1
                continue
            content = path.read_bytes()
            if content.startswith(b"\x7fELF") or b"\x00" in content:
                coverage["binary_non_submission_files"] += 1
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                coverage["binary_non_submission_files"] += 1
                continue
            coverage["additional_text_files_inspected"] += 1
            objects = []
            if re.fullmatch(r"[\s0-9+-]+", text):
                try:
                    circuit = parse_text_circuit(path, spec["families"])
                    if circuit is not None:
                        objects.append(circuit)
                except (ValueError, StopIteration):
                    pass
            for possible_json in [text, *text.splitlines()]:
                if not possible_json.lstrip().startswith(("{", "[")):
                    continue
                try:
                    objects.extend(circuit_objects(json.loads(possible_json)))
                except json.JSONDecodeError:
                    pass
            for circuit in objects:
                known = json.dumps(circuit, sort_keys=True, separators=(",", ":")) in canonical
                extra_candidates.append({"path": relative, "previously_screened_circuit": known})
    assert all(entry["previously_screened_circuit"] for entry in extra_candidates)
    parity = []
    for artifact in inventory["full_artifacts"]:
        if artifact["attempt"] not in ATTEMPTS:
            continue
        for identifier in artifact["candidates"]:
            candidate = candidates[identifier]
            official = summary["fresh_official_reports"][artifact["attempt"]]["families"][candidate["family"]]
            count = official["resources"]["cx_count"]
            native = candidate["screen"]["fields"]
            entry = {
                "attempt": artifact["attempt"], "family": candidate["family"],
                "native_failed_scenarios": int(native["failed_scenarios"]),
                "official_failed_scenarios": sum(official["failed_scenarios_by_order"].values()),
                "native_total_scenarios": int(native["scenarios"]),
                "expected_total_scenarios": sum(math.comb(count, order) for order in range(4)),
                "independent_ideal_score": candidate["ideal_score"],
                "official_ideal_score": official["ideal_score"],
            }
            entry["matched"] = (entry["native_failed_scenarios"] == entry["official_failed_scenarios"]
                                and entry["native_total_scenarios"] == entry["expected_total_scenarios"]
                                and entry["independent_ideal_score"] == entry["official_ideal_score"])
            assert entry["matched"]
            parity.append(entry)
    best = {}
    for scope in (*ATTEMPTS, "fresh_combined", "all_known"):
        best[scope] = {}
        for family in spec["families"]:
            pool = [(identifier, candidate) for identifier, candidate in candidates.items()
                    if candidate["family"] == family["id"] and
                    (scope == "all_known" or any(source["attempt"] == scope or
                     (scope == "fresh_combined" and source["attempt"] in ATTEMPTS)
                     for source in candidate["sources"]))]
            ideal_pool = [item for item in pool if not item[1]["ideal_failures"]]
            chosen = min(ideal_pool, key=lambda item: (-item[1]["screen"]["core_score_rounded_native"],
                         item[1]["screen"]["fields"]["failed_scenarios"]))
            best[scope][family["id"]] = {"unique_candidates": len(pool),
                                          "ideal_passing_candidates": len(ideal_pool),
                                          **compact(*chosen)}
    final_fingerprints = fingerprint_audit()
    assert all(entry["unchanged"] and entry["participant_current_matches_launch"]
               for entry in final_fingerprints.values())
    write("fingerprints_final.json", final_fingerprints)
    result = {
        "generation": 3,
        "spec_sha256": summary["spec_sha256"],
        "audit_script_sha256": digest(WORK / "audit.py"),
        "finalize_script_sha256": digest(Path(__file__)),
        "coverage": dict(coverage),
        "additional_embedded_or_numeric_candidate_sources": extra_candidates,
        "fresh_unique_family_candidates": sum(any(source["attempt"] in ATTEMPTS
                                               for source in candidate["sources"])
                                              for candidate in candidates.values()),
        "all_unique_family_candidates": len(candidates),
        "official_final_parity": parity,
        "best_ideal_feasible_candidates": best,
        "ranking": "Descending core score, then ascending failed omission scenarios, restricted to ideal-feasible candidates.",
        "failure_count_semantics": "Distinct omission sets of size zero through three with at least one failing low-weight Pauli; not the number of failing Pauli checks.",
        "fresh_standalone_full_artifacts": [entry for entry in inventory["full_artifacts"] if entry["attempt"] in ATTEMPTS],
        "fresh_passing_standalone_artifacts": summary["complete_standalone_fresh_witnesses"],
        "passing_family_candidates_including_private": summary["passing_family_candidates"],
        "private_sources_are_fresh_eligible": False,
        "numeric_or_family_only_components_are_direct_full_submissions": False,
        "deadline_eligible_fresh_sources": "Only sources with attempt v_3 or v_4 and matching helper deadline hashes; private sources have no fresh eligibility.",
        "missed_valid_saved_witness_found": False,
        "passing_family_portfolio_available": False,
        "solvability": "unknown",
        "root_failure": "Faulted low-weight spreading, not ideal mixing or native resource validity. Final v_3 already fails one omission in every family; v_4 passes one but fails two omissions in every family.",
        "all_attempt_outputs_byte_identical_to_deadline": True,
        "participant_and_trusted_evaluator_unchanged": summary["participant_unchanged"] and summary["trusted_source_hashes_unchanged"],
        "no_new_optimization_or_participant_code_execution": True,
        "no_official_final_evaluation_duplicated": True,
    }
    write("eligibility_summary.json", result)
    print(json.dumps({key: result[key] for key in ("coverage", "fresh_unique_family_candidates",
          "all_unique_family_candidates", "missed_valid_saved_witness_found", "solvability",
          "all_attempt_outputs_byte_identical_to_deadline")}, indent=2))


if __name__ == "__main__":
    main()
