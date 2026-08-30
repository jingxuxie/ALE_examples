import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
SEARCH = HERE.parent / "champion_1_search"
sys.path.insert(0, str(SEARCH / "champion"))
from contractor import load_mps, measure

FAMILIES = ("odd_weak_critical", "symmetry_restoration", "weak_field_response", "critical_profiles")
COEFFICIENTS = ("omega", "mass2", "lambda4", "field", "coupling")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hamiltonian_key(request):
    return (request["n_sites"], request["local_dim"],
            tuple(tuple(float(value) for value in request[name]) for name in COEFFICIENTS))


def problem_key(request):
    return hamiltonian_key(request), request["bond_cap"], request["sector"]


def coefficient_profile_key(request):
    return (request["n_sites"], tuple(tuple(float(value) for value in request[name])
                                     for name in ("mass2", "lambda4", "field", "coupling")))


def distinct_profile_selection(candidates):
    selected = []
    profiles = set()
    for candidate in candidates:
        profile = coefficient_profile_key(candidate["record"]["request"])
        if profile not in profiles:
            selected.append(candidate)
            profiles.add(profile)
        if len(selected) == 2:
            break
    return selected


def uniform(values):
    return max(values) - min(values) < 1e-14


def family_for(request):
    if any(not uniform(request[name]) for name in ("omega", "mass2", "lambda4", "coupling")):
        return "critical_profiles"
    if request["sector"] == "odd" and not any(request["field"]):
        return "odd_weak_critical"
    if request["sector"] == "any":
        return "weak_field_response" if any(request["field"]) else "symmetry_restoration"
    return "even_sector_control"


def in_bounds(request):
    if not (32 <= request["n_sites"] <= 64 and 8 <= request["local_dim"] <= 14
            and 12 <= request["bond_cap"] <= 24):
        return False
    if request["sector"] not in ("any", "even", "odd"):
        return False
    if request["sector"] != "any" and any(request["field"]):
        return False
    if any(len(request[name]) != request["n_sites"] for name in ("omega", "mass2", "lambda4", "field")):
        return False
    if len(request["coupling"]) != request["n_sites"] - 1:
        return False
    bounds = {"omega": (0.55, 1.85), "mass2": (-0.2, 0.03), "lambda4": (0.05, 0.3),
              "coupling": (0.05, 1.5), "field": (-0.004, 0.004)}
    return all(all(math.isfinite(value) and bounds[name][0] <= value <= bounds[name][1]
                   for value in request[name]) for name in bounds)


def read_search():
    records = []
    pending = []
    invalid = []
    started = []
    for request_path in sorted((SEARCH / "runs").glob("*/request.json")):
        request = json.loads(request_path.read_text())
        started.append(request)
        directory = request_path.parent
        result_path = directory / "result.json"
        try:
            raw = json.loads(result_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            pending.append(request["case_id"])
            continue
        if "reference" not in raw:
            pending.append(request["case_id"])
            continue
        try:
            champion = measure(load_mps(directory / "champion.npz", request), request)
            reference = measure(load_mps(directory / "reference.npz", request), request)
        except (ValueError, OSError) as error:
            invalid.append({"case_id": request["case_id"], "error": str(error)})
            continue
        wall_limited = (raw["champion"]["optimization_wall_seconds"] >= request["wall_seconds"] - 0.7
                        and raw["champion"]["optimization_cpu_seconds"] < request["budget_seconds"] - 0.5)
        records.append({"request": request, "directory": directory, "raw": raw,
                        "champion": champion, "reference": reference,
                        "family": family_for(request), "in_bounds": in_bounds(request),
                        "wall_limited": wall_limited})
    return records, started, pending, invalid


def candidates_from(records):
    candidates = []
    for record in records:
        if not record["in_bounds"] or record["wall_limited"] or record["family"] not in FAMILIES:
            continue
        request = record["request"]
        best_source = record
        best_measure = record["reference"]
        for source in records:
            if hamiltonian_key(source["request"]) != hamiltonian_key(request):
                continue
            try:
                checked = measure(load_mps(source["directory"] / "reference.npz", request), request)
            except (ValueError, OSError):
                continue
            if checked["energy"] < best_measure["energy"]:
                best_source, best_measure = source, checked
        gap = record["champion"]["energy"] - best_measure["energy"]
        screen = 1e-7 * request["n_sites"]
        candidates.append({"record": record, "reference_source": best_source,
                           "reference_measure": best_measure, "gap": gap,
                           "gap_per_site": gap / request["n_sites"], "margin": gap / screen,
                           "above_screen": gap > screen})
    return candidates


def public_candidate(candidate):
    record = candidate["record"]
    return {"source_case_id": record["request"]["case_id"], "family": record["family"],
            "reference_source_case_id": candidate["reference_source"]["request"]["case_id"],
            "champion_energy": record["champion"]["energy"],
            "reference_energy": candidate["reference_measure"]["energy"],
            "energy_gap": candidate["gap"], "gap_per_site": candidate["gap_per_site"],
            "screen_margin": candidate["margin"], "above_screen": candidate["above_screen"],
            "champion_cpu_seconds": record["raw"]["champion"]["optimization_cpu_seconds"],
            "champion_wall_seconds": record["raw"]["champion"]["optimization_wall_seconds"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    records, started, pending, invalid = read_search()
    initial_report = json.loads((SEARCH / "SEARCH_STATUS.json").read_text())
    initial_ids = {record["case_id"] for record in initial_report["records"]}
    additional = [request for request in started if request["case_id"] not in initial_ids]
    if len(additional) > 12:
        raise ValueError("Additional-probe authorization exceeded")
    candidates = candidates_from(records)
    by_family = {family: sorted((candidate for candidate in candidates
                                if candidate["record"]["family"] == family and candidate["above_screen"]),
                               key=lambda candidate: candidate["margin"], reverse=True) for family in FAMILIES}
    summary = {"updated_utc": datetime.now(timezone.utc).isoformat(),
               "initial_request_records": len(initial_ids), "additional_request_records": len(additional),
               "additional_probe_limit": 12, "total_started_request_records": len(started),
               "distinct_target_problems_including_sector_and_cap": len({problem_key(request) for request in started}),
               "distinct_finite_hamiltonians": len({hamiltonian_key(request) for request in started}),
               "distinct_coefficient_profiles_excluding_basis_sector_cap": len({coefficient_profile_key(request) for request in started}),
               "completed_valid_comparisons": len(records), "pending_case_ids": pending,
               "invalid_comparisons": invalid,
               "wall_limited_case_ids_excluded": [record["request"]["case_id"] for record in records if record["wall_limited"]],
               "valid_controls_outside_proposed_bounds": sum(not record["in_bounds"] for record in records),
               "eligible_gap_counts_by_family": {family: len(by_family[family]) for family in FAMILIES},
               "energy_screen_per_site": 1e-7, "preferred_screen_margin": 10,
               "all_negative_and_below_screen_cases_retained": True,
               "invalid_or_host_wall_failures_count_as_energy_gaps": False,
               "refinement_runs_are_not_independent_cases": True,
               "builder_modified_public_evaluator_targets": False,
               "official_resource_certification": False,
               "ground_energies_certified": False,
               "full_passing_general_solver_for_proposal_known": False,
               "initial_search_validation": "adversary/ratchet_1/provenance/initial_search_validation.json"}
    progress = {"search_summary": summary,
                "candidates": [public_candidate(candidate) for candidate in sorted(candidates, key=lambda candidate: candidate["margin"], reverse=True)]}
    write_json(HERE / "progress.json", progress)
    write_json(HERE / "search_counts.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    if not args.finalize:
        return
    chosen_by_family = {family: distinct_profile_selection(by_family[family]) for family in FAMILIES}
    if pending or invalid or any(len(chosen_by_family[family]) < 2 for family in FAMILIES):
        raise SystemExit("Not ready: need two valid above-screen cases per family and no pending/invalid probes")
    chosen = [candidate for family in FAMILIES for candidate in chosen_by_family[family]]
    cases = []
    provenance = []
    counters = Counter()
    for candidate in chosen:
        record = candidate["record"]
        source = candidate["reference_source"]
        family = record["family"]
        counters[family] += 1
        identifier = "%s_%d" % (family, counters[family])
        request = {name: value for name, value in record["request"].items()
                   if name not in ("budget_seconds", "wall_seconds")}
        reference_path = HERE / "reference_states" / (identifier + ".npz")
        champion_path = HERE / "champion_states" / (identifier + ".npz")
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        champion_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source["directory"] / "reference.npz", reference_path)
        shutil.copyfile(record["directory"] / "champion.npz", champion_path)
        checked = measure(load_mps(reference_path, request), request)
        champion_checked = measure(load_mps(champion_path, request), request)
        if champion_checked["energy"] - checked["energy"] <= 1e-7 * request["n_sites"]:
            raise ValueError("Retained gap no longer clears the declared screen")
        cases.append({"family": family, "request": request,
                      "reference_state": str(reference_path.relative_to(CONCEPT)),
                      "reference_energy": checked["energy"], "source_case_id": request["case_id"]})
        request_path = HERE / "requests" / (identifier + ".json")
        write_json(request_path, request)
        detail = dict(public_candidate(candidate), independent_reference_measure=checked,
                      independent_champion_measure=champion_checked,
                      reference_state=str(reference_path.relative_to(CONCEPT)),
                      champion_state=str(champion_path.relative_to(CONCEPT)),
                      source_reference_request=source["request"],
                      same_finite_hamiltonian_verified=hamiltonian_key(source["request"]) == hamiltonian_key(request),
                      reference_source_result=source["raw"], champion_source_result=record["raw"],
                      reference_sha256=sha256(reference_path), champion_sha256=sha256(champion_path),
                      request_sha256=sha256(request_path), official_resource_certificate=False)
        provenance_path = HERE / "provenance" / (identifier + ".json")
        write_json(provenance_path, detail)
        provenance.append({"family": family, "source_case_id": request["case_id"],
                           "file": str(provenance_path.relative_to(CONCEPT)), "sha256": sha256(provenance_path)})
    assert len(cases) == 8 and dict(counters) == {family: 2 for family in FAMILIES}
    for source_directory, destination_directory in ((SEARCH / "champion", HERE / "source_snapshot/champion"),
                                                  (SEARCH, HERE / "source_snapshot/teacher")):
        destination_directory.mkdir(parents=True, exist_ok=True)
        names = ("solve.py", "optimizer.py", "mps.py", "contractor.py") if source_directory.name == "champion" else (
            "phase_scan.py", "refine.py", "teacher_engine.py", "observables.py", "test_observables.py")
        for name in names:
            shutil.copyfile(source_directory / name, destination_directory / name)
    summary["selected_cases"] = 8
    summary["selected_counts_by_family"] = dict(counters)
    summary["selected_screen_margins"] = [candidate["margin"] for candidate in chosen]
    summary["selected_cases_below_preferred_10x_margin"] = [candidate["record"]["request"]["case_id"] for candidate in chosen if candidate["margin"] < 10]
    summary["selection_policy"] = "Descending measured gap within each family, with two distinct Hamiltonian coefficient profiles rather than basis-only duplicates"
    summary["case_admission_owned_by_main"] = True
    write_json(HERE / "reference_provenance.json", {"cases": provenance, "search_summary": summary})
    write_json(HERE / "proposal.json", {"cases": cases, "search_summary": summary})
    manifest = {str(path.relative_to(HERE)): {"sha256": sha256(path), "bytes": path.stat().st_size}
                for path in sorted(HERE.rglob("*")) if path.is_file() and path.name != "manifest.json"}
    write_json(HERE / "manifest.json", manifest)
    print("PROPOSAL_READY: eight independently remeasured cases; four families, two each", flush=True)


if __name__ == "__main__":
    main()
