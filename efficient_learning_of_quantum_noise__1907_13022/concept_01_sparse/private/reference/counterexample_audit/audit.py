import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


AUDIT = Path(__file__).resolve().parent
REFERENCE = AUDIT.parent
CONCEPT = REFERENCE.parents[1]
FROZEN = CONCEPT.parent / "private/runs/pilot/submissions/concept_01_sparse.py"
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(CONCEPT / "private"))
import evaluator
from build import observations, sampling_hash
from metrics import grade, measure
from physical import masks_to_observables, spectrum

evaluator.ROOT = AUDIT

REGIONS = [
    dict(name="higher_load", qubits=40, heavy=384, groups=4, hash_bits=7, span=12.0, noise_ratio=0.15, extra_offsets=32),
    dict(name="sign_noise", qubits=80, heavy=260, groups=4, hash_bits=7, span=32.0, noise_ratio=0.32, extra_offsets=48),
    dict(name="dynamic_range", qubits=100, heavy=480, groups=3, hash_bits=8, span=9000.0, noise_ratio=0.19, extra_offsets=48),
    dict(name="nearly_equal", qubits=64, heavy=352, groups=4, hash_bits=7, span=1.3, noise_ratio=0.15, extra_offsets=32),
    dict(name="approximate", qubits=96, heavy=280, groups=4, hash_bits=7, span=48.0, noise_ratio=0.19, extra_offsets=48, tail_count=8192, tail_fraction=0.06),
    dict(name="heteroscedastic", qubits=72, heavy=120, groups=4, hash_bits=6, span=1000.0, noise_ratio=0.13, extra_offsets=32, heteroscedastic=True),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected_inventory():
    paths = [path for path in CONCEPT.rglob("*") if path.is_file() and AUDIT not in path.parents]
    paths.append(FROZEN)
    return {str(path.relative_to(CONCEPT.parent)): digest(path) for path in sorted(paths)}


def write_json(path, value):
    path = Path(path).resolve()
    path.relative_to(AUDIT)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def generate(specification, seed):
    generator = np.random.default_rng(seed)
    qubits = specification["qubits"]
    count = specification["heavy"]
    hash_bits = specification["hash_bits"]
    tail_count = specification.get("tail_count", 0)
    mass = generator.uniform(0.15, 0.20)
    tail_mass = mass * specification.get("tail_fraction", 0.0)
    weights = np.geomspace(1.0, specification["span"], count) * generator.uniform(0.97, 1.03, count)
    generator.shuffle(weights)
    weights *= (mass - tail_mass) / weights.sum()
    tail = generator.uniform(0.6, 1.4, tail_count)
    if tail_count:
        tail *= tail_mass / tail.sum()
    probabilities = np.concatenate((weights, tail))
    labels = generator.integers(0, 4, (len(probabilities), qubits), dtype=np.uint8)
    assert np.all(np.any(labels, axis=1)) and len(np.unique(labels, axis=0)) == len(labels)
    table = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.uint8)
    bits = table[labels].reshape(len(labels), 2 * qubits)
    hashes = np.array([sampling_hash(generator, qubits, hash_bits) for group in range(specification["groups"])])
    offsets = np.vstack((np.zeros((1, 2 * qubits), dtype=np.uint8), np.eye(2 * qubits, dtype=np.uint8), generator.integers(0, 2, (specification["extra_offsets"], 2 * qubits), dtype=np.uint8)))
    clean = observations(bits, probabilities, 1.0 - mass, hashes, offsets)
    sigma = weights.min() * specification["noise_ratio"] * np.sqrt(2**hash_bits)
    noise_std = sigma * generator.uniform(0.9, 1.1, (len(hashes), len(offsets)))
    if specification.get("heteroscedastic"):
        factors = np.geomspace(0.45, 2.8, len(offsets))
        noise_std *= np.array([generator.permutation(factors) for group in hashes])
    values = clean + generator.normal(size=clean.shape) * noise_std[:, :, None]
    probes = generator.integers(0, 4, (384, qubits), dtype=np.uint8)
    assert np.all(np.any(probes, axis=1))
    expected = spectrum(labels, probabilities, 1.0 - mass, probes)
    maximum_error = 0.0
    binary = ((np.arange(2**hash_bits)[:, None] >> np.arange(hash_bits)) & 1).astype(np.uint8)
    for group, matrix in enumerate(hashes):
        commutators = (matrix[:, 0::2] @ matrix[:, 1::2].T + matrix[:, 1::2] @ matrix[:, 0::2].T) & 1
        assert not np.any(commutators)
        assert len(np.unique((binary @ matrix) & 1, axis=0)) == 2**hash_bits
        times = generator.integers(0, len(offsets), 32)
        indexes = generator.integers(0, 2**hash_bits, 32)
        masks = offsets[times] ^ ((binary[indexes] @ matrix) & 1)
        independent = spectrum(labels, probabilities, 1.0 - mass, masks_to_observables(masks))
        maximum_error = max(maximum_error, float(np.max(np.abs(independent - clean[group, times, indexes]))))
    assert maximum_error < 2e-12
    floor = float(weights.min() * 0.8)
    assert not tail_count or tail.max() < floor / 3
    assert abs(probabilities.sum() + (1.0 - mass) - 1.0) < 1e-14
    data = dict(n_qubits=np.array(qubits, dtype=np.int64), hashes=hashes, offsets=offsets, eigenvalues=values, noise_std=noise_std, recovery_floor=np.array(floor), max_terms=np.array(512, dtype=np.int64))
    truth = dict(paulis=labels, probabilities=probabilities, p_identity=np.array(1.0 - mass), probe_paulis=probes, probe_spectrum=expected)
    metadata = dict(nonidentity_mass=float(mass), heavy_dynamic_range=float(weights.max() / weights.min()), minimum_heavy_probability=float(weights.min()), tail_mass=float(tail_mass), mean_heavy_weight=float(np.count_nonzero(labels[:count], axis=1).mean()), load_per_group=count / 2**hash_bits, independent_observation_max_error=maximum_error, hashes_commute=True, hashes_full_rank=True)
    return data, truth, metadata


def prepare():
    if (AUDIT / "plan.json").exists():
        raise FileExistsError("The predefined audit already exists; no cases are replaced")
    inventory = protected_inventory()
    write_json(AUDIT / "protected_before.json", inventory)
    plan = dict(frozen_sha256=digest(FROZEN), reference_sha256=digest(REFERENCE / "solver.py"), metrics_sha256=digest(REFERENCE / "metrics.py"), eligibility=dict(reference_score_strictly_above=0.9, reference_f1_at_least=0.98, reference_uncapped_loss_strictly_below=0.1), cases=[])
    assert plan["frozen_sha256"] == "1996fc1f78936055adf84e5ebca607c0dfae8b0b832077e4769f8716891c73a4"
    for region_index, specification in enumerate(REGIONS):
        for replicate in range(2):
            case_id = f"{region_index:02d}_{specification['name']}_{replicate}"
            seed = 810031 + 997 * region_index + 17 * replicate
            directory = AUDIT / "cases" / case_id
            directory.mkdir(parents=True, exist_ok=False)
            data, truth, metadata = generate(specification, seed)
            np.savez_compressed(directory / "input.npz", **data)
            np.savez_compressed(directory / "truth.npz", **truth)
            record = dict(id=case_id, seed=seed, replicate=replicate, **specification, **metadata, input_sha256=digest(directory / "input.npz"), truth_sha256=digest(directory / "truth.npz"))
            plan["cases"].append(record)
            print(f"prepared {case_id} seed={seed}", flush=True)
    write_json(AUDIT / "plan.json", plan)
    assert protected_inventory() == inventory


def read_archive(path):
    with np.load(path, allow_pickle=False) as archive:
        return dict(archive)


def support_diagnostics(prediction, truth, floor):
    expected = {row.tobytes(): float(weight) for row, weight in zip(truth["paulis"], truth["probabilities"])}
    actual = {row.tobytes(): float(weight) for row, weight in zip(prediction["paulis"], prediction["probabilities"]) if weight > 0}
    heavy = {key for key, value in expected.items() if value >= floor}
    stable = {key for key, value in expected.items() if value >= 2 * floor}
    mass = sum(expected.values())
    stable_mass = sum(expected[key] for key in stable)
    common = stable & set(actual)
    errors = [abs(actual[key] - expected[key]) / expected[key] for key in common]
    return dict(heavy_labels_absent=len(heavy - set(actual)), missing_heavy_mass_fraction=sum(expected[key] for key in heavy - set(actual)) / mass, stable_labels_absent=len(stable - set(actual)), stable_label_count=len(stable), stable_probability_relative_l1=sum(abs(actual.get(key, 0.0) - expected[key]) for key in stable) / stable_mass if stable_mass else None, shared_stable_relative_error_quantiles=np.quantile(errors, [0.5, 0.95, 1.0]).tolist() if errors else None)


def compare_predictions(reference, frozen, truth, floor):
    left = {row.tobytes(): float(value) for row, value in zip(reference["paulis"], reference["probabilities"]) if value > 0}
    right = {row.tobytes(): float(value) for row, value in zip(frozen["paulis"], frozen["probabilities"]) if value > 0}
    true = {row.tobytes(): float(value) for row, value in zip(truth["paulis"], truth["probabilities"]) if value >= floor}
    mass = float(np.sum(truth["probabilities"]))
    union = set(left) | set(right)
    left_remaining = max(0.0, 1.0 - float(reference["p_identity"]) - sum(left.values()))
    right_remaining = max(0.0, 1.0 - float(frozen["p_identity"]) - sum(right.values()))
    uniform_difference = (left_remaining - right_remaining) * 4.0 ** (-truth["paulis"].shape[1])
    distance = sum(abs(left.get(key, 0.0) - right.get(key, 0.0) + uniform_difference) for key in union)
    distance += abs(left_remaining - right_remaining) * (1 - (1 + len(union)) * 4.0 ** (-truth["paulis"].shape[1]))
    return dict(prediction_nonidentity_l1_over_truth_mass=distance / mass, reference_only_heavy_labels=len((set(left) & set(true)) - set(right)), frozen_only_heavy_labels=len((set(right) & set(true)) - set(left)))


def run():
    plan = json.loads((AUDIT / "plan.json").read_text())
    before = json.loads((AUDIT / "protected_before.json").read_text())
    assert protected_inventory() == before
    assert digest(FROZEN) == plan["frozen_sha256"]
    results = []
    for case in plan["cases"]:
        directory = AUDIT / "cases" / case["id"]
        assert digest(directory / "input.npz") == case["input_sha256"]
        assert digest(directory / "truth.npz") == case["truth_sha256"]
        result_path = directory / "result.json"
        if result_path.exists():
            results.append(json.loads(result_path.read_text()))
            continue
        data = read_archive(directory / "input.npz")
        truth = read_archive(directory / "truth.npz")
        floor = float(data["recovery_floor"])
        result = dict(id=case["id"], region=case["name"], seed=case["seed"], eligible=False, excluded_reasons=[])
        predictions = {}
        calibration = {}
        for name, source in (("reference", REFERENCE / "solver.py"), ("weak", REFERENCE / "weak_solver.py")):
            prediction, details = evaluator.run_solver(source, directory / "input.npz", directory / f"{name}_prediction.npz")
            result[name] = details
            if prediction is not None:
                predictions[name] = prediction
                calibration[name] = measure(prediction, truth, floor)
                result[name].update(calibration[name])
        if len(calibration) == 2:
            for name in ("reference", "weak"):
                result[name].update(grade(calibration[name], calibration))
            strong = result["reference"]
            if strong["score"] <= 0.9:
                result["excluded_reasons"].append("reference_score_not_above_0.9")
            if strong["recovery_score"] < 0.98:
                result["excluded_reasons"].append("reference_F1_below_0.98")
            if strong["loss"] >= 0.1:
                result["excluded_reasons"].append("reference_uncapped_loss_not_below_0.1")
            result["eligible"] = not result["excluded_reasons"]
        else:
            result["excluded_reasons"].append("reference_or_weak_execution_failed")
        if result["eligible"]:
            result["reference"]["absolute_diagnostics"] = support_diagnostics(predictions["reference"], truth, floor)
            prediction, details = evaluator.run_solver(FROZEN, directory / "input.npz", directory / "frozen_prediction.npz")
            result["frozen"] = details
            if prediction is not None:
                result["frozen"].update(grade(measure(prediction, truth, floor), calibration))
                result["frozen"]["absolute_diagnostics"] = support_diagnostics(prediction, truth, floor)
                result["comparison"] = compare_predictions(predictions["reference"], prediction, truth, floor)
            else:
                result["frozen"].update(score=0.0, recovery_score=0.0)
        write_json(result_path, result)
        results.append(result)
        frozen_score = result.get("frozen", {}).get("score")
        print(f"{case['id']} eligible={result['eligible']} reference={result['reference'].get('score')} frozen={frozen_score} F1={result.get('frozen', {}).get('recovery_score')} reasons={result['excluded_reasons']}", flush=True)
        write_json(AUDIT / "results.json", dict(complete=False, cases=results))
    after = protected_inventory()
    write_json(AUDIT / "protected_after.json", after)
    assert after == before
    retained = [case for case in results if case["eligible"]]
    successful = [case for case in retained if case["frozen"]["status"] == "ok"]
    summary = dict(total_predefined=len(results), retained=len(retained), excluded=len(results) - len(retained), protected_files_unchanged=True, frozen_sha256=digest(FROZEN), reference_mean=float(np.mean([case["reference"]["score"] for case in retained])) if retained else None, frozen_mean=float(np.mean([case["frozen"]["score"] for case in retained])) if retained else None, frozen_minimum_score=min((case["frozen"]["score"] for case in retained), default=None), frozen_minimum_f1=min((case["frozen"]["recovery_score"] for case in retained), default=None), maximum_score_deficit=max((case["reference"]["score"] - case["frozen"]["score"] for case in retained), default=None), maximum_prediction_distance=max((case["comparison"]["prediction_nonidentity_l1_over_truth_mass"] for case in successful), default=None), maximum_missing_heavy_mass_fraction=max((case["frozen"]["absolute_diagnostics"]["missing_heavy_mass_fraction"] for case in successful), default=None))
    write_json(AUDIT / "results.json", dict(complete=True, summary=summary, cases=results))
    print(json.dumps(summary, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    arguments = parser.parse_args()
    if arguments.action == "prepare":
        prepare()
    else:
        run()


if __name__ == "__main__":
    main()
