import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.optimize import linprog


ROOT = Path(__file__).resolve().parent
STUDY = ROOT.parents[2] / "cancellation_search"
sys.path.insert(0, str(STUDY))
from build_batch import CASOracle, FAMILIES, seed_embedding, stress_model, validate_model, sample_model, increments
from build_diversified_batch import controlled_model, controls_of, triple_values, permute_virtuals, pairwise_summary


def main():
    output = ROOT / "holdout"
    output.mkdir(exist_ok=False)
    deadline = json.loads((ROOT / "budget.json").read_text())["deadline_unix"]
    master_seed = 20260828123791
    names = ("fresh_b1", "author_private")
    seeds = {}
    for name in names:
        _, embedded, _, _ = seed_embedding(name)
        arrays = np.load(STUDY / "batch_02" / ("nullspace_" + name + ".npz"))
        jacobian = arrays["jacobian"]
        left_vectors, singular_values, right_vectors = np.linalg.svd(jacobian, full_matrices=True)
        basis = right_vectors[int(np.sum(singular_values > 2e-6)):].T
        seeds[name] = (embedded, arrays["controls"], basis)
    models, tables, diagnostics, identities, canonical_tables = [], [], [], [], []
    for index, stream in enumerate(np.random.SeedSequence(master_seed).spawn(120)):
        if time.time() > deadline - 150:
            raise RuntimeError("holdout construction stopped at portfolio time reserve")
        family = FAMILIES[index % 6]
        draw_seed = int(stream.generate_state(1, dtype=np.uint64)[0])
        identity = {"index": index, "family": family, "draw_seed": draw_seed}
        if family == "mixed":
            name = names[(index // 6) % 2]
            embedded, controls, basis = seeds[name]
            generator = np.random.default_rng(draw_seed)
            bounds = np.r_[np.full(21, .45), np.full(21, .6)]
            accepted = False
            for trial in range(300):
                amplitude = generator.uniform(.015, .04)
                constraints = np.r_[basis, -basis]
                allowances = np.r_[np.minimum(bounds-controls-2e-4, amplitude), np.minimum(bounds+controls-2e-4, amplitude)]
                result = linprog(generator.normal(size=basis.shape[1]), A_ub=constraints, b_ub=allowances,
                                 bounds=[(None,None)]*basis.shape[1], method="highs")
                if not result.success:
                    continue
                changed = controls + basis @ result.x * generator.uniform(.7,.98)
                core = controlled_model(embedded, changed)
                displacement = np.zeros(10)
                displacement[3:] = generator.uniform(-.025,.025,7)
                core["orbital_energy"] = (np.asarray(core["orbital_energy"])-displacement).tolist()
                density = np.asarray(core["density"]) + (displacement[:,None]+displacement[None,:])/2
                np.fill_diagonal(density,0)
                core["density"] = density.tolist()
                canonical, sigma, jitter_max = stress_model(core,generator,1,jitter_sigma=float(generator.uniform(2e-5,1e-4)))
                parents = triple_values(canonical)
                if np.max(abs(parents)) > 1e-6 or np.max(abs(np.asarray(canonical["density"]))) > .65:
                    continue
                oracle = CASOracle(canonical)
                spectrum = oracle.spectrum()
                if spectrum["reference_weight"] < .94 or spectrum["gap"] < .35 or abs(oracle.energy(128)) < 3e-4:
                    continue
                accepted = True
                break
            if not accepted:
                raise RuntimeError("independent holdout admissibility exhausted")
            canonical_table = oracle.all_energies()
            permutation = generator.permutation(8)
            model, mask_map, site_order = permute_virtuals(canonical, permutation)
            oracle = CASOracle(model)
            table = oracle.all_energies()
            added = int(np.flatnonzero(permutation == 7)[0])
            checks = validate_model(model, oracle, table, stress=True, new_virtual=added)
            covariance_error = float(np.max(abs(table-canonical_table[mask_map])))
            if covariance_error > 1e-11:
                raise RuntimeError("holdout permutation covariance failed")
            identity.update(seed_neighborhood=name, near_null_dimension=basis.shape[1], coefficient_step_amplitude=float(amplitude),
                            independent_jitter_sigma=sigma, virtual_permutation=permutation.tolist(), accepted_trial=trial,
                            old_max_abs_triple_eh=float(np.max(abs(parents))), permutation_energy_error_eh=covariance_error)
            canonical_tables.append((name,canonical_table[:128]))
        else:
            model = sample_model(draw_seed, family)
            oracle = CASOracle(model)
            table = oracle.all_energies()
            checks = validate_model(model, oracle, table)
        models.append(model)
        tables.append(table)
        diagnostics.append(checks)
        identities.append(identity)
    np.savez_compressed(output/"cases.npz",energies=np.asarray(tables))
    (output/"models.json").write_text(json.dumps(models)+"\n")
    (output/"diagnostics.json").write_text(json.dumps(diagnostics,indent=2)+"\n")
    low_masks=[mask for mask in range(128) if mask.bit_count() <= 2]
    fourth_masks=[mask for mask in range(128) if mask.bit_count() == 4]
    diversity={name:{"CAS2":pairwise_summary([table[low_masks] for source_name,table in canonical_tables if source_name==name]),
                     "fourth_increments":pairwise_summary([increments(table)[fourth_masks] for source_name,table in canonical_tables if source_name==name])}
               for name in names}
    metadata={"independent_generation_seed":master_seed,"family_counts":dict(Counter(model["family"] for model in models)),
              "not_used_for_tuning":True,"conditioned_not_IID":True,"scope":"new coefficients/couplings/permutations and 100 new ordinary draws, but still two seed-derived neighborhoods; not independent new witness discoveries",
              "diversity":diversity,"cases":identities,"minimum_reference_weight":min(item["reference_weight"] for item in diagnostics),
              "minimum_gap_eh":min(item["gap"] for item in diagnostics),"maximum_residual":max(item["residual"] for item in diagnostics)}
    (output/"provenance.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps({key:value for key,value in metadata.items() if key not in ("cases","diversity")},indent=2),flush=True)


if __name__ == "__main__":
    main()
