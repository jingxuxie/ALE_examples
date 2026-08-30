import collections
import copy
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True

import challenge
import numpy as np


HERE = Path(__file__).resolve().parent


def select_perturbations(center, perturbed, control_indices):
    result = copy.deepcopy(center)
    for index in control_indices:
        control = challenge.CONTROLS[index]
        if control["kind"] == "pair_energy":
            orbital = control["orbitals"][0]
            result["pair_energy_eh"][orbital] = perturbed["pair_energy_eh"][orbital]
        else:
            source, destination = control["orbitals"]
            kind = control["kind"]
            result[kind][source][destination] = result[kind][destination][source] = perturbed[kind][source][destination]
    return result


def low_increments(engine, parameters):
    matrix, alternate = engine.matrices(parameters)
    if np.max(np.abs(matrix - alternate)) > 5e-10:
        raise AssertionError("gradient matrix disagreement")
    energies = {0: float(matrix[engine.reference, engine.reference])}
    for mask in challenge.LOW_MASKS:
        if mask:
            selected = engine.subsets[mask]
            energies[mask] = float(challenge.eigh(matrix[np.ix_(selected, selected)], subset_by_index=(0, 0), eigvals_only=True, check_finite=True)[0])
    increments = []
    for mask in challenge.TRIPLE_MASKS:
        subset, terms = mask, []
        while subset:
            sign = -1 if (mask.bit_count() - subset.bit_count()) % 2 else 1
            terms.append(sign * (energies[subset] - energies[0]))
            subset = (subset - 1) & mask
        increments.append(math.fsum(terms))
    return np.array(increments)


def main():
    started = time.perf_counter()
    target = json.loads((HERE / "inputs/target.json").read_text())
    center = challenge.champion_parameters(target)
    engine = challenge.IndependentEngine(target)
    grid_uniforms = json.loads((HERE / "grid_uniforms.json").read_text())
    uniforms = np.array(grid_uniforms["uniforms"])
    vv_results = json.loads((HERE / "results/grid_original_vv_0p001.json").read_text())
    full_results = json.loads((HERE / "results/grid_full_coefficients_0p001.json").read_text())
    sample_index = next(index for index in range(len(uniforms))
                        if vv_results["cases"][index]["passed"] and not full_results["cases"][index]["passed"])
    full = challenge.perturb(center, "full_coefficients", 0.001, uniforms[sample_index], target)
    groups = {
        "pair_energies": challenge.family_indices("diagonal_energy"),
        "fixed_density": challenge.family_indices("fixed_density"),
        "ov_hopping": challenge.family_indices("ov_transfer"),
        "oo_hopping": [index for index, control in enumerate(challenge.CONTROLS)
                       if control["kind"] == "hopping" and max(control["orbitals"]) < 3],
        "vv_hopping": [index for index in challenge.family_indices("original_vv") if challenge.CONTROLS[index]["kind"] == "hopping"],
        "vv_density": [index for index in challenge.family_indices("original_vv") if challenge.CONTROLS[index]["kind"] == "density"],
    }
    attribution = []
    for group, indices in groups.items():
        for operation, selected in (("only", indices), ("remove_from_full", [index for index in range(100) if index not in indices])):
            parameters = select_perturbations(center, full, selected)
            report = engine.evaluate(parameters, complete=True)
            label = operation + "_" + group
            path = HERE / "diagnostic_examples" / (label + ".json")
            challenge.write_json(path, dict(operation=operation, group=group, selected_control_indices=selected,
                                            seed=grid_uniforms["seed"], sample_index=sample_index,
                                            radius_eh=0.001, parameters=parameters, report=report))
            attribution.append(dict(operation=operation, group=group, report=report,
                                    example=str(path.relative_to(HERE))))
    auxiliary = {}
    for family in ("ov_relative_one_percent", "ov_absolute_strong_only", "ov_absolute_small_only", "full_without_oo_hopping"):
        records, examples = [], {}
        for sample_index, row in enumerate(uniforms):
            perturbed = challenge.perturb(center, "full_coefficients", 0.001, row, target)
            if family == "full_without_oo_hopping":
                selected = [index for index in range(100) if index not in groups["oo_hopping"]]
            else:
                selected = groups["ov_hopping"]
                if family in ("ov_absolute_strong_only", "ov_absolute_small_only"):
                    strong = family == "ov_absolute_strong_only"
                    selected = [index for index in selected if (abs(center["hopping"][challenge.CONTROLS[index]["orbitals"][0]][challenge.CONTROLS[index]["orbitals"][1]]) >= 0.01) == strong]
            parameters = select_perturbations(center, perturbed, selected)
            if family == "ov_relative_one_percent":
                for index in selected:
                    source, destination = challenge.CONTROLS[index]["orbitals"]
                    original = center["hopping"][source][destination]
                    changed = float(original + abs(original) * 0.01 * (2 * row[index] - 1))
                    parameters["hopping"][source][destination] = parameters["hopping"][destination][source] = changed
            report = engine.evaluate(parameters)
            report["sample_index"] = sample_index
            records.append(report)
            if report["cluster"] not in examples:
                path = HERE / "diagnostic_examples" / (family + "_" + report["cluster"].replace("+", "_") + ".json")
                complete_report = engine.evaluate(parameters, complete=True)
                if complete_report["cluster"] != report["cluster"] or not complete_report["numerical_valid"]:
                    raise AssertionError("auxiliary example verification failed")
                challenge.write_json(path, dict(family=family, seed=grid_uniforms["seed"], sample_index=sample_index,
                                                selected_control_indices=selected, parameters=parameters, report=complete_report))
                examples[report["cluster"]] = str(path.relative_to(HERE))
        auxiliary[family] = dict(control_count=len(selected), summary=challenge.aggregate(records), examples=examples, cases=records)
        print(json.dumps(dict(auxiliary_family=family, successes=auxiliary[family]["summary"]["successes"], count=len(records))), flush=True)
    derivatives = []
    for index in groups["ov_hopping"]:
        source, destination = challenge.CONTROLS[index]["orbitals"]
        derivative_vectors = []
        for step in (1e-6, 5e-7):
            lower, upper = copy.deepcopy(center), copy.deepcopy(center)
            lower["hopping"][source][destination] = lower["hopping"][destination][source] = center["hopping"][source][destination] - step
            upper["hopping"][source][destination] = upper["hopping"][destination][source] = center["hopping"][source][destination] + step
            derivative_vectors.append((low_increments(engine, upper) - low_increments(engine, lower)) / (2 * step))
        derivative = derivative_vectors[0]
        derivatives.append(dict(control_index=index, orbitals=[source, destination],
                                nominal_coefficient_eh=center["hopping"][source][destination],
                                max_absolute_triple_derivative=float(np.max(np.abs(derivative))),
                                max_linearized_triple_change_at_1mEh=float(0.001 * np.max(np.abs(derivative))),
                                finite_difference_step_agreement=float(np.max(np.abs(derivative_vectors[0] - derivative_vectors[1])))))
    derivatives.sort(key=lambda entry: entry["max_absolute_triple_derivative"], reverse=True)
    family_worst_triples = {}
    for family in ("original_vv", "ov_transfer", "full_coefficients"):
        cases = json.loads((HERE / ("results/grid_" + family + "_0p001.json")).read_text())["cases"]
        family_worst_triples[family] = dict(collections.Counter(",".join(map(str, case["worst_triple_virtual_indices"])) for case in cases))
    result = dict(status="complete private post-grid attribution, not a target", elapsed_seconds=time.perf_counter() - started,
                  attribution=attribution, auxiliary=auxiliary, ov_sensitivity=derivatives,
                  worst_triple_frequencies=family_worst_triples, audit=challenge.frozen_audit(),
                  interpretation_limits="finite differences and ablations are local mechanism diagnostics, not a universal bound or a newly frozen assay; auxiliary draws reuse the declared grid rows")
    challenge.write_json(HERE / "diagnostics.json", result)
    print(json.dumps(dict(complete=True, seconds=result["elapsed_seconds"])), flush=True)


if __name__ == "__main__":
    main()
