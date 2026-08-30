import itertools
import json
import math
import os
from collections import Counter

import numpy as np
from scipy.optimize import linprog

from build_batch import (
    CASOracle, ENERGY_SHIFT, FAMILIES, OWNED, SEEDS, TARGET, immutable_manifest,
    increments, require, restriction_diagnostics, seed_embedding, sha256,
    signed_orders, stress_model, validate_model, write_json,
)


MASTER_SEED = 202608280271
CONTROL_ROWS, CONTROL_COLUMNS = np.triu_indices(7, 1)
TRIPLE_MASKS = np.array([mask for mask in range(128) if mask.bit_count() == 3])
LOW_MASKS = np.array([mask for mask in range(128) if mask.bit_count() <= 3])
PARENT_LIMIT = 1e-6


def controls_of(model):
    return np.concatenate([
        np.asarray(model[field])[3:10, 3:10][CONTROL_ROWS, CONTROL_COLUMNS]
        for field in ("hopping", "density")
    ])


def controlled_model(template, controls):
    model = {"family": "mixed", "orbital_energy": list(template["orbital_energy"])}
    for field, values in zip(("hopping", "density"), np.split(controls, 2)):
        matrix = np.array(template[field])
        matrix[CONTROL_ROWS + 3, CONTROL_COLUMNS + 3] = values
        matrix[CONTROL_COLUMNS + 3, CONTROL_ROWS + 3] = values
        model[field] = matrix.tolist()
    return model


def triple_values(model):
    oracle = CASOracle(model)
    table = np.zeros(128)
    table[LOW_MASKS] = [oracle.energy(int(mask)) for mask in LOW_MASKS]
    return increments(table)[TRIPLE_MASKS]


def nullspace_model(template):
    controls = controls_of(template)
    step = 2e-5
    jacobian = np.empty((35, 42))
    for column in range(42):
        displacement = np.zeros(42)
        displacement[column] = step
        forward = triple_values(controlled_model(template, controls + displacement))
        backward = triple_values(controlled_model(template, controls - displacement))
        jacobian[:, column] = (forward - backward) / (2 * step)
    left_vectors, singular_values, right_vectors = np.linalg.svd(jacobian, full_matrices=True)
    basis = right_vectors[35:].T
    require(basis.shape == (42, 7), "unexpected triple-Jacobian nullspace shape")
    null_residual = float(np.max(np.abs(jacobian @ basis)))
    require(null_residual < 1e-12, "Jacobian nullspace residual too large")
    directional_residuals = []
    for column in range(7):
        displacement = basis[:, column] * 5e-5
        forward = triple_values(controlled_model(template, controls + displacement))
        backward = triple_values(controlled_model(template, controls - displacement))
        directional_residuals.append(float(np.max(np.abs((forward - backward) / 1e-4))))
    return controls, jacobian, basis, {
        "shape": [35, 42], "central_difference_step_eh": step,
        "jacobian_model_calls": 84, "null_direction_validation_model_calls": 14,
        "singular_values": singular_values.tolist(),
        "rank_at_relative_tolerance_1e-8": int(np.sum(singular_values > singular_values[0] * 1e-8)),
        "nullspace_dimension_used": 7, "jacobian_nullspace_max_residual": null_residual,
        "independent_null_direction_derivative_maxima": directional_residuals,
        "baseline_triple_maximum_eh": float(np.max(np.abs(triple_values(template)))),
    }


def permute_virtuals(model, permutation):
    site_order = np.r_[np.arange(3), permutation + 3]
    result = {"family": "mixed", "orbital_energy": np.asarray(model["orbital_energy"])[site_order].tolist()}
    for field in ("hopping", "density"):
        result[field] = np.asarray(model[field])[np.ix_(site_order, site_order)].tolist()
    mask_map = np.array([
        sum(1 << int(permutation[position]) for position in range(8) if mask & (1 << position))
        for mask in range(256)
    ])
    return result, mask_map, site_order


def check_gauge_on_diversified_core(model, displacement):
    original = {"family": "mixed", "orbital_energy": (np.asarray(model["orbital_energy"][:10]) + displacement - ENERGY_SHIFT).tolist()}
    original["hopping"] = np.asarray(model["hopping"])[:10, :10].tolist()
    density = np.asarray(model["density"])[:10, :10] - (displacement[:, None] + displacement[None, :]) / 2
    np.fill_diagonal(density, 0)
    original["density"] = density.tolist()
    embedded = {"family": "mixed", "orbital_energy": model["orbital_energy"][:10],
                "hopping": np.asarray(model["hopping"])[:10, :10].tolist(),
                "density": np.asarray(model["density"])[:10, :10].tolist()}
    original_oracle, embedded_oracle = CASOracle(original), CASOracle(embedded)
    matrix_error = float(np.max(np.abs(embedded_oracle.matrix - original_oracle.matrix - np.eye(120) * 2.7)))
    table_error = max(abs(embedded_oracle.energy(mask) - original_oracle.energy(mask)) for mask in range(128))
    require(matrix_error < 1e-12 and table_error < 1e-11, "diversified-core gauge identity failed")
    return {"diversified_core_gauge_matrix_max_error_eh": matrix_error,
            "diversified_core_gauge_all128_max_error_eh": table_error}


def pairwise_summary(vectors):
    differences = [np.asarray(left) - right for left, right in itertools.combinations(vectors, 2)]
    return {
        "pair_count": len(differences),
        "maxnorm_min_median_max": [float(function([np.max(np.abs(delta)) for delta in differences])) for function in (np.min, np.median, np.max)],
        "rms_min_median_max": [float(function([np.sqrt(np.mean(delta ** 2)) for delta in differences])) for function in (np.min, np.median, np.max)],
    }


def main():
    os.umask(0o077)
    source = OWNED / "batch_01"
    output = OWNED / "batch_02"
    require(len(list(OWNED.glob("batch_??"))) <= 2 and source.is_dir(), "second and final batch requires first batch")
    require(not (output / "cases.npz").exists() and not (output / "score.json").exists(), "refusing to replace an already built or evaluated second batch")
    output.mkdir(mode=0o700, exist_ok=True)
    manifest = immutable_manifest()
    source_provenance = json.loads((source / "provenance.json").read_text())
    require(manifest == source_provenance["input_sha256"], "inputs changed since first batch")
    source_models = json.loads((source / "models.json").read_text())
    source_tables = np.load(source / "cases.npz", allow_pickle=False)["energies"]
    source_diagnostics = json.loads((source / "diagnostics.json").read_text())
    target = json.loads(TARGET.read_text())
    bounds = np.r_[np.full(21, target["hopping_bound_eh"]), np.full(21, target["density_bound_eh"])]
    seeds, seed_diagnostics, nullspaces, null_diagnostics = {}, {}, {}, {}
    original_models, seed_tables = {}, {}
    for name in SEEDS:
        original, embedded, table, diagnostic = seed_embedding(name)
        original_models[name], seed_tables[name] = original, table
        seeds[name], seed_diagnostics[name] = embedded, diagnostic
        controls, jacobian, basis, null_diagnostic = nullspace_model(embedded)
        proposal_basis = basis
        if name == "fresh_b1":
            left_vectors, singular_values, right_vectors = np.linalg.svd(jacobian, full_matrices=True)
            first_near_null = int(np.sum(singular_values > 2e-6))
            proposal_basis = right_vectors[first_near_null:].T
        null_diagnostic.update(
            proposal_basis_dimension=proposal_basis.shape[1],
            proposal_basis_mode="bounded_truncated_SVD_near_null" if name == "fresh_b1" else "exact_seven_dimensional_Jacobian_nullspace",
            proposal_basis_max_singular_value=float(np.linalg.norm(jacobian @ proposal_basis, 2)),
            near_null_cutoff=2e-6 if name == "fresh_b1" else None,
        )
        nullspaces[name] = (controls, proposal_basis)
        null_diagnostics[name] = null_diagnostic
        np.savez_compressed(output / f"nullspace_{name}.npz", controls=controls, jacobian=jacobian, basis=basis, proposal_basis=proposal_basis)
        print(json.dumps({"seed": name, "nullspace_prepared": null_diagnostic}), flush=True)
    write_json(output / "seed_models.json", {"original": original_models, "gauge_embedded": seeds})
    write_json(output / "seed_diagnostics.json", seed_diagnostics)
    write_json(output / "nullspace_diagnostics.json", null_diagnostics)
    np.savez_compressed(output / "seed_tables.npz", **seed_tables)
    streams = np.random.SeedSequence(MASTER_SEED).spawn(20)
    configurations = list(itertools.combinations(range(11), 3))
    configuration_positions = {configuration: index for index, configuration in enumerate(configurations)}
    models, tables, diagnostics, provenance = [], [], [], []
    core_tables, core_controls, core_names = [], [], []
    for index in range(120):
        family = FAMILIES[index % 6]
        if family != "mixed":
            model, table = source_models[index], source_tables[index]
            oracle = CASOracle(model)
            checks = validate_model(model, oracle, table)
            identity = dict(source_provenance["cases"][index])
            identity["ordinary_control_source"] = "batch_01: identical independently sampled ordinary control, not resampled after outcomes"
        else:
            mixed_index = index // 6
            name = tuple(SEEDS)[mixed_index % 2]
            variant = mixed_index // 2
            draw_seed = int(streams[mixed_index].generate_state(1, dtype=np.uint64)[0])
            generator = np.random.default_rng(draw_seed)
            controls, basis = nullspaces[name]
            rejections = Counter()
            accepted = False
            for trial in range(3000):
                if name == "fresh_b1":
                    amplitude_limit = float(generator.uniform(0.015, 0.03))
                    constraint = np.r_[basis, -basis]
                    allowances = np.r_[np.minimum(bounds - controls - 1e-5, amplitude_limit),
                                       np.minimum(bounds + controls - 1e-5, amplitude_limit)]
                    result = linprog(generator.normal(size=basis.shape[1]), A_ub=constraint, b_ub=allowances,
                                     bounds=[(None, None)] * basis.shape[1], method="highs",
                                     options={"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9})
                    if not result.success:
                        rejections["near_null_bound_feasibility"] += 1
                        continue
                    displacement = basis @ result.x * generator.uniform(0.8, 0.98)
                    amplitude = float(np.max(np.abs(displacement)))
                else:
                    direction = basis @ generator.normal(size=basis.shape[1])
                    amplitude = float(generator.uniform(0.01, 0.03))
                    displacement = direction * amplitude / np.max(np.abs(direction))
                candidate_controls = controls + displacement
                if np.any(np.abs(candidate_controls) > bounds):
                    rejections["B_control_bounds"] += 1
                    continue
                diversified = controlled_model(seeds[name], candidate_controls)
                parents = triple_values(diversified)
                if np.max(np.abs(parents)) > PARENT_LIMIT:
                    rejections["triple_parent_limit"] += 1
                    continue
                canonical_model, jitter_sigma, jitter_max = stress_model(diversified, generator, variant + 1, jitter_sigma=1e-7)
                final_controls = controls_of(canonical_model)
                if np.any(np.abs(final_controls) > bounds):
                    rejections["jittered_control_bounds"] += 1
                    continue
                final_parents = triple_values(canonical_model)
                if np.max(np.abs(final_parents)) > PARENT_LIMIT:
                    rejections["jittered_triple_parent_limit"] += 1
                    continue
                canonical_oracle = CASOracle(canonical_model)
                spectrum = canonical_oracle.spectrum()
                if spectrum["reference_weight"] < 0.94 or spectrum["gap"] < 0.35 or abs(canonical_oracle.energy(128)) < 3e-4:
                    rejections["public_physics_or_eighth_activity"] += 1
                    continue
                accepted = True
                break
            if not accepted:
                write_json(output / "incomplete_generation.json", {"seed": name, "variant": variant, "rejections": dict(rejections)})
            require(accepted, f"nullspace sampling exhausted for {name} variant {variant}")
            canonical_table = canonical_oracle.all_energies()
            permutation = generator.permutation(8)
            model, mask_map, site_order = permute_virtuals(canonical_model, permutation)
            oracle = CASOracle(model)
            table = oracle.all_energies()
            new_virtual = int(np.flatnonzero(permutation == 7)[0])
            checks = validate_model(model, oracle, table, stress=True, new_virtual=new_virtual)
            checks.update(restriction_diagnostics(canonical_model, canonical_table, seed_tables[name]))
            gauge_displacement = np.asarray(seed_diagnostics[name]["density_gauge_displacement_eh"])
            checks.update(check_gauge_on_diversified_core(canonical_model, gauge_displacement))
            permutation_error = float(np.max(np.abs(table - canonical_table[mask_map])))
            configuration_map = [configuration_positions[tuple(sorted(int(site_order[site]) for site in configuration))] for configuration in configurations]
            matrix_error = float(np.max(np.abs(oracle.matrix - canonical_oracle.matrix[np.ix_(configuration_map, configuration_map)])))
            require(permutation_error < 1e-11 and matrix_error < 1e-12, "virtual permutation covariance failed")
            checks.update(permutation_all256_energy_max_error_eh=permutation_error,
                          permutation_hamiltonian_max_error_eh=matrix_error,
                          old_virtual_hopping_bound_margin_eh=float(np.min(bounds[:21] - abs(final_controls[:21]))),
                          old_virtual_density_bound_margin_eh=float(np.min(bounds[21:] - abs(final_controls[21:]))))
            identity = {
                "index": index, "family": family, "draw_seed": draw_seed,
                "construction": "42_control_35_triple_Jacobian_nullspace_step_plus_independent_jitter_and_active_eighth_then_random_virtual_permutation",
                "seed_witness": name, "variant": variant,
                "accepted_trial": trial, "rejections": dict(rejections),
                "null_step_max_coefficient_eh": amplitude,
                "null_step_basis_mode": null_diagnostics[name]["proposal_basis_mode"],
                "null_step_basis_dimension": basis.shape[1],
                "null_step_l2_eh": float(np.linalg.norm(displacement)),
                "old_control_change_max_eh": float(np.max(np.abs(final_controls - controls))),
                "old_control_change_l2_eh": float(np.linalg.norm(final_controls - controls)),
                "old_coefficient_perturbation_sigma_eh": jitter_sigma,
                "old_coefficient_max_perturbation_eh": jitter_max,
                "old_triple_limit_eh": PARENT_LIMIT,
                "virtual_permutation_new_position_to_canonical": permutation.tolist(),
                "active_added_virtual_index": new_virtual,
                "canonical_mask_for_each_permuted_mask": mask_map.tolist(),
            }
            core_tables.append(canonical_table[:128])
            core_controls.append(final_controls)
            core_names.append(name)
            print(json.dumps({"case_index": index, "seed": name, "trials": trial + 1,
                              "null_step_max_eh": amplitude, "new_virtual_position": new_virtual,
                              "old_triple_max_eh": checks["old_max_abs_triple_eh"],
                              "old_tail_eh": checks["old_signed_tail_ge4_eh"]}), flush=True)
        models.append(model)
        tables.append(table)
        diagnostics.append({**identity, **checks})
        provenance.append(identity)
    require(immutable_manifest() == manifest, "immutable inputs changed during final construction")
    np.savez_compressed(output / "cases.npz", energies=np.asarray(tables))
    np.savez_compressed(output / "canonical_old_cores.npz", energies=np.asarray(core_tables), controls=np.asarray(core_controls), seed_names=np.asarray(core_names))
    write_json(output / "models.json", models)
    write_json(output / "diagnostics.json", diagnostics)
    diversity = {}
    cas2_masks = [mask for mask in range(128) if mask.bit_count() <= 2]
    fourth_masks = [mask for mask in range(128) if mask.bit_count() == 4]
    for name in SEEDS:
        selected_indices = [index for index, source_name in enumerate(core_names) if source_name == name]
        selected_tables = [core_tables[index] for index in selected_indices]
        selected_controls = [core_controls[index] for index in selected_indices]
        selected_terms = [increments(table) for table in selected_tables]
        order4_sums = [math.fsum(terms[fourth_masks]) for terms in selected_terms]
        tails = [math.fsum(value for mask, value in enumerate(terms) if mask.bit_count() >= 4) for terms in selected_terms]
        diversity[name] = {
            "count": len(selected_indices),
            "controls_42_pairwise": pairwise_summary(selected_controls),
            "canonical_old_CAS2_pairwise_eh": pairwise_summary([table[cas2_masks] for table in selected_tables]),
            "canonical_old_fourth_increment_pairwise_eh": pairwise_summary([terms[fourth_masks] for terms in selected_terms]),
            "canonical_old_four_virtual_CAS_pairwise_eh": pairwise_summary([table[fourth_masks] for table in selected_tables]),
            "distinct_CAS2_vectors_rounded_12_decimals": len({tuple(np.round(table[cas2_masks], 12)) for table in selected_tables}),
            "signed_order4_range_eh": [min(order4_sums), max(order4_sums)],
            "signed_tail_ge4_range_eh": [min(tails), max(tails)],
        }
    write_json(output / "diversity.json", {
        "scope": "Twenty distinct, conditioned systems in two seed-derived neighborhoods; not twenty independent witness seeds or IID mixed draws. Core comparisons use canonical labels, removing permutation-only diversity.",
        "seed_groups": diversity,
    })
    mixed = [item for item in diagnostics if item["family"] == "mixed"]
    summary = {
        "case_count": 120, "all_checks_passed": True,
        "family_counts": dict(Counter(model["family"] for model in models)),
        "minimum_reference_weight": min(item["reference_weight"] for item in diagnostics),
        "minimum_gap_eh": min(item["gap"] for item in diagnostics),
        "maximum_residual": max(item["residual"] for item in diagnostics),
        "maximum_independent_energy_error_eh": max(item["independent_full_energy_error_eh"] for item in diagnostics),
        "maximum_independent_residual": max(item["independent_full_residual"] for item in diagnostics),
        "minimum_mixed_reference_weight": min(item["reference_weight"] for item in mixed),
        "minimum_mixed_gap_eh": min(item["gap"] for item in mixed),
        "minimum_active_eighth_singleton_magnitude_eh": min(abs(item["active_added_virtual_singleton_eh"]) for item in mixed),
        "maximum_excluded_eighth_restriction_error_eh": max(item["all_128_excluded_new_orbital_error_eh"] for item in mixed),
        "maximum_old_restriction_drift_eh": max(item["old_128_max_drift_from_seed_eh"] for item in mixed),
        "maximum_permutation_energy_error_eh": max(item["permutation_all256_energy_max_error_eh"] for item in mixed),
        "maximum_permutation_hamiltonian_error_eh": max(item["permutation_hamiltonian_max_error_eh"] for item in mixed),
        "maximum_diversified_gauge_error_eh": max(item["diversified_core_gauge_all128_max_error_eh"] for item in mixed),
        "maximum_old_triple_magnitude_eh": max(item["old_max_abs_triple_eh"] for item in mixed),
        "null_control_step_maxnorm_range_eh": [min(item["old_control_change_max_eh"] for item in mixed), max(item["old_control_change_max_eh"] for item in mixed)],
        "added_virtual_position_histogram": dict(Counter(str(item["active_added_virtual_index"]) for item in mixed)),
        "minimum_B_control_bound_margin_eh": min(min(item["old_virtual_hopping_bound_margin_eh"], item["old_virtual_density_bound_margin_eh"]) for item in mixed),
        "perturbed_mixed_case_count": len(mixed),
        "cases_sha256": sha256(output / "cases.npz"), "models_sha256": sha256(output / "models.json"),
    }
    require(summary["family_counts"] == {family: 20 for family in FAMILIES}, "unbalanced final batch")
    write_json(output / "validation_summary.json", summary)
    write_json(output / "provenance.json", {
        "private": True, "batch": 2, "master_seed": MASTER_SEED,
        "scientific_scope": "Conditioned nullspace-diversified mixed-family stress, not IID; two source-witness neighborhoods, ten cases each",
        "family_counts": summary["family_counts"], "witness_counts": dict(Counter(core_names)),
        "ordinary_controls": "The same 100 independent ordinary draws as batch 1, held fixed without outcome-based replacement",
        "ordinary_source_cases_sha256": sha256(source / "cases.npz"),
        "selection": "Author seed: random exact-Jacobian-nullspace directions. B1: random linear objectives restricted to a bounded 22-dimensional truncated-SVD near-null subspace (cutoff 2e-6), then random radial scaling. Step sizes approximately .01-.03; accept only B coefficient bounds, 1 microhartree actual parent bound, public physical thresholds, and active new orbital. No champion- or tail-error objective or selection.",
        "preflight_refinement": "Before any second-batch cases were saved or evaluated, all 3000 naive exact-null proposals for B1 violated its many nearly saturated B coefficient bounds. Small exact-null linear-feasibility probes also yielded only tiny moves. Thus B1 uses explicitly approximate near-null, not claimed exact-null, directions; author uses exact-null directions. Both retain independent old-coefficient jitter sigma 1e-7 and actual-CAS parent checks.",
        "permutation": "Independent full uniform random permutation of all eight virtual labels per accepted stress model; all 256 CAS energies and full Hamiltonian covariance independently verified",
        "protocol": source_provenance["protocol"], "unchanged_targets_eh": source_provenance["unchanged_targets_eh"],
        "ordering": source_provenance["ordering"], "input_sha256": manifest, "cases": provenance,
    })
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
