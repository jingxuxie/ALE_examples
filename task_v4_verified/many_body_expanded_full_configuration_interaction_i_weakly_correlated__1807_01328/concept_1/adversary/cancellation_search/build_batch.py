import argparse
import hashlib
import itertools
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np


OWNED = Path(__file__).resolve().parent
ROOT = OWNED.parents[2]
CONCEPT = ROOT / "concept_1"
sys.path.insert(0, str(CONCEPT / "participant/workspace"))
from pair_model import CASOracle, FAMILIES, increments, sample_model


SEEDS = {
    "fresh_b1": ROOT / "concept_2/champions/generation_1/submission/witness.json",
    "author_private": ROOT / "concept_2/adversary/known_witness.json",
}
TARGET = ROOT / "concept_2/champions/generation_1/evaluator/hidden/target.json"
OCCUPIED = np.array([-0.45, -0.22, 0.0])
ENERGY_SHIFT = 0.9


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def immutable_manifest():
    paths = [TARGET, *SEEDS.values(), CONCEPT / "participant/workspace/pair_model.py"]
    paths.extend(sorted((CONCEPT / "evaluator").glob("*.py")))
    paths.extend(sorted(path for path in (CONCEPT / "attempts/v_1").rglob("*") if path.is_file()))
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def independent_hamiltonian(model):
    orbital_energy = np.asarray(model["orbital_energy"])
    hopping = np.asarray(model["hopping"])
    density = np.asarray(model["density"])
    configurations = list(itertools.combinations(range(len(orbital_energy)), 3))
    positions = {configuration: index for index, configuration in enumerate(configurations)}
    matrix = np.zeros((len(configurations), len(configurations)))
    for row, configuration in enumerate(configurations):
        matrix[row, row] = math.fsum(orbital_energy[list(configuration)]) + math.fsum(
            density[left, right] for left, right in itertools.combinations(configuration, 2)
        )
        for source in configuration:
            for destination in range(len(orbital_energy)):
                if destination not in configuration:
                    child = tuple(sorted((set(configuration) - {source}) | {destination}))
                    matrix[row, positions[child]] = hopping[source, destination]
    return matrix


def signed_orders(table):
    terms = increments(table)
    result = {}
    for order in range(int(math.log2(len(table))) + 1):
        selected = [float(value) for mask, value in enumerate(terms) if mask.bit_count() == order]
        result[str(order)] = {
            "count": len(selected),
            "signed_sum_eh": math.fsum(selected),
            "positive_sum_eh": math.fsum(value for value in selected if value > 0),
            "negative_sum_eh": math.fsum(value for value in selected if value < 0),
            "absolute_sum_eh": math.fsum(abs(value) for value in selected),
            "max_absolute_eh": max(map(abs, selected), default=0.0),
        }
    return result


def validate_model(model, oracle, table, stress=False, new_virtual=7):
    orbital_energy = np.asarray(model["orbital_energy"])
    require(np.array_equal(orbital_energy[:3], OCCUPIED), "occupied energies changed")
    require(bool(np.all((orbital_energy[3:] >= 0.85) & (orbital_energy[3:] <= 2.4))), "virtual range invalid")
    for field in ("hopping", "density"):
        matrix = np.asarray(model[field])
        require(matrix.shape == (11, 11), "matrix shape invalid")
        require(bool(np.isfinite(matrix).all()), "nonfinite coefficients")
        require(bool(np.array_equal(matrix, matrix.T)), "asymmetric coefficients")
        require(bool(np.all(np.diag(matrix) == 0)), "nonzero diagonal")
    require(table.shape == (256,) and bool(np.isfinite(table).all()), "invalid energy table")
    spectrum = oracle.spectrum()
    require(spectrum["reference_weight"] >= 0.94, "reference weight below public threshold")
    require(spectrum["gap"] >= 0.35, "gap below public threshold")
    require(spectrum["residual"] < 1e-11, "full eigenpair residual too large")
    independent = independent_hamiltonian(model)
    matrix_error = float(np.max(np.abs(independent - oracle.matrix)))
    eigenvalues, eigenvectors = np.linalg.eigh(independent)
    energy_error = float(abs(eigenvalues[0] - independent[0, 0] - table[-1]))
    independent_residual = float(np.linalg.norm(independent @ eigenvectors[:, 0] - eigenvalues[0] * eigenvectors[:, 0]))
    require(matrix_error < 1e-12 and energy_error < 1e-11, "independent diagonalization disagrees")
    require(independent_residual < 1e-11, "independent residual too large")
    monotonic_violation = max(
        float(table[mask] - table[mask ^ (1 << orbital)])
        for mask in range(1, 256) for orbital in range(8) if mask & (1 << orbital)
    )
    require(monotonic_violation < 1e-11, "CAS variational monotonicity violated")
    terms = increments(table)
    closure_error = abs(math.fsum(terms) - table[-1])
    require(closure_error < 1e-11, "Mobius closure failed")
    if stress:
        new_site = new_virtual + 3
        other_virtuals = [site for site in range(3, 11) if site != new_site]
        require(abs(table[1 << new_virtual]) >= 3e-4, "new virtual is insufficiently active")
        hopping = np.asarray(model["hopping"])
        require(bool(np.all((abs(hopping[:3, new_site]) >= 0.04) & (abs(hopping[:3, new_site]) <= 0.08))), "new occupied hopping invalid")
        require(bool(np.all((abs(hopping[other_virtuals, new_site]) >= 0.05) & (abs(hopping[other_virtuals, new_site]) <= 0.15))), "new virtual hopping invalid")
    return {
        **spectrum,
        "independent_matrix_max_error_eh": matrix_error,
        "independent_full_energy_error_eh": energy_error,
        "independent_full_residual": independent_residual,
        "independent_reference_weight": float(eigenvectors[0, 0] ** 2),
        "independent_gap_eh": float(eigenvalues[1] - eigenvalues[0]),
        "max_variational_violation_eh": monotonic_violation,
        "mobius_closure_error_eh": closure_error,
        "eighth_singleton_eh": float(table[128]),
        "active_added_virtual_index": new_virtual if stress else None,
        "active_added_virtual_singleton_eh": float(table[1 << new_virtual]) if stress else None,
        "signed_orders": signed_orders(table),
    }


def seed_embedding(name):
    target = json.loads(TARGET.read_text())
    witness = json.loads(SEEDS[name].read_text())
    hopping = np.zeros((10, 10))
    hopping[:3, 3:] = target["occupied_virtual_hopping"]
    hopping[3:, :3] = hopping[:3, 3:].T
    hopping[3:, 3:] = witness["virtual_hopping"]
    density = np.asarray(target["background_density"], dtype=float)
    density[3:, 3:] += np.asarray(witness["virtual_density"])
    original = {
        "family": "mixed", "orbital_energy": target["pair_energy_eh"],
        "hopping": hopping.tolist(), "density": density.tolist(),
    }
    original_oracle = CASOracle(original)
    original_table = np.array([original_oracle.energy(mask) for mask in range(128)])
    shifted = np.asarray(target["pair_energy_eh"], dtype=float) + ENERGY_SHIFT
    displacement = np.zeros(10)
    displacement[:3] = shifted[:3] - OCCUPIED
    shifted -= displacement
    shifted[:3] = OCCUPIED
    compensated_density = density + (displacement[:, None] + displacement[None, :]) / 2
    np.fill_diagonal(compensated_density, 0)
    embedded = {
        "family": "mixed", "orbital_energy": shifted.tolist(),
        "hopping": hopping.tolist(), "density": compensated_density.tolist(),
    }
    embedded_oracle = CASOracle(embedded)
    embedded_table = np.array([embedded_oracle.energy(mask) for mask in range(128)])
    matrix_error = float(np.max(np.abs(embedded_oracle.matrix - original_oracle.matrix - np.eye(120) * 3 * ENERGY_SHIFT)))
    table_error = float(np.max(np.abs(embedded_table - original_table)))
    require(matrix_error < 1e-12 and table_error < 1e-11, "exact seed gauge identity failed")
    terms = increments(original_table)
    diagnostics = {
        "seed": name,
        "original_spectrum": original_oracle.spectrum(),
        "embedded_spectrum": embedded_oracle.spectrum(),
        "energy_shift_per_site_eh": ENERGY_SHIFT,
        "constant_three_pair_shift_eh": 3 * ENERGY_SHIFT,
        "density_gauge_displacement_eh": displacement.tolist(),
        "gauge_matrix_max_error_eh": matrix_error,
        "all_128_correlation_max_error_eh": table_error,
        "old_max_abs_triple_eh": max(abs(float(value)) for mask, value in enumerate(terms) if mask.bit_count() == 3),
        "old_signed_tail_ge4_eh": math.fsum(float(value) for mask, value in enumerate(terms) if mask.bit_count() >= 4),
        "signed_orders": signed_orders(original_table),
    }
    return original, embedded, original_table, diagnostics


def stress_model(embedded, generator, variant, jitter_sigma=None):
    orbital_energy = np.r_[embedded["orbital_energy"], generator.uniform(2.0, 2.4)]
    hopping = np.zeros((11, 11))
    density = np.zeros((11, 11))
    hopping[:10, :10] = embedded["hopping"]
    density[:10, :10] = embedded["density"]
    perturbation_sigma = 0.0 if variant == 0 else float(10 ** generator.uniform(-7, -4.7))
    if jitter_sigma is not None:
        perturbation_sigma = jitter_sigma
    orbital_energy[3:10] += generator.normal(0, perturbation_sigma, 7)
    upper_rows, upper_columns = np.triu_indices(10, 1)
    for matrix in (hopping, density):
        changes = generator.normal(0, perturbation_sigma, len(upper_rows))
        matrix[upper_rows, upper_columns] += changes
        matrix[upper_columns, upper_rows] = matrix[upper_rows, upper_columns]
    hopping[:3, 10] = generator.uniform(0.04, 0.08, 3) * generator.choice([-1, 1], 3)
    hopping[3:10, 10] = generator.uniform(0.05, 0.15, 7) * generator.choice([-1, 1], 7)
    hopping[10, :10] = hopping[:10, 10]
    density[:10, 10] = generator.normal(0, 0.1, 10)
    density[10, :10] = density[:10, 10]
    model = {
        "family": "mixed", "orbital_energy": orbital_energy.tolist(),
        "hopping": hopping.tolist(), "density": density.tolist(),
    }
    perturbation_max = max(
        float(np.max(np.abs(orbital_energy[:10] - embedded["orbital_energy"]))),
        float(np.max(np.abs(hopping[:10, :10] - embedded["hopping"]))),
        float(np.max(np.abs(density[:10, :10] - embedded["density"]))),
    )
    return model, perturbation_sigma, perturbation_max


def restriction_diagnostics(model, table, seed_table):
    restricted_model = {
        "family": "mixed", "orbital_energy": model["orbital_energy"][:10],
        "hopping": np.asarray(model["hopping"])[:10, :10].tolist(),
        "density": np.asarray(model["density"])[:10, :10].tolist(),
    }
    oracle = CASOracle(restricted_model)
    restricted_table = np.array([oracle.energy(mask) for mask in range(128)])
    restriction_error = float(np.max(np.abs(table[:128] - restricted_table)))
    require(restriction_error < 1e-11, "added orbital changed an excluded CAS restriction")
    terms = increments(table)
    old_tail = math.fsum(float(terms[mask]) for mask in range(128) if mask.bit_count() >= 4)
    new_tail = math.fsum(float(terms[mask]) for mask in range(128, 256) if mask.bit_count() >= 4)
    return {
        "all_128_excluded_new_orbital_error_eh": restriction_error,
        "old_128_max_drift_from_seed_eh": float(np.max(np.abs(table[:128] - seed_table))),
        "old_max_abs_triple_eh": max(abs(float(terms[mask])) for mask in range(128) if mask.bit_count() == 3),
        "new_max_abs_triple_eh": max(abs(float(terms[mask])) for mask in range(128, 256) if mask.bit_count() == 3),
        "old_signed_tail_ge4_eh": old_tail,
        "new_signed_tail_ge4_eh": new_tail,
        "total_signed_tail_ge4_eh": old_tail + new_tail,
        "old_signed_orders": signed_orders(table[:128]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=(1, 2), default=1)
    parser.add_argument("--seed", type=int, default=202608280173)
    arguments = parser.parse_args()
    os.umask(0o077)
    OWNED.chmod(0o700)
    output = OWNED / f"batch_{arguments.batch:02d}"
    output.mkdir(mode=0o700, exist_ok=False)
    manifest = immutable_manifest()
    seed_models = {}
    seed_tables = {}
    seed_diagnostics = {}
    original_models = {}
    for name in SEEDS:
        original, embedded, table, diagnostics = seed_embedding(name)
        original_models[name] = original
        seed_models[name] = embedded
        seed_tables[name] = table
        seed_diagnostics[name] = diagnostics
    write_json(output / "seed_models.json", {"original": original_models, "gauge_embedded": seed_models})
    write_json(output / "seed_diagnostics.json", seed_diagnostics)
    np.savez_compressed(output / "seed_tables.npz", **seed_tables)
    streams = np.random.SeedSequence(arguments.seed).spawn(120)
    models, tables, diagnostics, provenance = [], [], [], []
    for index, stream in enumerate(streams):
        family = FAMILIES[index % len(FAMILIES)]
        draw_seed = int(stream.generate_state(1, dtype=np.uint64)[0])
        identity = {"index": index, "family": family, "draw_seed": draw_seed}
        if family == "mixed":
            mixed_index = index // 6
            seed_name = tuple(SEEDS)[mixed_index % 2]
            variant = mixed_index // 2
            generator = np.random.default_rng(draw_seed)
            accepted = False
            for trial in range(100):
                model, perturbation_sigma, perturbation_max = stress_model(seed_models[seed_name], generator, variant)
                oracle = CASOracle(model)
                spectrum = oracle.spectrum()
                if spectrum["reference_weight"] >= 0.94 and spectrum["gap"] >= 0.35 and abs(oracle.energy(128)) >= 3e-4:
                    accepted = True
                    break
            require(accepted, "stress admissibility sampling exhausted")
            identity.update(
                construction="conditioned_gauge_embedding_with_active_eighth_virtual",
                seed_witness=seed_name, variant=variant, admissibility_trial=trial,
                old_coefficient_perturbation_sigma_eh=perturbation_sigma,
                old_coefficient_max_perturbation_eh=perturbation_max,
            )
        else:
            model = sample_model(draw_seed, family)
            oracle = CASOracle(model)
            identity["construction"] = "independent_public_sample_model_draw"
        table = oracle.all_energies()
        checks = validate_model(model, oracle, table, stress=family == "mixed")
        if family == "mixed":
            checks.update(restriction_diagnostics(model, table, seed_tables[seed_name]))
        models.append(model)
        tables.append(table)
        diagnostics.append({**identity, **checks})
        provenance.append(identity)
        if (index + 1) % 6 == 0:
            print(json.dumps({"validated_cases": index + 1, "latest_mixed_seed": seed_name,
                              "reference_weight": checks["reference_weight"], "old_tail_eh": checks["old_signed_tail_ge4_eh"]}), flush=True)
    require(Counter(model["family"] for model in models) == Counter({family: 20 for family in FAMILIES}), "batch is not balanced")
    require(immutable_manifest() == manifest, "immutable assets changed during generation")
    np.savez_compressed(output / "cases.npz", energies=np.array(tables))
    write_json(output / "models.json", models)
    write_json(output / "diagnostics.json", diagnostics)
    write_json(output / "provenance.json", {
        "private": True, "batch": arguments.batch, "master_seed": arguments.seed,
        "scientific_scope": "20 deliberately conditioned mixed-family stress cases, not IID draws; 100 independent ordinary sampler draws",
        "family_counts": dict(Counter(model["family"] for model in models)),
        "witness_counts": dict(Counter(item["seed_witness"] for item in provenance if "seed_witness" in item)),
        "ordering": "public FAMILIES round-robin; seed witnesses alternate within mixed; no outcome-based case selection",
        "selection": "predeclared random couplings and perturbations, rejecting only public physical admissibility failures and inactive eighth virtuals",
        "protocol": {"persistent_processes_per_batch": 1, "query_budget": 160, "maximum_query_order": 6,
                     "cpu_seconds": 120, "wall_seconds": 180, "memory_bytes": 2147483648},
        "unchanged_targets_eh": {"overall_rmse": 1e-5, "worst_family_rmse": 2.5e-5},
        "input_sha256": manifest, "cases": provenance,
    })
    mixed = [item for item in diagnostics if item["family"] == "mixed"]
    summary = {
        "case_count": len(models), "all_checks_passed": True,
        "family_counts": dict(Counter(model["family"] for model in models)),
        "minimum_reference_weight": min(item["reference_weight"] for item in diagnostics),
        "minimum_gap_eh": min(item["gap"] for item in diagnostics),
        "maximum_residual": max(item["residual"] for item in diagnostics),
        "maximum_independent_energy_error_eh": max(item["independent_full_energy_error_eh"] for item in diagnostics),
        "maximum_independent_residual": max(item["independent_full_residual"] for item in diagnostics),
        "minimum_mixed_reference_weight": min(item["reference_weight"] for item in mixed),
        "minimum_mixed_gap_eh": min(item["gap"] for item in mixed),
        "minimum_active_eighth_singleton_magnitude_eh": min(abs(item["eighth_singleton_eh"]) for item in mixed),
        "maximum_excluded_eighth_restriction_error_eh": max(item["all_128_excluded_new_orbital_error_eh"] for item in mixed),
        "maximum_old_restriction_drift_eh": max(item["old_128_max_drift_from_seed_eh"] for item in mixed),
        "maximum_old_coefficient_perturbation_eh": max(item["old_coefficient_max_perturbation_eh"] for item in mixed),
        "perturbed_mixed_case_count": sum(item["old_coefficient_perturbation_sigma_eh"] > 0 for item in mixed),
        "cases_sha256": sha256(output / "cases.npz"),
        "models_sha256": sha256(output / "models.json"),
    }
    write_json(output / "validation_summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
