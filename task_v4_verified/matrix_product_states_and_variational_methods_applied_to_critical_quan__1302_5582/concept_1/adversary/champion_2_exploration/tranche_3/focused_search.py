import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import time

import numpy as np

from harness import ROOT, base_request, launch, load_mps, manifest, measure, preserve_request, sha256, write_json
from compact_diagnostics import diagnostics


OLD = ROOT.parent
CONCEPT = ROOT.parents[2]
CPU_LIMIT = 1200.0
FAMILIES = {
    "disordered_weak_link_odd": ("disordered_weaklink_cap12_odd", "teacher_90"),
    "competing_edge_island_odd": ("f2_odd_edge_islands", "teacher_80"),
    "dimerized_even_ground": ("f2_even_dimerized", "teacher_80"),
    "quartic_interface_even_ground": ("f2_even_quartic_interfaces", "teacher_80"),
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    write_json(temporary, value)
    temporary.replace(path)


def read_json(path):
    return json.loads(path.read_text())


def concept_path(path):
    return str(path.resolve().relative_to(CONCEPT))


def validate_request(request):
    length = request["n_sites"]
    assert 32 <= length <= 64
    assert 8 <= request["local_dim"] <= 14
    assert 12 <= request["bond_cap"] <= 24
    assert request["sector"] in ("even", "odd")
    bounds = {"omega": (0.55, 1.85), "mass2": (-0.20, 0.03),
              "lambda4": (0.05, 0.30), "field": (0.0, 0.0), "coupling": (0.05, 1.50)}
    for key, (minimum, maximum) in bounds.items():
        values = np.asarray(request[key])
        assert len(values) == length - int(key == "coupling"), key
        assert np.isfinite(values).all() and np.min(values) >= minimum and np.max(values) <= maximum, key


def variants():
    length = 64
    coordinate = np.linspace(0.0, 1.0, length)
    result = {family: [] for family in FAMILIES}
    disorder_specs = [
        (-0.0255, 5.0, 0.2, (12, 30, 49), (0.06, 0.09, 0.05), 0.052, 0.82, 1.48),
        (-0.0270, 7.0, 0.4, (17, 37, 51), (0.05, 0.07, 0.11), 0.050, 0.90, 1.50),
        (-0.0230, 4.0, 0.7, (10, 29, 46), (0.08, 0.05, 0.13), 0.055, 0.85, 1.45),
        (-0.0300, 5.5, 0.1, (13, 34, 53), (0.05, 0.10, 0.06), 0.060, 0.90, 1.50),
        (-0.0210, 8.0, 0.5, (18, 31, 50), (0.12, 0.05, 0.08), 0.050, 0.78, 1.48),
        (-0.0260, 3.0, 0.9, (11, 26, 45), (0.07, 0.12, 0.05), 0.055, 0.95, 1.45),
    ]
    edge_specs = [
        (-0.017, (0.08, 0.86), (0.11, 0.15), (0.020, 0.026), (10, 33, 51), (0.07, 0.11, 0.05), 0.050),
        (-0.019, (0.04, 0.92), (0.08, 0.10), (0.022, 0.021), (6, 29, 56), (0.05, 0.08, 0.07), 0.053),
        (-0.018, (0.10, 0.88), (0.13, 0.11), (0.018, 0.030), (11, 38, 53), (0.09, 0.05, 0.06), 0.055),
        (-0.020, (0.06, 0.84), (0.10, 0.16), (0.026, 0.022), (8, 30, 50), (0.05, 0.14, 0.08), 0.060),
        (-0.015, (0.03, 0.89), (0.14, 0.13), (0.024, 0.029), (10, 34, 54), (0.06, 0.07, 0.11), 0.050),
        (-0.019, (0.09, 0.95), (0.12, 0.09), (0.025, 0.024), (12, 36, 57), (0.08, 0.10, 0.05), 0.055),
    ]
    dimer_specs = [
        (-0.035, 1.45, 0.70, 0, (17, 45), (0.07, 0.05), 0.052, 14),
        (-0.031, 1.40, 0.75, 0, (21, 41), (0.05, 0.10), 0.050, 14),
        (-0.039, 1.50, 0.60, 0, (15, 39), (0.08, 0.06), 0.060, 14),
        (-0.034, 1.45, 0.65, 1, (18, 46), (0.05, 0.08), 0.055, 14),
        (-0.027, 1.35, 0.80, 0, (13, 43), (0.10, 0.05), 0.050, 12),
        (-0.037, 1.50, 0.70, 1, (20, 40), (0.06, 0.12), 0.055, 12),
    ]
    quartic_specs = [
        ((12, 20, 18, 14), (0.055, 0.100, 0.065, 0.115), (-0.025, -0.041, -0.028, -0.047), (1.45, 1.05, 1.25, 1.20), (0.07, 0.10, 0.08)),
        ((10, 22, 12, 20), (0.050, 0.080, 0.100, 0.070), (-0.023, -0.033, -0.042, -0.031), (1.50, 1.15, 0.95, 1.35), (0.10, 0.06, 0.12)),
        ((18, 14, 20, 12), (0.060, 0.095, 0.075, 0.130), (-0.026, -0.040, -0.033, -0.054), (1.40, 1.05, 1.35, 1.10), (0.05, 0.14, 0.07)),
        ((14, 18, 10, 22), (0.050, 0.120, 0.065, 0.090), (-0.019, -0.048, -0.027, -0.037), (1.50, 0.95, 1.40, 1.20), (0.12, 0.08, 0.05)),
        ((20, 12, 18, 14), (0.055, 0.075, 0.110, 0.085), (-0.025, -0.035, -0.047, -0.036), (1.45, 1.25, 1.05, 1.30), (0.06, 0.09, 0.13)),
        ((11, 17, 21, 15), (0.065, 0.105, 0.080, 0.125), (-0.028, -0.044, -0.033, -0.051), (1.35, 1.10, 1.45, 1.15), (0.08, 0.05, 0.11)),
    ]
    for family_index, family in enumerate(FAMILIES):
        for variant_index in range(6):
            generator_seed = 1302558300 + 100 * family_index + variant_index
            generator = np.random.default_rng(generator_seed)
            case = "f3_" + family + "_" + str(variant_index + 1)
            sector = "odd" if family_index < 2 else "even"
            request = base_request(case, -0.025, sector)
            request["bond_cap"] = 12
            if family_index == 0:
                mass, frequency, phase, contacts, strengths, quartic, low, high = disorder_specs[variant_index]
                request["mass2"] = (mass + 0.006 * np.sin(frequency * np.pi * coordinate + phase)
                                    + generator.uniform(-0.003, 0.003, length)).tolist()
                request["lambda4"] = [quartic] * length
                request["coupling"] = generator.uniform(low, high, length - 1).tolist()
                physical_spec = disorder_specs[variant_index]
                motivation = "Unequal weakly coupled regions with changed contact locations, strengths, mass-wave profile, quartic and independent spatial spring disorder."
            elif family_index == 1:
                mass, centers, widths, depths, contacts, strengths, quartic = edge_specs[variant_index]
                profile = mass + 0.0008 * np.cos(3 * np.pi * coordinate + 0.2 * variant_index)
                for center, width, depth in zip(centers, widths, depths):
                    profile -= depth * np.exp(-((coordinate - center) / width) ** 2)
                request["mass2"] = (profile + generator.uniform(-0.002, 0.002, length)).tolist()
                request["lambda4"] = [quartic] * length
                request["coupling"] = generator.uniform(1.08, 1.48, length - 1).tolist()
                physical_spec = edge_specs[variant_index]
                motivation = "Competing end islands with changed locations, widths, depths and separating weak-contact geometry; independent quenched mass/spring disorder."
            elif family_index == 2:
                mass, strong, weak, phase, contacts, strengths, quartic, cap = dimer_specs[variant_index]
                request["bond_cap"] = cap
                request["mass2"] = (mass + generator.uniform(-0.0035, 0.0035, length)
                                    + 0.001 * np.sin(3 * np.pi * coordinate)).tolist()
                request["lambda4"] = [quartic] * length
                request["coupling"] = [strong if (bond + phase) % 2 == 0 else weak for bond in range(length - 1)]
                physical_spec = dimer_specs[variant_index]
                motivation = "Changed dimer contrast/phase, mass and quartic coefficients, and unequal weak-contact positions test even-sector allocation independently of the original geometry."
            else:
                region_lengths, quartics, masses, springs, strengths = quartic_specs[variant_index]
                request["lambda4"] = np.repeat(quartics, region_lengths).tolist()
                request["mass2"] = (np.repeat(masses, region_lengths)
                                    + 0.0025 * np.cos((5 + variant_index) * np.pi * coordinate + 0.25)).tolist()
                request["coupling"] = np.repeat(springs, region_lengths)[:-1].tolist()
                contacts = np.cumsum(region_lengths)[:-1] - 1
                physical_spec = quartic_specs[variant_index]
                motivation = "Unequal quartic-region lengths, new quartic/mass/spring values and interface strengths change both local truncation response and inter-region entanglement."
            for contact, strength in zip(contacts, strengths):
                request["coupling"][int(contact)] = strength
            validate_request(request)
            preserve_request(request, family, motivation)
            provenance_path = ROOT / "requests" / (case + ".provenance.json")
            provenance = read_json(provenance_path)
            provenance.update(generator_seed=generator_seed, physical_spec=physical_spec,
                              solver_seed_changed=False, original_family_case=FAMILIES[family][0])
            write_json(provenance_path, provenance)
            result[family].append(case)
    return result


def allocation_differences(baseline, reference):
    first = baseline.get("diagnostics", {}).get("bond_charge_counts")
    second = reference.get("diagnostics", {}).get("bond_charge_counts")
    if first is None or second is None:
        return None
    return [{"cut": before["cut"], "v4": before, "reference": after}
            for before, after in zip(first, second) if before != after]


def measured_record(family, case, root, reference_label):
    request_path = root / "requests" / (case + ".json")
    request = read_json(request_path)
    validate_request(request)
    baseline_dir = root / "runs" / case / "v4_40"
    repeat_dir = root / "runs" / case / "repeat_v4_40"
    reference_dir = root / "runs" / case / reference_label
    results = {}
    for label, directory in (("baseline", baseline_dir), ("repeat", repeat_dir), ("reference", reference_dir)):
        saved = read_json(directory / "result.json")
        tensors = load_mps(directory / "state.npz", request)
        measured = measure(tensors, request)
        assert abs(saved["measurement"]["energy"] - measured["energy"]) < 1e-9
        assert sha256(directory / "state.npz") == saved["state_sha256"]
        results[label] = {
            "result": concept_path(directory / "result.json"),
            "state_sha256": saved["state_sha256"],
            "result_sha256": sha256(directory / "result.json"),
            "measurement": measured,
            "cpu_seconds": saved["cpu_seconds"], "wall_seconds": saved["wall_seconds"],
            "resource_observation_valid": saved["resource_observation_valid"],
            "physical_validity": True,
            "diagnostics": diagnostics(tensors, request, measured["energy"]),
        }
    assert results["baseline"]["resource_observation_valid"] and results["repeat"]["resource_observation_valid"]
    reference_energy = results["reference"]["measurement"]["energy"]
    baseline_gap = results["baseline"]["measurement"]["energy"] - reference_energy
    repeat_gap = results["repeat"]["measurement"]["energy"] - reference_energy
    screen = 1e-7 * request["n_sites"]
    assert min(baseline_gap, repeat_gap) >= 2 * screen
    charge_differences = allocation_differences(results["baseline"], results["reference"])
    for value in results.values():
        value.pop("diagnostics")
    return {
        "family": family,
        "request": {key: value for key, value in request.items() if key not in ("budget_seconds", "wall_seconds")},
        "reference_state": concept_path(reference_dir / "state.npz"),
        "reference_energy": reference_energy,
        "source_case_id": case,
        "provenance": {
            "source_request": concept_path(request_path), "source_request_sha256": sha256(request_path),
            "source_scope": "immutable_prior_tranche" if root == OLD else "tranche_3",
            "reference_type": "corrected_warm_teacher_seeded_from_v3_portfolio",
            "ground_energy_certified": False, "finite_hamiltonian": "P q^k P, padded d+4 oscillator before projection",
            "same_bond_cap": True, "formal_admission_run": False,
            "measurements": results,
        },
        "baseline_gaps": {"v4_40": baseline_gap, "repeat_v4_40": repeat_gap,
                          "screen": screen, "minimum_screen_ratio": min(baseline_gap, repeat_gap) / screen},
        "allocation_difference_cuts": charge_differences,
    }


def main():
    starting_wall = time.monotonic()
    started = stamp()
    assert not (ROOT / "SEARCH_ACCOUNTING.json").exists(), "Do not overwrite a completed search"
    origins = {}
    for path in sorted((ROOT / "snapshots").rglob("*")):
        if path.is_file():
            previous = OLD / path.relative_to(ROOT)
            assert sha256(path) == sha256(previous)
            origins[str(path.relative_to(ROOT))] = {"copied_from": str(previous), "sha256": sha256(path), "identical": True}
    write_json(ROOT / "SOURCE_ORIGINS.json", origins)
    cases = variants()
    manifest()
    records = [measured_record(family, case, OLD, teacher) for family, (case, teacher) in FAMILIES.items()]
    completed = []
    confirmed = set()
    stop_reason = "variant_limit"

    def cpu_accounting():
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        return {"child_cpu_seconds": usage.ru_utime + usage.ru_stime,
                "controller_cpu_seconds": time.process_time(),
                "total_cpu_seconds": usage.ru_utime + usage.ru_stime + time.process_time(),
                "wall_seconds": time.monotonic() - starting_wall,
                "cpu_limit_seconds": CPU_LIMIT}

    def checkpoint(status, active=None):
        atomic_json(ROOT / "CHECKPOINT.json", {
            "status": status, "started_utc": started, "updated_utc": stamp(), "controller_pid": os.getpid(),
            "active": active, "accounting": cpu_accounting(), "family_partners_confirmed": sorted(confirmed),
            "new_variants_completed": len(completed), "completed_variants": completed,
            "actual_proposal_records": records, "suite_complete": len(records) == 8,
            "domain_extension": False, "fixed_parity_zero_fields_only": True,
            "formal_admission_run": False, "fresh_launch": False,
        })

    write_json(ROOT / "PLAN.json", {"families": FAMILIES, "planned_variants": cases, "max_new_configurations": 24,
                                    "max_per_family": 6, "cpu_limit_seconds": CPU_LIMIT, "early_stop": "one confirmed new partner in each family",
                                    "baseline": "byte-identical v4 at 40 CPU seconds", "teacher": "v3_40 plus corrected teacher_60 warm refinement",
                                    "required_minimum_gap_screen_ratio": 2.0, "all_candidates_fixed_parity_zero_field": True})
    checkpoint("ready")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for variant_index in range(6):
            for family in FAMILIES:
                if family in confirmed:
                    continue
                if cpu_accounting()["total_cpu_seconds"] + 220 > CPU_LIMIT:
                    stop_reason = "conservative_cpu_reserve"
                    break
                case = cases[family][variant_index]
                checkpoint("screening", {"case": case, "solvers": ["v4_40", "v3_40"]})
                jobs = {solver: pool.submit(launch, case, solver, 40) for solver in ("v4", "v3")}
                results = {solver: future.result() for solver, future in jobs.items()}
                entry = {"family": family, "case_id": case, "screen": 6.4e-6,
                         "physical_validity": {solver: result["physical_validity"] for solver, result in results.items()},
                         "resource_validity": {solver: result["resource_observation_valid"] for solver, result in results.items()}}
                completed.append(entry)
                if not all(result["physical_validity"] for result in results.values()) or not results["v4"]["resource_observation_valid"]:
                    entry["classification"] = "invalid_observation_not_scientific_failure"
                    checkpoint("screen_completed")
                    continue
                gap = results["v4"]["measurement"]["energy"] - results["v3"]["measurement"]["energy"]
                entry.update(v4_energy=results["v4"]["measurement"]["energy"], v3_energy=results["v3"]["measurement"]["energy"],
                             v4_minus_v3=gap, screen_ratio=gap / entry["screen"],
                             allocation_difference_cuts=allocation_differences(results["v4"], results["v3"]))
                entry["classification"] = "positive_awaiting_repeat_refinement" if gap >= 2 * entry["screen"] else "below_robust_screen"
                print(json.dumps({"screen_completed": entry, "accounting": cpu_accounting()}), flush=True)
                checkpoint("first_positive_or_screen_completed")
                if gap < 2 * entry["screen"]:
                    continue
                checkpoint("confirming_positive", {"case": case, "solvers": ["repeat_v4_40", "teacher_60"]})
                repeat_job = pool.submit(launch, case, "v4", 40, run_label="repeat_v4_40")
                teacher_job = pool.submit(launch, case, "teacher", 60,
                                          seed=ROOT / "runs" / case / "v3_40/state.npz")
                repeat = repeat_job.result()
                teacher = teacher_job.result()
                entry["repeat_physical_validity"] = repeat["physical_validity"]
                entry["repeat_resource_validity"] = repeat["resource_observation_valid"]
                entry["teacher_physical_validity"] = teacher["physical_validity"]
                if repeat["physical_validity"] and repeat["resource_observation_valid"] and teacher["physical_validity"]:
                    lower = teacher["measurement"]["energy"]
                    if min(results["v4"]["measurement"]["energy"], repeat["measurement"]["energy"]) - lower >= 2 * entry["screen"]:
                        record = measured_record(family, case, ROOT, "teacher_60")
                        records.append(record)
                        confirmed.add(family)
                        entry["classification"] = "robust_repeated_refined_gap"
                        entry["reference_energy"] = lower
                        entry["confirmed_gaps"] = record["baseline_gaps"]
                    else:
                        entry["classification"] = "positive_not_confirmed"
                else:
                    entry["classification"] = "confirmation_invalid_not_scientific_failure"
                checkpoint("confirmation_completed")
                print(json.dumps({"confirmation": entry["classification"], "case": case,
                                  "families_confirmed": sorted(confirmed), "accounting": cpu_accounting()}), flush=True)
            if len(confirmed) == 4:
                stop_reason = "all_four_families_have_two_robust_cases"
                break
            if stop_reason == "conservative_cpu_reserve":
                break
    accounting = cpu_accounting()
    accounting.update(started_utc=started, ended_utc=stamp(), stop_reason=stop_reason,
                      configuration_count=len(completed), formal_admission_run=False)
    write_json(ROOT / "SEARCH_ACCOUNTING.json", accounting)
    write_json(ROOT / "SUMMARY.json", {"variants": completed, "accounting": accounting})
    write_json(ROOT / "PROPOSAL.json", {"cases": records, "suite_complete": len(records) == 8,
                                      "families": list(FAMILIES), "accounting": accounting,
                                      "ground_energies_certified": False,
                                      "formal_admission_run": False, "public_assets_changed": False})
    checkpoint("complete" if len(records) == 8 else "bounded_search_partial")
    print(json.dumps({"final_records": len(records), "accounting": accounting}), flush=True)


if __name__ == "__main__":
    main()
