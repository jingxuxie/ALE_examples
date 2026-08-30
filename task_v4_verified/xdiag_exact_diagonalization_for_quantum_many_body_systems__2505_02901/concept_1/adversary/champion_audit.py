import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "adversary" / "champion_audit"
SUMMARY_PATH = ROOT / "adversary" / "champion_audit_summary.json"
SUBMISSION = ROOT / "champions" / "generation_1"
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
from fleet import load_fleet, objective, route_array
from isolation import run_isolated
from physics import QuantumCase
from scoring import strict_json, validate
from relaxed_bound import ring_bounds


FAMILIES = ("drifting_priors", "sector_congestion", "frustrated_bridges")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physics_identity(case):
    content = {key: value for key, value in case.items()
               if key not in ("case_id", "prior_scenarios", "calibration_test")}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def generate():
    pool = []
    for family in FAMILIES:
        first = ROOT / "evaluator" / "hidden" / "fleets" / (family + "_0")
        second = ROOT / "evaluator" / "hidden" / "fleets" / (family + "_1")
        manifest = strict_json((second / "manifest.json").read_text())
        sources = [(first, "unit_0"), (first, "unit_3"), (second, manifest["cases"][-1]["case_id"])]
        for directory, identifier in sources:
            case = strict_json((directory / (identifier + ".json")).read_text())
            pool.append({"family": family, "configuration": case,
                         "configuration_path": directory / (identifier + ".json"),
                         "response_path": directory / (identifier + ".npz"),
                         "physics_id": physics_identity(case)})
    specifications = []
    for family_index, family in enumerate(FAMILIES):
        for variant in range(4):
            seed = 202608280 + family_index * 101 + variant * 17
            random = np.random.RandomState(seed)
            count = (6, 7, 8, 6)[variant]
            own = [entry for entry in pool if entry["family"] == family]
            others = [entry for entry in pool if entry["family"] != family]
            selected = own + [others[index] for index in random.choice(len(others), count - len(own), replace=False)]
            random.shuffle(selected)
            identifier = "audit_{}_{}".format(family, variant)
            directory = AUDIT / "inputs" / identifier
            directory.mkdir(parents=True, exist_ok=True)
            manifest = {"schema_version": 1, "fleet_id": identifier,
                        "shared_sensor_count": (4, 3, 5, 4)[variant],
                        "shared_action_count": (4, 4, 3, 5)[variant],
                        "sensor_usage_caps": {}, "action_usage_caps": {}, "cases": []}
            cap_scale = (1.0, 0.85, 1.15, 0.72)[variant]
            if family == "sector_congestion":
                cap_scale *= 0.85
            for index, multiplier in enumerate((1.6, 1.8, 1.5, 4.0, 3.5, 3.0, 3.8)):
                manifest["sensor_usage_caps"]["sensor_{}".format(index)] = max(3, int(count * multiplier * cap_scale))
            action_scale = (10.0, 7.0, 11.0, 5.0)[variant]
            for index in range(10):
                manifest["action_usage_caps"]["feedback_{}".format(index)] = max(count, int(count * action_scale * random.uniform(0.8, 1.2)))
            concentration = (0.90, 0.99, 0.80, 0.95)[variant]
            calibration_retention = (0.85, 0.60, 1.0, 0.35)[variant]
            origins = []
            for index, entry in enumerate(selected):
                case = copy.deepcopy(entry["configuration"])
                case_id = "ring_{}".format(index)
                case["case_id"] = case_id
                regime_ids = [regime["regime_id"] for regime in case["regimes"]]
                background = random.dirichlet(np.ones(len(regime_ids)))
                priors = [background, random.dirichlet(np.full(len(regime_ids), 0.4))]
                priors += [concentration * np.eye(len(regime_ids))[regime] + (1 - concentration) * background
                           for regime in range(len(regime_ids))]
                case["prior_scenarios"] = [{"scenario_id": "ambiguity_{}".format(prior_index),
                                             "prior": dict(zip(regime_ids, prior.tolist()))}
                                            for prior_index, prior in enumerate(priors)]
                probe = case["calibration_test"]
                for regime_id in regime_ids:
                    likelihood = np.array([probe["likelihood_by_regime"][regime_id][result] for result in probe["results"]])
                    likelihood = calibration_retention * likelihood + (1 - calibration_retention) / len(likelihood)
                    probe["likelihood_by_regime"][regime_id] = dict(zip(probe["results"], likelihood.tolist()))
                    assert abs(likelihood.sum() - 1) < 1e-12 and np.min(likelihood) >= 0
                assert physics_identity(case) == entry["physics_id"]
                assert 6 <= case["L"] <= 10 and len(priors) <= 6
                for prior in priors:
                    assert abs(prior.sum() - 1) < 1e-12 and np.min(prior) >= 0
                configuration = case_id + ".json"
                responses = case_id + ".npz"
                write_json(directory / configuration, case)
                shutil.copyfile(entry["response_path"], directory / responses)
                manifest["cases"].append({"case_id": case_id, "configuration": configuration, "responses": responses})
                origins.append({"case_id": case_id, "physics_id": entry["physics_id"],
                                "source": str(entry["configuration_path"].relative_to(ROOT)),
                                "source_configuration_sha256": digest(entry["configuration_path"]),
                                "source_responses_sha256": digest(entry["response_path"])})
            write_json(directory / "manifest.json", manifest)
            specifications.append({"id": identifier, "family": family, "variant": variant, "seed": seed,
                                   "directory": str(directory.relative_to(ROOT)), "ring_count": count,
                                   "shared_sensor_count": manifest["shared_sensor_count"],
                                   "shared_action_count": manifest["shared_action_count"],
                                   "sensor_capacity_scale": cap_scale, "action_capacity_scale": action_scale,
                                   "prior_concentration": concentration,
                                   "calibration_signal_retention": calibration_retention, "origins": origins})
    write_json(AUDIT / "stress_specs.json", specifications)
    write_json(AUDIT / "provenance.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "champion_source": "attempts/v_1/solve.py (original generation only)",
        "champion_sha256": digest(ROOT / "champions" / "generation_1" / "solve.py"),
        "repaired_score_source": "attempts/v_1.repaired_evaluation.json",
        "repaired_fresh_attempt_accessed": False,
        "raw_physics_changed": False,
        "construction": "Nine source rings, three per original physical family, recombined into twelve fleets; six normalized ambiguity priors, calibrated classical-probe confusion, shared manufacturing limits, and structural sensor/action capacities vary within the published envelope.",
        "scoring": "Existing strict policy validator and isolated 60s/one-CPU/2GiB runner; regime-resolved losses independently recomputed with direct quantum evolution. A private in-memory physics cache is reused only when raw Hamiltonian, initial state, sensors, bridges, actions and loss are identical.",
        "bound": "Existing ring_bounds relaxation: each ring/prior gets its own Bayes-optimal adaptive tree, with realized path budgets retained but fleet sharing/capacities removed. 1e-4 absolute loss guard. This is optimistic headroom, not a feasible quality certificate.",
        "failure_rule": "A genuine quality failure requires an independently validated feasible alternative at least 3% better than the champion and an absolute loss reduction at least 0.005. Residual relaxation gaps and protocol/resource-only failures do not satisfy this rule.",
        "new_targets": None})
    return specifications


class PhysicsAudit:
    def __init__(self):
        self.models = {}
        self.open_tables = {}
        self.errors = {}

    def score(self, manifest, data, policy):
        configurations = [entry["configuration"] for entry in data]
        sensor_usage, action_usage = validate(manifest, configurations, policy)
        case_losses = {}
        for entry, case_policy in zip(data, policy["cases"]):
            case = entry["configuration"]
            identity = physics_identity(case)
            if identity not in self.models:
                self.models[identity] = QuantumCase(case, propagators=False)
                self.errors[identity] = 0.0
            model = self.models[identity]
            if case_policy["root"] == "open":
                if identity not in self.open_tables:
                    self.open_tables[identity] = model.open_table()
                table = self.open_tables[identity]
                self.errors[identity] = max(self.errors[identity], float(np.max(np.abs(table - entry["table"]["open"]))))
                regime_losses = table[:, entry["action_index"][case_policy["action"]]]
            else:
                regime_losses = np.zeros(len(case["regimes"]))
                for result, branch in enumerate(case_policy["branches"]):
                    for sector, second in enumerate(branch["seconds"]):
                        probability, numerator = model.route(branch["first_sensor"], sector, second["second_sensor"])
                        catalog = route_array(entry, branch["first_sensor"], sector, second["second_sensor"])
                        self.errors[identity] = max(self.errors[identity], float(np.max(np.abs(numerator - catalog))))
                        for outcome, action in enumerate(second["actions"]):
                            regime_losses += entry["likelihood"][result] * numerator[:, outcome, entry["action_index"][action]]
            values = entry["priors"] @ regime_losses
            assert np.isfinite(values).all() and float(np.min(values)) >= -1e-7
            assert self.errors[identity] < 2e-7
            case_losses[case["case_id"]] = dict(zip([scenario["scenario_id"] for scenario in case["prior_scenarios"]], values.tolist()))
        value = max(loss for losses in case_losses.values() for loss in losses.values())
        catalog_error = abs(value - objective(data, policy["cases"]))
        assert catalog_error < 2e-7
        return {"objective": value, "scenario_losses": case_losses, "sensor_usage": sensor_usage,
                "action_usage": action_usage, "catalog_objective_error": catalog_error}

    def save(self):
        directory = AUDIT / "physics_cache"
        directory.mkdir(parents=True, exist_ok=True)
        records = {}
        for identity, model in self.models.items():
            arrays = {}
            if identity in self.open_tables:
                arrays["open"] = self.open_tables[identity]
            for index, (route, values) in enumerate(sorted(model.routes.items())):
                arrays["route_{}".format(index)] = values[1]
                arrays["probability_{}".format(index)] = values[0]
            filename = identity + ".npz"
            np.savez_compressed(directory / filename, **arrays)
            records[identity] = {"archive": "physics_cache/" + filename,
                                 "route_keys_in_archive_order": [list(key) for key in sorted(model.routes)],
                                 "maximum_direct_vs_catalog_error": self.errors[identity],
                                 "route_count": len(model.routes)}
        write_json(AUDIT / "physics_validation.json", {"models": records,
                   "maximum_error": max(self.errors.values(), default=0.0),
                   "independent_direct_evolution": True,
                   "prior_and_calibration_changes_excluded_from_cache_key_only_because_they_do_not_change_quantum_dynamics": True})


def execute(submission, directory, destination):
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="xdiag_champion_audit_") as temporary:
            response, seconds = run_isolated(submission, directory, temporary, 60)
        policy = strict_json(response)
        write_json(destination, policy)
        return {"executed": True, "seconds": seconds}, policy
    except Exception as error:
        return {"executed": False, "seconds": time.monotonic() - started,
                "reason": str(error), "classification": "protocol_or_resource_only_not_scientific_failure"}, None


def summarize(records, specifications, variants, elapsed, physics_error, incomplete_reason=None):
    valid = [record for record in records if record.get("comparison_valid")]
    failures = []
    for record in valid:
        alternatives = [{"kind": "same_case_baseline", "score": record["baseline"]}]
        alternatives += [{"kind": "equivalent_case_order_portfolio", "score": variant["score"]}
                         for variant in variants if variant.get("valid") and variant["id"] == record["id"]]
        best = min(alternatives, key=lambda entry: entry["score"]["objective"])
        champion = record["champion"]["objective"]
        reduction = champion - best["score"]["objective"]
        improvement = 100 * reduction / champion
        if reduction >= 0.005 and improvement >= 3.0:
            failures.append({"id": record["id"], "family": record["family"],
                             "root_cause_cluster": "capacity_allocation_or_shared_design_search_gap" if best["kind"] == "same_case_baseline" else "case_order_sensitive_coupled_search",
                             "witness_kind": best["kind"], "absolute_loss_reduction": reduction,
                             "relative_champion_improvement_percent": improvement,
                             "champion_objective": champion, "feasible_alternative_objective": best["score"]["objective"]})
    families = {}
    for family in FAMILIES:
        subset = [record for record in valid if record["family"] == family]
        families[family] = {"completed_valid_comparisons": len(subset),
                            "mean_champion_improvement_over_baseline_percent": float(np.mean([entry["improvement_percent"] for entry in subset])) if subset else None,
                            "maximum_remaining_relaxed_headroom_percent": max((entry["remaining_relaxed_headroom_percent"] for entry in subset), default=None),
                            "headroom_at_most_one_percent": sum(entry["remaining_relaxed_headroom_percent"] <= 1 for entry in subset),
                            "unresolved_relaxation_gaps_above_three_percent": sum(entry["remaining_relaxed_headroom_percent"] > 3 for entry in subset),
                            "genuine_failures": sum(entry["family"] == family for entry in failures)}
    detail_directory = str(AUDIT.relative_to(ROOT))
    summary = {"completed_utc": datetime.now(timezone.utc).isoformat(),
               "counters": {"stress_fleets_generated": len(specifications), "stress_fleets_evaluated": len(records),
                            "valid_comparisons": len(valid), "protocol_resource_or_audit_errors": len(records) - len(valid),
                            "unique_source_physics": 9, "equivalent_order_variants_evaluated": len(variants),
                            "genuine_failures": len(failures), "ratchet_generations_built": 0, "fresh_agents_launched": 0},
               "per_family_results": families, "genuine_failure_found": bool(failures),
               "ratchet_recommended": bool(failures), "failures": failures,
               "reason": "A feasible independently checked same-instance alternative demonstrates a substantive champion quality gap; review the witness before building a ratchet." if failures else "No trustworthy new scientific failure was found in the sampled space. Relaxation gaps alone do not prove improvability, and protocol/resource-only failures are not counted as science. No forced ratchet is recommended.",
               "incomplete_reason": incomplete_reason,
               "elapsed_seconds": elapsed, "maximum_independent_physics_error": physics_error,
               "resource_limits": {"seconds_per_fleet": 60, "logical_cpus": 1, "address_space_bytes": 2147483648},
               "new_targets_created": False, "repaired_fresh_attempt_accessed": False,
               "detail_files": {"generator": "adversary/champion_audit.py", "specifications": detail_directory + "/stress_specs.json",
                                "results": detail_directory + "/results.json", "variants": detail_directory + "/variants.json",
                                "provenance": detail_directory + "/provenance.json",
                                "physics_validation": detail_directory + "/physics_validation.json",
                                "champion": str(SUBMISSION / "solve.py"), "archived_repaired_score": "champions/generation_1/repaired_evaluation.json"}}
    write_json(SUMMARY_PATH, summary)
    text = ["# Bounded champion audit", "", summary["reason"], "",
            "Completed valid comparisons: {} / {}.".format(len(valid), len(specifications)),
            "Genuine failures: {}. New ratchet tasks: 0.".format(len(failures)),
            "The original 6%/3% targets were not used. No new passing target was introduced.",
            "Each stress fleet has its own baseline and conservatively guarded relaxed bound.",
            "Direct quantum evolution independently checks both submitted policies; physics caching only reuses identical raw dynamics.", ""]
    for family, values in families.items():
        text.append("- {}: {} valid comparisons; {} substantiated failures; {} unresolved optimistic-bound gaps above 3%.".format(family, values["completed_valid_comparisons"], values["genuine_failures"], values["unresolved_relaxation_gaps_above_three_percent"]))
    if incomplete_reason:
        text.extend(["", "Bounded stop: " + incomplete_reason])
    (AUDIT / "SUMMARY.md").write_text("\n".join(text) + "\n")
    return summary


def main():
    global AUDIT, SUMMARY_PATH, SUBMISSION
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, default=SUBMISSION)
    parser.add_argument("--reuse-inputs", action="store_true")
    parser.add_argument("--output-tag")
    arguments = parser.parse_args()
    source_audit = AUDIT
    SUBMISSION = arguments.submission.resolve()
    if arguments.output_tag:
        if not all(character.isalnum() or character in "_-" for character in arguments.output_tag):
            parser.error("output tag must contain only letters, numbers, underscores or hyphens")
        AUDIT = ROOT / "adversary" / ("champion_audit_" + arguments.output_tag)
        SUMMARY_PATH = ROOT / "adversary" / ("champion_audit_" + arguments.output_tag + "_summary.json")
        if AUDIT.exists() or SUMMARY_PATH.exists():
            parser.error("choose a new output tag to preserve earlier audit results")
    elif SUBMISSION != (ROOT / "champions" / "generation_1").resolve():
        parser.error("a different submission requires --output-tag to preserve the original audit")
    started = time.monotonic()
    deadline = started + 620
    if arguments.reuse_inputs:
        specifications = strict_json((source_audit / "stress_specs.json").read_text())
        provenance = strict_json((source_audit / "provenance.json").read_text())
        write_json(AUDIT / "stress_specs.json", specifications)
        write_json(AUDIT / "provenance.json", provenance)
    else:
        specifications = generate()
    provenance = strict_json((AUDIT / "provenance.json").read_text())
    provenance["tested_submission"] = str(SUBMISSION)
    provenance["tested_solver_sha256"] = digest(SUBMISSION / "solve.py")
    provenance["reuse_existing_stress_inputs"] = arguments.reuse_inputs
    write_json(AUDIT / "provenance.json", provenance)
    print("generated twelve stress fleets from nine independently reusable ring Hamiltonians", flush=True)
    physics = PhysicsAudit()
    records = []
    variants = []
    stopped = None
    for specification in specifications:
        if time.monotonic() > deadline - 90:
            stopped = "Conservative global audit wall budget; remaining fleets were not run."
            break
        directory = ROOT / specification["directory"]
        manifest, data = load_fleet(directory)
        record = {"id": specification["id"], "family": specification["family"]}
        scenario_bounds = [ring_bounds(entry) for entry in data]
        relaxed = max(max(values) for values in scenario_bounds)
        guarded = max(0, relaxed - 1e-4)
        record.update({"relaxed_objective_lower_bound": relaxed, "guarded_lower_bound": guarded,
                       "numeric_guard_in_loss": 1e-4, "ring_scenario_bounds": scenario_bounds})
        policies = {}
        for role, submission in (("baseline", ROOT / "participant" / "baseline"),
                                 ("champion", SUBMISSION)):
            run, policy = execute(submission, directory, AUDIT / "policies" / (specification["id"] + "_" + role + ".json"))
            record[role + "_run"] = run
            if policy is not None:
                try:
                    record[role] = physics.score(manifest, data, policy)
                    policies[role] = policy
                except Exception as error:
                    record[role + "_validation_error"] = str(error)
        record["comparison_valid"] = len(policies) == 2
        if record["comparison_valid"]:
            baseline = record["baseline"]["objective"]
            champion = record["champion"]["objective"]
            if guarded > min(baseline, champion) + 2e-7:
                raise AssertionError("relaxed bound exceeds a feasible exact score")
            record.update({"improvement_percent": 100 * (1 - champion / baseline),
                           "baseline_improvement_upper_bound_percent": 100 * (1 - guarded / baseline),
                           "remaining_relaxed_headroom_percent": 100 * (1 - guarded / champion),
                           "headroom_is_optimistic_not_achievability": True})
        records.append(record)
        write_json(AUDIT / "results.json", records)
        physics.save()
        summary = summarize(records, specifications, variants, time.monotonic() - started,
                            max(physics.errors.values(), default=0.0), "audit running")
        print(json.dumps({"id": record["id"], "valid": record["comparison_valid"],
                          "improvement_percent": record.get("improvement_percent"),
                          "remaining_relaxed_headroom_percent": record.get("remaining_relaxed_headroom_percent"),
                          "champion_seconds": record["champion_run"]["seconds"]}), flush=True)
        if summary["genuine_failure_found"]:
            print("GENUINE_FAILURE " + json.dumps(summary["failures"]), flush=True)
    candidates = sorted([record for record in records if record.get("comparison_valid")
                         and record["remaining_relaxed_headroom_percent"] > 3],
                        key=lambda record: -record["remaining_relaxed_headroom_percent"])
    for record in candidates[:2]:
        if time.monotonic() > deadline - 75:
            break
        source = ROOT / next(specification["directory"] for specification in specifications if specification["id"] == record["id"])
        destination = AUDIT / "variant_inputs" / record["id"]
        shutil.copytree(source, destination, dirs_exist_ok=True)
        manifest = strict_json((destination / "manifest.json").read_text())
        manifest["cases"] = list(reversed(manifest["cases"]))
        write_json(destination / "manifest.json", manifest)
        run, policy = execute(SUBMISSION, destination,
                              AUDIT / "variant_policies" / (record["id"] + ".json"))
        variant = {"id": record["id"], "run": run, "valid": False,
                   "transformation": "reverse case order only; exactly the same physical fleet and constraints"}
        if policy is not None:
            original_manifest, data = load_fleet(source)
            by_id = {case["case_id"]: case for case in policy["cases"]}
            policy["cases"] = [by_id[entry["case_id"]] for entry in original_manifest["cases"]]
            try:
                variant["score"] = physics.score(original_manifest, data, policy)
                variant["valid"] = True
                write_json(AUDIT / "variant_policies" / (record["id"] + "_restored.json"), policy)
            except Exception as error:
                variant["reason"] = str(error)
        variants.append(variant)
        write_json(AUDIT / "variants.json", variants)
        summary = summarize(records, specifications, variants, time.monotonic() - started,
                            max(physics.errors.values(), default=0.0), "audit running")
        print("variant " + json.dumps({"id": record["id"], "valid": variant["valid"],
                                         "objective": variant.get("score", {}).get("objective")}), flush=True)
        if summary["genuine_failure_found"]:
            print("GENUINE_FAILURE " + json.dumps(summary["failures"]), flush=True)
    write_json(AUDIT / "variants.json", variants)
    physics.save()
    summary = summarize(records, specifications, variants, time.monotonic() - started,
                        max(physics.errors.values(), default=0.0), stopped)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
