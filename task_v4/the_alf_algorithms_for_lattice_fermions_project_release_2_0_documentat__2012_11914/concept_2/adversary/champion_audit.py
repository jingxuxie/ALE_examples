import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "adversary/champion_audit_v1"


def write_json(path, content):
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + "\n")


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def build_batch(instances, labels):
    dimension = max(math.prod(instance["shape"]) for instance in instances)
    matrices = np.zeros((len(instances), 5, dimension, dimension), dtype=complex)
    partners = np.broadcast_to(np.arange(dimension), (len(instances), 4, dimension)).copy()
    amplitudes = np.zeros((len(instances), 4, dimension))
    phases = np.zeros_like(amplitudes)
    onsite = np.zeros((len(instances), dimension))
    for sample, instance in enumerate(instances):
        size = math.prod(instance["shape"])
        onsite[sample, :size] = instance["site_potential"]
        matrices[sample, 4] = np.diag(onsite[sample])
        for label, source, target, amplitude, phase in instance["bonds"]:
            component = labels.index(label)
            value = -amplitude * np.exp(1j * phase)
            matrices[sample, component, source, target] += value
            matrices[sample, component, target, source] += value.conjugate()
            partners[sample, component, source] = target
            partners[sample, component, target] = source
            amplitudes[sample, component, source] = amplitude
            amplitudes[sample, component, target] = amplitude
            phases[sample, component, source] = -phase
            phases[sample, component, target] = phase
    total_values, total_vectors = np.linalg.eigh(matrices.sum(axis=1))
    return partners, amplitudes, phases, onsite, total_values, total_vectors


def positive_spectrum(stages, step, labels, batch):
    partners, amplitudes, phases, onsite, total_values, total_vectors = batch
    dimension = onsite.shape[1]
    factor = np.broadcast_to(np.eye(dimension, dtype=complex), (len(onsite), dimension, dimension)).copy()
    center = len(stages) // 2
    for index, stage in enumerate(stages[:center + 1]):
        component = labels.index(stage["component"])
        weight = step * stage["coefficient"] * (0.5 if index == center else 1.0)
        if component == 4:
            factor *= np.exp(-weight * onsite)[:, None, :]
        else:
            angle = weight * amplitudes[:, component]
            diagonal = np.cosh(angle)
            offdiagonal = np.sinh(angle) * np.exp(1j * phases[:, component])
            partner_columns = np.take_along_axis(factor, partners[:, component, None, :], axis=2)
            factor = factor * diagonal[:, None, :] + partner_columns * offdiagonal[:, None, :]
    vectors, singular_values, right_vectors = np.linalg.svd(factor, full_matrices=False)
    if not np.all(singular_values > 0):
        raise ArithmeticError("nonpositive singular value in positive-factor representation")
    logarithms = 2 * np.log(singular_values)
    return logarithms, vectors


def reconstructed(vectors, diagonal):
    return (vectors * diagonal[:, None, :]) @ vectors.conj().swapaxes(-1, -2)


def audit_batch(instances, candidate, baseline, labels, steps):
    batch = build_batch(instances, labels)
    total_values, total_vectors = batch[-2:]
    records = []
    for step in steps:
        candidate_logs, candidate_vectors = positive_spectrum(candidate, step, labels, batch)
        baseline_logs, baseline_vectors = positive_spectrum(baseline, step, labels, batch)
        for repeats in (1, 4):
            exact_logs = -repeats * step * total_values
            largest = np.maximum.reduce((exact_logs.max(axis=1), (repeats * candidate_logs).max(axis=1), (repeats * baseline_logs).max(axis=1)))
            exact_propagator = reconstructed(total_vectors, np.exp(exact_logs - largest[:, None]))
            candidate_propagator = reconstructed(candidate_vectors, np.exp(repeats * candidate_logs - largest[:, None]))
            baseline_propagator = reconstructed(baseline_vectors, np.exp(repeats * baseline_logs - largest[:, None]))
            exact_green = reconstructed(total_vectors, expit(repeats * step * total_values))
            candidate_green = reconstructed(candidate_vectors, expit(-repeats * candidate_logs))
            baseline_green = reconstructed(baseline_vectors, expit(-repeats * baseline_logs))
            for observable, truth, proposed, control in (("propagator", exact_propagator, candidate_propagator, baseline_propagator), ("green", exact_green, candidate_green, baseline_green)):
                padding = truth.shape[-1] - np.array([math.prod(instance["shape"]) for instance in instances])
                padded_value = np.exp(-largest) if observable == "propagator" else 0.5
                denominator = np.sqrt(np.maximum(np.linalg.norm(truth, axis=(-2, -1)) ** 2 - padding * padded_value ** 2, 1e-300))
                candidate_errors = np.linalg.norm(proposed - truth, axis=(-2, -1)) / denominator
                baseline_errors = np.linalg.norm(control - truth, axis=(-2, -1)) / denominator
                ratios = np.maximum(candidate_errors, 1e-14) / np.maximum(baseline_errors, 1e-14)
                for index, instance in enumerate(instances):
                    records.append({"case_id": instance["id"], "family": instance["family"], "dtau": step, "repetitions": repeats, "observable": observable, "ratio": float(ratios[index]), "candidate_error": float(candidate_errors[index]), "baseline_error": float(baseline_errors[index]), "single_step_log_condition_candidate": float(np.ptp(candidate_logs[index])), "single_step_log_condition_baseline": float(np.ptp(baseline_logs[index]))})
    return records


def extend(instances, regime, seed):
    generator = np.random.default_rng(seed)
    for instance in instances:
        width, height = instance["shape"]
        size = width * height
        instance["id"] = regime + "_" + instance["id"]
        parameters = {"base_family": instance["family"]}
        if regime == "larger_steps":
            instance["audit_parameters"] = parameters
            continue
        strength = float(generator.uniform(0.5, 6.0) if regime in ("checkerboard", "stripes", "blocks", "uniform") else generator.uniform(2.5, 6.0))
        chemical = float(generator.uniform(-0.4, 0.4))
        sign = int(generator.choice([-1, 1]))
        coordinates = np.array([(abscissa, ordinate) for ordinate in range(height) for abscissa in range(width)])
        if regime == "checkerboard":
            fields = sign * (-1.0) ** coordinates.sum(axis=1)
        elif regime == "stripes":
            axis = int(generator.integers(2))
            fields = sign * (-1.0) ** coordinates[:, axis]
            parameters["stripe_axis"] = axis
        elif regime == "blocks":
            domains = generator.choice([-1.0, 1.0], size=(height // 2, width // 2))
            fields = np.array([domains[ordinate // 2, abscissa // 2] for abscissa, ordinate in coordinates])
        elif regime == "uniform":
            fields = np.full(size, float(sign))
        else:
            fields = generator.choice([-1.0, 1.0], size=size)
        instance["site_potential"] = (strength * fields - chemical).tolist()
        parameters.update({"field_strength": strength, "chemical_potential": chemical, "field_pattern": regime})
        if regime == "strong_flux":
            for bond in instance["bonds"]:
                bond[4] = float(generator.uniform(-math.pi, math.pi))
            parameters["phase_width"] = math.pi
        instance["audit_parameters"] = parameters
    return instances


def summarize(records):
    ratios = np.array([record["ratio"] for record in records])
    cases = {record["case_id"] for record in records}
    family_scores = {family: float(1 / np.sqrt(np.mean([record["ratio"] ** 2 for record in records if record["family"] == family]))) for family in sorted({record["family"] for record in records})}
    return {"cases": len(cases), "points": len(records), "core_score": float(np.exp(np.mean(np.log(list(family_scores.values()))))), "worst_family_score": min(family_scores.values()), "family_scores": family_scores, "max_point_ratio": float(ratios.max()), "quantiles": {str(quantile): float(np.quantile(ratios, quantile)) for quantile in (0.5, 0.9, 0.99, 0.999)}, "points_worse_than_strang": int(np.count_nonzero(ratios > 1)), "points_above_original_cap": int(np.count_nonzero(ratios > 1.15)), "cases_worse_than_strang": len({record["case_id"] for record in records if record["ratio"] > 1}), "cases_above_original_cap": len({record["case_id"] for record in records if record["ratio"] > 1.15}), "worst": max(records, key=lambda record: record["ratio"])}


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-per-family", type=int, default=384)
    parser.add_argument("--extension-per-family", type=int, default=96)
    parser.add_argument("--large-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.large_only:
        OUT = ROOT / "adversary/champion_audit_large_v1"
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    checker = load_module("trusted_audit_checker", ROOT / "evaluator/evaluate.py")
    generator = load_module("trusted_audit_generator", ROOT / "evaluator/hidden/generate.py")
    contract_bytes = (ROOT / "evaluator/hidden/contract.json").read_bytes()
    rules = json.loads(contract_bytes)
    source = ROOT / "attempts/v_1/submission.json"
    raw = source.read_bytes()
    candidate_payload = checker.parse_json(raw.decode())
    candidate = checker.validate(candidate_payload, rules)
    baseline = checker.reference_stages(rules)
    digest = hashlib.sha256(raw).hexdigest()
    if (OUT / "candidate.json").exists() and (OUT / "candidate.json").read_bytes() != raw:
        raise SystemExit("Refusing to overwrite a different candidate snapshot")
    (OUT / "candidate.json").write_bytes(raw)
    (OUT / "original_contract.json").write_bytes(contract_bytes)
    write_json(OUT / "baseline.json", {"schema_version": 1, "stages": baseline})
    metadata = {"candidate_source": str(source.relative_to(ROOT)), "candidate_sha256": digest, "original_contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "seed_original": 82841001, "seed_extensions_base": 82842000, "threads": 1, "original_cases_per_family": arguments.original_per_family, "extension_cases_per_family": arguments.extension_per_family, "steps_original": [0.08, 0.16, 0.28, 0.4], "steps_extensions": [0.4, 0.6, 0.8, 1.0], "repetitions": [1, 4], "oracle": "Exact H eigenbasis Fermi function; candidate/baseline P=L L* positive-half factors, with eigenvalues and eigenvectors obtained by SVD(L). Green functions use expit(-r*log(lambda(P))); no direct inverse of I+P^r. Propagator comparisons use a shared log scale.", "extension_law": "Base hoppings from the four original families with equal counts. Larger_steps changes only h. strong_field redraws iid binary onsite fields with strength U[2.5,6] and chemical potential U[-.4,.4]. strong_flux additionally redraws every oriented bond phase U[-pi,pi]. checkerboard/stripes/blocks/uniform use strength U[.5,6], chemical potential U[-.4,.4], and the named correlated binary pattern; stripes choose axis equiprobably; blocks are independent random 2x2 domains. No instance is selected before the broad scan.", "public_or_targets_modified": False, "high_precision_status": "pending worst-case validation"}
    write_json(OUT / "metadata.json", metadata)
    summaries = {}
    regimes = ("larger_tori",) if arguments.large_only else ("original_law", "larger_steps", "strong_field", "strong_flux", "checkerboard", "stripes", "blocks", "uniform")
    for regime_index, regime in enumerate(regimes):
        within_original = regime == "original_law"
        count = arguments.original_per_family if within_original else arguments.extension_per_family
        seed = 82841001 if within_original else 82842000 + regime_index
        sampling_rules = copy.deepcopy(rules)
        if regime == "larger_tori":
            sampling_rules["sampling"]["lattice_shapes"] = [[6,6], [6,8], [8,8]]
        instances = generator.draw_suite(sampling_rules, seed, count)["instances"]
        if not within_original and regime != "larger_tori":
            instances = extend(instances, regime, seed + 200)
        steps = [0.08, 0.16, 0.28, 0.4] if within_original or regime == "larger_tori" else ([0.6, 0.8, 1.0] if regime == "larger_steps" else [0.4, 0.6, 0.8, 1.0])
        all_records = []
        for start in range(0, len(instances), 48):
            all_records.extend(audit_batch(instances[start:start + 48], candidate, baseline, rules["components"], steps))
        summary = summarize(all_records)
        summary["within_original_law_and_steps"] = within_original
        summary["coupling_law_unchanged"] = regime in ("original_law", "larger_steps", "larger_tori")
        summary["shapes"] = sampling_rules["sampling"]["lattice_shapes"]
        summary["seed"] = seed
        summary["by_step_and_observable"] = {f"h={step}:{observable}": summarize([record for record in all_records if record["dtau"] == step and record["observable"] == observable]) for step in steps for observable in ("propagator", "green")}
        summaries[regime] = summary
        write_json(OUT / (regime + "_summary.json"), summary)
        worst_records = sorted(all_records, key=lambda record: record["ratio"], reverse=True)
        selected = []
        seen = set()
        for record in worst_records:
            if record["case_id"] not in seen:
                seen.add(record["case_id"])
                selected.append(record)
            if len(selected) == 12:
                break
        selected_ids = {record["case_id"] for record in selected}
        fixtures = [instance for instance in instances if instance["id"] in selected_ids]
        write_json(OUT / (regime + "_worst_fixtures.json"), {"regime": regime, "candidate_sha256": digest, "instances": fixtures, "worst_records": selected})
        with (OUT / (regime + "_points.jsonl")).open("w") as handle:
            for record in all_records:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        write_json(OUT / "summary.json", {"candidate_sha256": digest, "elapsed_wall_seconds": time.monotonic() - started, "regimes": summaries})
        print(json.dumps({"regime": regime, "cases": summary["cases"], "points": summary["points"], "core": summary["core_score"], "worst_family": summary["worst_family_score"], "max_ratio": summary["max_point_ratio"], "cases_ratio_gt_1_15": summary["cases_above_original_cap"], "elapsed": time.monotonic() - started}), flush=True)
    metadata["source_sha256_after_scan"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata["snapshot_still_matches_source"] = metadata["source_sha256_after_scan"] == digest
    metadata["elapsed_wall_seconds"] = time.monotonic() - started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    metadata["cpu_seconds"] = usage.ru_utime + usage.ru_stime
    metadata["peak_rss_kib"] = usage.ru_maxrss
    write_json(OUT / "metadata.json", metadata)
    print("BROAD_AUDIT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
