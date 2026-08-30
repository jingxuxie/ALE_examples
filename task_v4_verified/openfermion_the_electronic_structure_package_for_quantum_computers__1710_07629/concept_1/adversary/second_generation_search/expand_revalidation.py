import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("trusted_preparation", HERE / "prepare.py")
TRUSTED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRUSTED)
np = TRUSTED.np
OUTPUT = HERE / "targeted_expansion"
REPEATS = HERE / "champion_2_revalidation"
TASK = TRUSTED.ROOT.parent


def load(path):
    return json.loads(path.read_text())


def write(name, value):
    temporary = OUTPUT / (name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(OUTPUT / name)


def solutions(path):
    return {entry["id"]: entry for entry in load(path)["solutions"]}


def independent_costs(cases, response, private):
    proposed = solutions(response)
    return [{"id": case["id"],
             "champion_cost": TRUSTED.validate_solution(case, proposed[case["id"]]),
             "private_feasible_cost": TRUSTED.validate_solution(case, private[case["id"]])}
            for case in cases]


def repeat_evidence():
    original = load(HERE / "champion_2_audit/report.json")
    earlier = {entry["id"]: entry for entry in original["records"]}
    private = solutions(HERE / "private_solution.json")
    entries = []
    for number in (11, 6, 7, 9, 10):
        batch = REPEATS / f"batch_{number:02d}"
        report = load(batch / "report.json")
        case_list = load(batch / "request.json")["cases"]
        if not report.get("valid"):
            entries.extend({"id": case["id"], "valid": False,
                            "original_valid": earlier[case["id"]]["valid"],
                            "reason": report.get("reason"),
                            "classification": ("New timeout on repeat; original quality observation unconfirmed"
                                               if earlier[case["id"]]["valid"] else
                                               "Repeated batch timeout; no individual quality inference")}
                           for case in case_list)
            continue
        for entry in independent_costs(case_list, batch / "response.json", private):
            prior = earlier[entry["id"]]
            best = min(entry["champion_cost"], prior.get("champion_cost", float("inf")))
            entry.update(valid=True, original_valid=prior["valid"],
                         repeat_runtime_seconds=report["runtime_seconds"],
                         best_observed_champion_cost=best,
                         robust_gap=1 - entry["private_feasible_cost"] / best,
                         classification="Repeated quality measurement" if prior["valid"] else
                         "Original batch timeout not reproduced; deadline variability, not proven cause")
            entries.append(entry)
    return entries


def make_pool():
    cases, inputs, proofs, starts = [], [], [], {}
    previous = load(HERE / "cases.json")["cases"]
    previous += load(TRUSTED.FROZEN / "participant/input/examples.json")["cases"]
    prior_spectra = [(case["id"], len(case["one_body"]), TRUSTED.spectrum(case))
                     for case in previous]
    for index in range(8):
        dimension = 14 if index in (2, 6) else 16
        rank = dimension - 2
        first_rank = rank // 2
        seed = 94306177 + index * 10007
        random = np.random.default_rng(seed)
        identifier = f"targeted_023_{index + 1:03d}"
        parent_seeds = [seed + 17, seed + 53]
        first, first_witness, _ = TRUSTED.GENERATOR.make_case(
            parent_seeds[0], "overlapping_clusters", dimension, first_rank, "parent_first")
        second, second_witness, _ = TRUSTED.GENERATOR.make_case(
            parent_seeds[1], "overlapping_clusters", dimension, rank - first_rank, "parent_second")
        first_basis = np.asarray(first_witness["orbital"])
        second_basis = np.asarray(second_witness["orbital"])
        first_roots = np.tensordot(np.asarray(first_witness["auxiliary"]),
                                   np.asarray(first["factors"]), axes=(1, 0))
        second_roots = np.tensordot(np.asarray(second_witness["auxiliary"]),
                                    np.asarray(second["factors"]), axes=(1, 0))
        strength = float(random.uniform(1.20, 1.35))
        root_scales = random.uniform(0.75, 1.35, rank)
        roots = np.concatenate((first_roots, strength * second_roots)) * root_scales[:, None, None]
        block = TRUSTED.block_diag(TRUSTED.GENERATOR.orthogonal(random, first_rank),
                                   TRUSTED.GENERATOR.orthogonal(random, rank - first_rank))
        skew = random.normal(size=(rank, rank))
        skew = (skew - skew.T) / math.sqrt(rank)
        mixing_strength = 0.12 if dimension == 14 else 0.20
        mixing = TRUSTED.expm(mixing_strength * skew) @ block
        factors = np.tensordot(mixing, roots, axes=(1, 0))
        one_body = (np.asarray(first["one_body"]) + strength * np.asarray(second["one_body"])) / (1 + strength)
        case = {"id": identifier, "family": "competing_nearblock_gauge", "one_body": one_body.tolist(),
                "factors": factors.tolist()}
        identity = TRUSTED.witness(identifier, np.eye(dimension), np.eye(rank))
        unrotated_cost = TRUSTED.validate_solution(case, identity)
        scaled = dict(case, baseline_cost=unrotated_cost)
        gram = factors.reshape(rank, -1) @ factors.reshape(rank, -1).T
        _, auxiliary_vectors = np.linalg.eigh(gram)
        candidates = [
            ("first_native", first_basis, mixing.T),
            ("second_native", second_basis, mixing.T),
            ("first_gram", first_basis, auxiliary_vectors.T),
            ("second_gram", second_basis, auxiliary_vectors.T),
            ("first_blend", TRUSTED.polar(0.65 * first_basis + 0.35 * second_basis), mixing.T),
            ("second_blend", TRUSTED.polar(0.35 * first_basis + 0.65 * second_basis), mixing.T),
        ]
        starts[identifier] = [{"label": label, "solution": TRUSTED.witness(identifier, orbital, auxiliary)}
                              for label, orbital, auxiliary in candidates]
        spectral = TRUSTED.BASELINE.solve(scaled)
        if isinstance(spectral, tuple):
            spectral = spectral[0]
        starts[identifier].append({"label": "author_spectral", "solution": spectral})
        flattened_roots = roots.reshape(rank, -1)
        flattened_factors = factors.reshape(rank, -1)
        tensor = flattened_roots.T @ flattened_roots
        residual = float(np.linalg.norm(tensor - flattened_factors.T @ flattened_factors) / np.linalg.norm(tensor))
        minimum_eigenvalue = float(np.linalg.eigvalsh(roots).min())
        support_residuals = []
        preferences = []
        for family_index, (native, begin, end) in enumerate(((first_basis, 0, first_rank),
                                                           (second_basis, first_rank, rank))):
            local = np.einsum("pi,apq,qj->aij", native, roots[begin:end], native)
            for factor_index, factor in enumerate(local):
                center = (3 * factor_index + factor_index // 3) % dimension
                support = [(center + offset) % dimension for offset in range(3)]
                outside = factor.copy()
                outside[np.ix_(support, support)] = 0
                support_residuals.append(float(np.linalg.norm(outside)))
            preferences.append([float(np.square(np.abs(np.einsum(
                "pi,apq,qj->aij", basis, roots[begin:end], basis)).sum(axis=(1, 2))).sum())
                                for basis in (first_basis, second_basis)])
        physical_spectrum = TRUSTED.spectrum(case)
        separations = {name: float(np.linalg.norm(physical_spectrum - spectrum) /
                                   max(np.linalg.norm(physical_spectrum), np.linalg.norm(spectrum)))
                       for name, size, spectrum in prior_spectra if size == dimension}
        prior_spectra.append((identifier, dimension, physical_spectrum))
        if (residual > 1e-10 or minimum_eigenvalue < -1e-8 or
                min(separations.values()) < 1e-6 or max(support_residuals) > 1e-8):
            raise ValueError("Invalid physical certificate or duplicate spectrum")
        proofs.append({"id": identifier, "seed": seed, "parent_seeds": parent_seeds,
                       "dimension": dimension, "rank": rank, "strength_regime": "secondary_stronger",
                       "relative_strength": strength, "root_scales": root_scales.tolist(),
                       "auxiliary_skew_strength": mixing_strength,
                       "minimum_root_eigenvalue": minimum_eigenvalue,
                       "squared_operator_tensor_relative_residual": residual,
                       "maximum_native_support_residual": max(support_residuals),
                       "native_family_costs_in_two_frames": preferences,
                       "both_families_prefer_own_basis": preferences[0][0] < preferences[0][1] and
                                                                  preferences[1][1] < preferences[1][0],
                       "one_particle_sector_spectrum": physical_spectrum.tolist(),
                       "minimum_prior_or_public_spectral_separation": min(separations.values())})
        cases.append(case)
        inputs.append(scaled)
    write("cases.json", {"cases": cases, "seconds_per_case": 10})
    write("optimizer_inputs.json", {"cases": inputs, "diagnostic_denominator": "unrotated identity cost only"})
    write("provenance.json", {"cases": proofs, "law": "Independent overlapping PSD charge families in independent Haar frames; no physical reuse or regauging", "targeted_subrange": [1.20, 1.35]})
    write("planted_starts.json", starts)
    return cases, inputs, proofs, starts


def evaluate_batch(entries, number):
    destination = OUTPUT / f"batch_{number:02d}"
    destination.mkdir(exist_ok=False)
    (destination / "request.json").write_text(json.dumps({"cases": entries, "seconds_per_case": 10}))
    command = ["taskset", "-c", "188", sys.executable, str(TASK / "private/affinity.py"),
               str(TASK / "private/capture_gauge_evaluation.py"), "--evaluator",
               str(TRUSTED.FROZEN / "evaluator/evaluate.py"), "--submission",
               str(TRUSTED.ROOT / "champions/generation_2"), "--cases", str(destination / "request.json"),
               "--report", str(destination / "report.json"), "--response", str(destination / "response.json")]
    with (destination / "evaluation.log").open("w") as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=120, check=False)
    return destination, load(destination / "report.json")


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (490, 510))
    OUTPUT.mkdir(exist_ok=False)
    TRUSTED.DIRECTORY = OUTPUT
    repeats = repeat_evidence()
    write("repeat_evidence.json", {"records": repeats})
    trigger = next(entry for entry in repeats if entry["id"] == "second_pool_023")
    if not trigger.get("valid") or trigger["robust_gap"] <= 0:
        reason = ("Case023 repeat timed out; no quality revalidation and no expansion gate"
                  if not trigger.get("valid") else "Case023 had no repeated positive quality gap")
        write("report.json", {"expanded": False, "reason": reason, "repeat_records": repeats})
        return
    snapshot, mismatches = TRUSTED.source_snapshot()
    write("source_hashes.json", snapshot)
    write("config.json", {"cases": 8, "dimensions": [14, 16], "ranks": [12, 14],
                          "seed_base": 94306177, "seed_stride": 10007, "cpu": 187,
                          "private_cpu_budget": 300, "optimizer_rounds": 10, "seconds_per_start": 4,
                          "targeted_parent": "second_pool_023", "no_untrusted_imports": True,
                          "runtime_contract": "10 seconds per case, two-case batches"})
    cases, inputs, proofs, starts = make_pool()
    arguments = SimpleNamespace(cpu=187, cpu_budget=300, rounds=10, seconds_per_start=4)
    private, references, history, exhausted = TRUSTED.optimize(cases, inputs, proofs, starts, arguments)
    print(json.dumps({"phase": "references_ready", "cases": len(cases), "cpu_seconds": time.process_time()}), flush=True)
    records, batches = [], []
    for number, offset in enumerate(range(0, len(cases), 2)):
        entries = inputs[offset:offset + 2]
        destination, report = evaluate_batch(entries, number)
        batches.append({"batch": number, "report": report})
        if report.get("valid"):
            measured = independent_costs(entries, destination / "response.json", private)
            for entry in measured:
                entry.update(valid=True, gap=1 - entry["private_feasible_cost"] / entry["champion_cost"],
                             batch=number, runtime_seconds=report["runtime_seconds"])
                records.append(entry)
        else:
            records.extend({"id": case["id"], "valid": False, "batch": number,
                            "reason": report.get("reason")} for case in entries)
        write("audit.json", {"records": records, "batches": batches})
        print(json.dumps({"phase": "audited", "batch": number, "valid": report.get("valid"),
                          "positive_gaps": [entry for entry in records if entry.get("gap", 0) > 0]}), flush=True)
    new_snapshot, new_mismatches = TRUSTED.source_snapshot()
    write("report.json", {"expanded": True, "cases": len(cases), "records": records,
                          "repeat_records": repeats, "process_cpu_seconds": time.process_time(),
                          "wall_seconds": time.monotonic() - started, "budget_exhausted": exhausted,
                          "frozen_sources_unchanged": snapshot == new_snapshot,
                          "freeze_manifest_mismatches": mismatches + new_mismatches,
                          "maximum_native_support_residual": max(proof["maximum_native_support_residual"] for proof in proofs),
                          "not_a_global_optimality_test": True, "participant_generation_created": False})


if __name__ == "__main__":
    main()
