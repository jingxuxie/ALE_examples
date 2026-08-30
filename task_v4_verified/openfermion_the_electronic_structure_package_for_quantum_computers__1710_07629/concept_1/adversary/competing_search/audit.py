import argparse
import hashlib
import json
import os
import shutil
import time
from collections import defaultdict

import numpy as np
from scipy.linalg import expm

import search


def prepare():
    request = search.read_json("cases.json")
    provenance = search.read_json("provenance.json")
    starts = search.read_json("starts.json")
    counts = defaultdict(int)
    for case, record in zip(request["cases"], provenance["cases"]):
        ordinal = counts[case["family"]]
        counts[case["family"]] += 1
        record["prospective_split"] = "public" if ordinal < 4 else "hidden"
        first, second = starts[case["id"]][:2]
        roots = np.tensordot(np.asarray(first["auxiliary"]), np.asarray(case["factors"]), axes=(1, 0))
        boundary = record["family_ranks"][0]
        entries = []
        for group in (roots[:boundary], roots[boundary:]):
            row = []
            for starting in (first, second):
                orbital = np.asarray(starting["orbital"])
                rotated = np.stack([orbital.T @ factor @ orbital for factor in group])
                weights = np.abs(rotated).sum(axis=(1, 2))
                row.append(float(0.5 * weights @ weights))
            entries.append(row)
        record["unmixed_family_costs_in_two_planted_bases"] = entries
        record["both_families_prefer_own_basis"] = entries[0][0] < entries[0][1] and entries[1][1] < entries[1][0]
    provenance["split_rule"] = "Before inspecting champion results: first four independent seeds per stratum public; next four hidden. Both splits contain n=10,12,14,16 in every stratum. Split assignment never enters the objective."
    search.write_json("provenance.json", provenance)
    print(json.dumps({"phase": "prepared", "cases_with_competing_native_preferences": sum(record["both_families_prefer_own_basis"] for record in provenance["cases"])}), flush=True)


def refine(seconds):
    report = search.read_json("report.json")
    request = search.read_json("cases.json")
    cases = {case["id"]: case for case in request["cases"]}
    private = {entry["id"]: entry for entry in search.read_json("private_solution.json")["solutions"]}
    champion = {entry["id"]: entry for entry in search.read_json("champion_solution.json")["solutions"]}
    selected = sorted(report["records"], key=lambda record: record["attainable_extra_reduction"], reverse=True)[:6]
    deadline = time.monotonic() + seconds
    refinements = []
    for index, record in enumerate(selected):
        case = cases[record["id"]]
        generator = np.random.default_rng(record["seed"] + 710009)
        best = private[case["id"]]
        best_cost = search.validate_solution(case, best)
        per_case = max(0, deadline - time.monotonic()) / (len(selected) - index)
        case_deadline = time.monotonic() + per_case
        attempts = []
        for trial in range(12):
            remaining = case_deadline - time.monotonic()
            if remaining < 0.25:
                break
            center = champion[case["id"]] if trial % 3 == 0 else best
            orbital = np.asarray(center["orbital"])
            auxiliary = np.asarray(center["auxiliary"])
            scale = (0.0, 0.03, 0.1, 0.25)[trial % 4]
            for matrix in (orbital, auxiliary):
                skew = generator.normal(size=matrix.shape)
                skew = (skew - skew.T) / np.sqrt(len(matrix))
                matrix[:] = matrix @ expm(scale * skew)
            starting = search.solution(case["id"], orbital, auxiliary)
            candidate, details = search.PORTFOLIO.optimize(case, starting, min(4.0, remaining))
            value = search.validate_solution(case, candidate)
            attempts.append({"trial": trial, "jolt_scale": scale, "center": "champion_json_witness" if trial % 3 == 0 else "private_witness", "cost": value, "evaluations": details["evaluations"]})
            if value < best_cost:
                best, best_cost = candidate, value
        private[case["id"]] = best
        refinements.append({"id": case["id"], "cost": best_cost, "attainable_extra_reduction": 1 - best_cost / record["champion_cost"], "attempts": attempts})
        search.write_json("private_solution.json", {"solutions": [private[case["id"]] for case in request["cases"]]})
        search.write_json("refinements.json", refinements)
        print(json.dumps({key: value for key, value in refinements[-1].items() if key != "attempts"}), flush=True)
    search.summarize()


def repeat():
    archive = search.DIRECTORY / "initial_champion"
    if not archive.exists():
        shutil.copytree(search.DIRECTORY / "champion", archive)
        shutil.copy2(search.DIRECTORY / "report.json", search.DIRECTORY / "pre_mutex_report.json")
    wrapper = search.ROOT.parent / "private/affinity.py"
    if "fcntl.flock" not in wrapper.read_text():
        raise ValueError("Required affinity mutex is absent")
    search.evaluate_champion(search.ROOT / "champions/generation_1")
    search.write_json("mutex_revalidation.json", {"all_24_cases_repeated": True, "wrapper_sha256": hashlib.sha256(wrapper.read_bytes()).hexdigest(), "method": "Two serialized original 12-case batches through the affinity wrapper with its global fcntl lock. Initial responses retained in initial_champion/.", "cpu": 188})
    search.summarize()


def finish():
    search.summarize()
    report = search.read_json("report.json")
    request = search.read_json("cases.json")
    cases = {case["id"]: case for case in request["cases"]}
    private = {entry["id"]: entry for entry in search.read_json("private_solution.json")["solutions"]}
    champion = {entry["id"]: entry for entry in search.read_json("champion_solution.json")["solutions"]}
    provenance = {entry["id"]: entry for entry in search.read_json("provenance.json")["cases"]}
    initial_report = search.read_json("pre_mutex_report.json")
    initial_records = {entry["id"]: entry for entry in initial_report["records"]}
    changes = [filename for filename, digest in search.read_json("frozen_sources.json").items() if hashlib.sha256((search.ROOT / filename).read_bytes()).hexdigest() != digest]
    if changes:
        raise ValueError(f"Frozen source hashes changed: {changes}")
    clusters = defaultdict(list)
    for record in report["records"]:
        record["initial_extra_reduction"] = initial_records[record["id"]]["attainable_extra_reduction"]
        record["robust_extra_reduction"] = min(record["initial_extra_reduction"], record["attainable_extra_reduction"])
        if record["robust_extra_reduction"] < 0.005:
            continue
        identifier = record["id"]
        case = cases[identifier]
        cross_orbital = dict(champion[identifier], orbital=private[identifier]["orbital"])
        cross_auxiliary = dict(champion[identifier], auxiliary=private[identifier]["auxiliary"])
        orbital_only = search.validate_solution(case, cross_orbital)
        auxiliary_only = search.validate_solution(case, cross_auxiliary)
        sampled_best = record["champion_cost"]
        generator = np.random.default_rng(record["seed"] + 11171)
        for trial in range(120):
            candidate = dict(champion[identifier])
            name = "orbital" if trial % 2 == 0 else "auxiliary"
            matrix = np.asarray(candidate[name]).copy()
            first, second = generator.choice(len(matrix), size=2, replace=False)
            angle = generator.choice((0.001, 0.01, 0.05)) * generator.choice((-1, 1))
            left = matrix[:, first].copy()
            right = matrix[:, second].copy()
            matrix[:, first] = np.cos(angle) * left + np.sin(angle) * right
            matrix[:, second] = -np.sin(angle) * left + np.cos(angle) * right
            candidate[name] = matrix.tolist()
            sampled_best = min(sampled_best, search.validate_solution(case, candidate))
        evidence = {"both_families_prefer_own_basis": provenance[identifier]["both_families_prefer_own_basis"], "private_orbital_with_champion_auxiliary_cost": orbital_only, "champion_orbital_with_private_auxiliary_cost": auxiliary_only, "best_sampled_small_rotation_reduction": 1 - sampled_best / record["champion_cost"], "coordinated_replacement_needed_for_this_witness": min(orbital_only, auxiliary_only) >= record["champion_cost"]}
        record["root_cause_evidence"] = evidence
        clusters[record["family"]].append(record)
    eligible = {family: entries for family, entries in clusters.items() if {record["prospective_split"] for record in entries} == {"public", "hidden"}}
    retained = [entry for entries in eligible.values() for entry in entries]
    physical_spectra = {}
    for record in retained:
        case = cases[record["id"]]
        factors = np.asarray(case["factors"])
        one_particle = np.asarray(case["one_body"]) + 0.5 * np.einsum("aij,ajk->ik", factors, factors)
        physical_spectra[case["id"]] = np.linalg.eigvalsh(one_particle).tolist()
    independence = []
    for public in [record for record in retained if record["prospective_split"] == "public"]:
        for hidden in [record for record in retained if record["prospective_split"] == "hidden"]:
            public_spectrum = np.asarray(physical_spectra[public["id"]])
            hidden_spectrum = np.asarray(physical_spectra[hidden["id"]])
            same_dimension = len(public_spectrum) == len(hidden_spectrum)
            separation = float(np.linalg.norm(public_spectrum - hidden_spectrum) / max(np.linalg.norm(public_spectrum), np.linalg.norm(hidden_spectrum))) if same_dimension else None
            independence.append({"public": public["id"], "hidden": hidden["id"], "distinct_parent_seeds": set(provenance[public["id"]]["parent_seeds"]).isdisjoint(provenance[hidden["id"]]["parent_seeds"]), "same_dimension": same_dimension, "relative_one_particle_spectral_separation": separation, "not_an_exact_orbital_auxiliary_regauging": not same_dimension or separation > 1e-6})
    report["physical_independence_proof"] = {"one_particle_sector_spectra": physical_spectra, "public_hidden_pairs": independence, "criterion": "The physical N=1 Hamiltonian is h + 0.5*sum(B_k@B_k). Its spectrum is invariant under both allowed gauges; different spectra exclude exact regauging transfer."}
    proposed = {}
    for split in ("public", "hidden", "combined"):
        entries = [record for record in retained if split == "combined" or record["prospective_split"] == split]
        ratios = [record["private_cost"] / record["champion_cost"] for record in entries]
        family_scores = {family: 1 - np.exp(np.mean([np.log(record["private_cost"] / record["champion_cost"]) for record in entries if record["family"] == family])) for family in {record["family"] for record in entries}}
        if entries:
            aggregate = float(1 - np.exp(np.mean(np.log(ratios))))
            worst = float(min(family_scores.values()))
            proposed[split] = {"cases": len(entries), "core_score": aggregate, "worst_family_score": worst, "quality_pass": aggregate >= 0.01 and worst >= 0.005, "required_runtime_seconds": 10 * len(entries), "runtime_valid_general_solver_established": False}
        if split != "combined":
            search.write_json(f"ratchet_candidates/{split}.json", {"cases": [cases[record["id"]] for record in entries], "seconds_per_case": 10, "reference_costs": {record["id"]: record["champion_cost"] for record in entries}, "next_targets": {"core_score": 0.01, "worst_family_score": 0.005, "runtime_seconds": 10 * len(entries)}, "not_a_participant_generation": True})
            search.write_json(f"ratchet_candidates/{split}.witnesses.json", {"solutions": [private[record["id"]] for record in entries]})
    report["ready_for_new_target"] = bool(eligible) and not report["failures"] and all(proposed.get(split, {}).get("quality_pass", False) for split in ("public", "hidden")) and all(pair["distinct_parent_seeds"] and pair["not_an_exact_orbital_auxiliary_regauging"] for pair in independence)
    report["proposed_next_target_artifact_scores"] = proposed
    report["original_8_percent_search_goal_met"] = report["at_least_8_percent_gaps"] > 0
    report["positive_gaps"] = sum(record["attainable_extra_reduction"] > 1e-6 for record in report["records"])
    report["positive_gap_numerical_floor"] = 1e-6
    report["mutex_revalidated"] = (search.DIRECTORY / "mutex_revalidation.json").exists()
    report["submitted_champion"] = str(search.ROOT / "champions/generation_1")
    report["champion_file_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (search.ROOT / "champions/generation_1").iterdir() if path.is_file()}
    report["frozen_sources_unchanged"] = True
    report["both_families_prefer_own_basis_count"] = sum(record["both_families_prefer_own_basis"] for record in provenance.values())
    report["independent_split_clusters"] = {family: {split: [record["id"] for record in entries if record["prospective_split"] == split] for split in ("public", "hidden")} for family, entries in eligible.items()}
    report["next_target_recommendation"] = "Candidate only: disclose the competing-locality distribution; freeze 1.0% extra aggregate and 0.5% worst-family reduction over the saved champion reference costs, at 10 seconds per case and total 10*N. The private artifact passes quality, not an unprivileged runtime claim. Original 25%/10% targets are untouched. Small sample and single-family limitations require explicit disclosure." if report["ready_for_new_target"] else "No supported 1.0% aggregate / 0.5% worst-family ratchet from this bounded search; retain original task as solved."
    report["mutex_batch_runtime_audit"] = [{"batch": batch, "cases": 12, "runtime_seconds": search.read_json(f"champion/batch_{batch}.report.json").get("runtime_seconds"), "next_budget_seconds": 120, "observed_within_next_budget": search.read_json(f"champion/batch_{batch}.report.json").get("runtime_seconds", float("inf")) <= 120, "frozen_evaluator_enforced_limit": 180} for batch in range(2)]
    search.write_json("report.json", report)
    search.write_json("validation.json", {"all_private_witnesses_valid": all(np.isfinite(search.validate_solution(case, private[case["id"]])) for case in request["cases"]), "frozen_sources_unchanged": True, "numeric_contract_valid": all(10 <= len(case["one_body"]) <= 16 and 8 <= len(case["factors"]) <= 14 for case in request["cases"]), "cases": len(cases), "champion_code_imported": False, "distribution_extension": True})
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "refine", "repeat", "finish"))
    parser.add_argument("--seconds", type=float, default=150)
    arguments = parser.parse_args()
    if arguments.phase != "prepare" and 188 in os.sched_getaffinity(0):
        os.sched_setaffinity(0, {188})
    if arguments.phase == "prepare":
        prepare()
    elif arguments.phase == "refine":
        refine(arguments.seconds)
    elif arguments.phase == "repeat":
        repeat()
    else:
        finish()


if __name__ == "__main__":
    main()
