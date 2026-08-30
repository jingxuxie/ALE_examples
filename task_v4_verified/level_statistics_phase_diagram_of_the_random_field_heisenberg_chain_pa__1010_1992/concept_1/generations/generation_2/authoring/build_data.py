from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "OMP_THREAD_LIMIT"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np

from generators import FAMILIES, sample_fields
from physics import hamiltonian, observables, sector


def read_records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def write_records(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n"
                            for record in records))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(fields):
    values = np.asarray(fields, dtype=float)
    values = values - values.mean()
    return min(tuple(np.round(np.roll(orientation, shift), 11))
               for orientation in (values, -values, values[::-1], -values[::-1])
               for shift in range(len(values)))


def simulate(case):
    result = observables(case["fields"])
    if result["dimension"] != 3432 or not 0 <= result["f"] <= 1:
        raise ValueError("Invalid L14 exact-diagonalization result")
    return dict(case, f=result["f"], min_gap=result["min_gap"], dimension=result["dimension"])


def summarize(records):
    counts = Counter((case["L"], case["family"]) for case in records)
    families = {}
    for family in FAMILIES:
        selected = [case["f"] for case in records if case["family"] == family]
        families[family] = {"count": len(selected), "f_min": min(selected), "f_max": max(selected),
                            "f_mean": float(np.mean(selected)), "f_std": float(np.std(selected))}
    return {"records": len(records), "strata": {f"L{length}/{family}": count for (length, family), count in sorted(counts.items())},
            "families": families,
            "minimum_field_separation": min(float(np.min(np.diff(np.sort(case["fields"])))) for case in records)}


def main():
    started = time.monotonic()
    public = ROOT / "participant/input"
    private = ROOT / "evaluator/hidden"
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    if (private / "manifest.json").exists():
        raise RuntimeError("Completed data package exists; refusing regeneration")
    auxiliary = []
    for name, destination in (("train", "auxiliary_train_L10_L12.jsonl"),
                              ("validation", "auxiliary_validation_L10_L12.jsonl")):
        source = SOURCE / "participant/input" / f"{name}.jsonl"
        (public / destination).write_bytes(source.read_bytes())
        records = read_records(source)
        if any(case["L"] not in (10, 12) for case in records):
            raise ValueError("Auxiliary data must be the original public L10/L12 records")
        auxiliary.extend(records)
    source_bank = SOURCE / "adversary/broad_prediction_bank.jsonl"
    bank = [case for case in read_records(source_bank) if case["L"] == 14]
    if len(bank) != 320 or Counter(case["family"] for case in bank) != Counter({family: 80 for family in FAMILIES}):
        raise ValueError("Expected exactly 320 private L14 records, 80 per family")
    hidden = [dict({key: case[key] for key in ("L", "family", "fields", "f")}, id=f"g2_test_{index:05d}")
              for index, case in enumerate(bank)]
    seen = set()
    for case in auxiliary + hidden:
        fields = np.asarray(case["fields"], dtype=float)
        if not np.isfinite(fields).all() or np.min(np.diff(np.sort(fields))) <= 1e-8:
            raise ValueError("Invalid or degenerate source fields")
        if not np.isfinite(case["f"]) or not 0 <= case["f"] <= 1:
            raise ValueError("Invalid source label")
        signature = canonical(fields)
        if signature in seen:
            raise ValueError("Duplicate source records under exact physical symmetries")
        seen.add(signature)
    write_records(private / "test.jsonl", hidden)
    pending_path = ROOT / "authoring/generated_cases.json"
    if pending_path.exists():
        generation = json.loads(pending_path.read_text())
        cases = generation["cases"]
        for case in cases:
            signature = canonical(case["fields"])
            if signature in seen:
                raise ValueError("Checkpoint fields overlap another split")
            seen.add(signature)
    else:
        seeds = {name: secrets.randbits(128) for name in ("train", "validation")}
        cases = []
        for name, per_family in (("train", 80), ("validation", 40)):
            rng = np.random.default_rng(seeds[name])
            selected = []
            for family in FAMILIES:
                for sample_index in range(per_family):
                    while True:
                        fields = sample_fields(rng, 14, family)
                        signature = canonical(fields)
                        if signature not in seen:
                            seen.add(signature)
                            break
                    selected.append({"L": 14, "family": family, "fields": fields, "split": name})
            rng.shuffle(selected)
            cases.extend(dict(case, id=f"g2_{name}_{index:05d}") for index, case in enumerate(selected))
        generation = {"seeds": seeds, "cases": cases, "created_utc": datetime.now(timezone.utc).isoformat()}
        write_json(pending_path, generation)
    checkpoint = ROOT / "authoring/simulation_results.jsonl"
    completed = {case["id"]: case for case in read_records(checkpoint)} if checkpoint.exists() else {}
    expected = {case["id"]: case for case in cases}
    for identity, result in completed.items():
        if identity not in expected or result["fields"] != expected[identity]["fields"]:
            raise ValueError("Simulation checkpoint does not match planned fields")
    remaining = [case for case in cases if case["id"] not in completed]
    print(json.dumps({"new_L14_labels": len(cases), "remaining": len(remaining), "workers": 16,
                      "private_hidden_records_reused": len(hidden), "auxiliary_records": len(auxiliary)}), flush=True)
    with checkpoint.open("a") as stream, ProcessPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(simulate, case) for case in remaining]
        for future in as_completed(futures):
            result = future.result()
            completed[result["id"]] = result
            stream.write(json.dumps(result, allow_nan=False, separators=(",", ":")) + "\n")
            stream.flush()
            if len(completed) % 16 == 0:
                print(f"L14 labels: {len(completed)}/480; elapsed {time.monotonic() - started:.1f}s", flush=True)
    manifest = {"generation": 2, "ratchet": 1, "created_utc": generation["created_utc"],
                "target_length": 14, "workers": 16, "blas_threads_per_worker": 1,
                "public_seeds": generation["seeds"], "cross_split_symmetry_duplicates": 0,
                "central_dimension": 3432, "central_rank_interval_zero_based": [1144, 2288],
                "eigenstates_per_target": 1144, "all_new_labels_simulated": True,
                "splits": {}}
    for name in ("train", "validation"):
        records = [completed[case["id"]] for case in cases if case["split"] == name]
        labels = [{key: case[key] for key in ("id", "L", "fields", "family", "f")} for case in records]
        destination = public / f"{name}.jsonl"
        write_records(destination, labels)
        statistics = summarize(labels)
        statistics.update({"sha256": digest(destination),
                           "minimum_central_spectral_gap": min(case["min_gap"] for case in records)})
        manifest["splits"][name] = statistics
        if name == "validation":
            write_json(public / "validation_cases.json", {"cases": [{key: case[key] for key in ("id", "L", "fields")} for case in labels]})
    manifest["splits"]["test"] = dict(summarize(hidden), sha256=digest(private / "test.jsonl"))
    manifest["private_hidden_source"] = {"source": "Original concept_1 private broad bank, L14 subset only",
                                          "sha256": digest(source_bank), "new_labels": False}
    manifest["auxiliary"] = {name: {"records": len(read_records(public / name)), "sha256": digest(public / name)}
                             for name in ("auxiliary_train_L10_L12.jsonl", "auxiliary_validation_L10_L12.jsonl")}
    evaluator_physics = ROOT / "evaluator/physics.py"
    participant_physics = ROOT / "participant/workspace/physics.py"
    assert evaluator_physics.read_bytes() == participant_physics.read_bytes()
    assert evaluator_physics.read_bytes() == (SOURCE / "evaluator/physics.py").read_bytes()
    manifest["physics_sha256"] = digest(evaluator_physics)
    manifest["generator_sha256"] = digest(ROOT / "participant/workspace/generators.py")
    states, spins, exchange, mode = sector(14)
    sample = cases[0]["fields"]
    matrix = hamiltonian(sample)
    expected_diagonal = np.sum(spins * np.roll(spins, -1, axis=1), axis=1) + spins @ sample
    np.testing.assert_allclose(np.diag(matrix), expected_diagonal, atol=1e-13, rtol=0)
    assert matrix.shape == (3432, 3432) and np.all(spins.sum(axis=1) == 0)
    assert np.max(np.abs(matrix - matrix.T)) == 0
    physics_checks = {"frozen_physics_identical_to_original": True,
                      "zero_Sz_dimension": len(states), "middle_third_states": 1144,
                      "periodic_J1_hamiltonian_symmetric": True,
                      "field_and_exchange_diagonal_check": "passed",
                      "observables": "Pal-Huse Eq. 6 mean of eigenstate ratios",
                      "new_labels": len(completed), "minimum_central_gap": min(case["min_gap"] for case in completed.values()),
                      "extra_diagonalizations_for_checks": 0}
    write_json(public / "physics_checks.json", physics_checks)
    manifest["creator_seconds"] = time.monotonic() - started
    write_json(private / "manifest.json", manifest)
    public_manifest = {key: value for key, value in manifest.items() if key not in ("splits", "private_hidden_source")}
    public_manifest["splits"] = {name: manifest["splits"][name] for name in ("train", "validation")}
    public_manifest["hidden_contract"] = {"records": 320, "length": 14, "records_per_family": 80,
                                           "law": "Same public family generators and amplitude mixture"}
    write_json(public / "data_checks.json", public_manifest)
    for name in ("champion_size_transfer_control.json", "baseline_size_stress.json"):
        (ROOT / "authoring" / name).write_bytes((SOURCE / "adversary" / name).read_bytes())
    print(json.dumps({"data_ready": True, "new_labels": len(completed),
                      "creator_seconds": manifest["creator_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
