import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import logging
import math
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
import generate as reference


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "private"
REFERENCE = PRIVATE / "reference"
MANIFEST = PRIVATE / "challenge_pool" / "manifest.json"
SPECIFICATION = importlib.util.spec_from_file_location("stress_scoring", PRIVATE / "evaluator.py")
SCORING = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(SCORING)


def rounded(value):
    return round(float(value), 12)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def weak_ladder(length, rung_mean, rung_amplitude, leg_mean, leg_amplitude, anisotropy):
    rungs = length // 2
    bonds = []
    for rung in range(rungs):
        coupling = rung_mean + rung_amplitude * math.cos(2 * math.pi * rung / (rungs - 1))
        bonds.append({"sites": [2 * rung, 2 * rung + 1], "jxy": rounded(coupling), "jz": rounded(anisotropy * coupling)})
    for rung in range(rungs - 1):
        for leg in [0, 1]:
            coupling = leg_mean + leg_amplitude * math.cos(2 * math.pi * (rung + 0.5) / (rungs - 1) + 0.2 * leg)
            bonds.append({"sites": [2 * rung + leg, 2 * rung + leg + 2], "jxy": rounded(coupling), "jz": rounded(anisotropy * coupling)})
    left_rung = rungs // 4
    pairs = [[2 * left_rung, 2 * left_rung + 1]]
    for distance in [1, 2, 4, 8, 12, rungs // 2]:
        for leg in [0, 1]:
            pairs.append([2 * left_rung, 2 * (left_rung + distance) + leg])
    return {
        "family": "spinhalf_ladder", "length": length, "spin": 0.5,
        "ground_sector": 0, "excited_sector": 1, "bonds": bonds,
        "single_ion": [0.0] * length,
        "field": [rounded(0.002 * math.cos(math.pi * (site // 2) / (rungs - 1)) + 0.001 * (-1) ** (site // 2 + site % 2)) for site in range(length)],
        "observables": [{"kind": kind, "sites": pair} for kind in ["zz", "xx"] for pair in pairs],
    }


def near_mott_boson(length, interaction_mean, interaction_amplitude, hopping_mean, hopping_amplitude, trap):
    left = length // 4
    distances = sorted(set([1, 2, 4, 8, 12, 16, 24, 32, length // 2]))
    return {
        "family": "bose_hubbard", "length": length, "nmax": 4, "particles": length,
        "bonds": [{"sites": [site, site + 1], "hopping": rounded(hopping_mean + hopping_amplitude * math.cos(2 * math.pi * (site + 0.5) / (length - 1)))} for site in range(length - 1)],
        "interaction": [rounded(interaction_mean + interaction_amplitude * math.cos(2 * math.pi * site / (length - 1))) for site in range(length)],
        "potential": [rounded(trap * (2 * site / (length - 1) - 1) ** 2 + 0.004 * (2 * site / (length - 1) - 1)) for site in range(length)],
        "observables": [{"kind": kind, "sites": [left, left + distance]} for kind in ["one_body", "density_connected"] for distance in distances],
    }


def stress_cases():
    return {
        "stress_ladder72_weak": weak_ladder(72, 0.590, 0.008, 1.650, 0.030, 1.008),
        "stress_ladder80_weak": weak_ladder(80, 0.545, 0.010, 1.780, 0.015, 0.998),
        "stress_boson64_nearmott": near_mott_boson(64, 4.080, 0.030, 1.230, 0.008, 0.050),
        "stress_boson80_nearmott": near_mott_boson(80, 4.120, 0.020, 1.220, 0.012, 0.080),
    }


def parameter_audit(case):
    length = case["length"]
    assert 32 <= length <= 80
    assert all(0 <= item["sites"][0] < item["sites"][1] < length for item in case["observables"])
    pairs = [tuple(bond["sites"]) for bond in case["bonds"]]
    assert len(set(pairs)) == len(pairs)
    if case["family"] == "spinhalf_ladder":
        rungs = length // 2
        expected = {(2 * rung, 2 * rung + 1) for rung in range(rungs)}
        expected.update((2 * rung + leg, 2 * rung + leg + 2) for rung in range(rungs - 1) for leg in [0, 1])
        assert set(pairs) == expected
        assert all(0.5 <= bond[key] <= 2.5 for bond in case["bonds"] for key in ["jxy", "jz"])
        assert all(0.85 <= bond["jz"] / bond["jxy"] <= 1.2 for bond in case["bonds"])
        assert max(abs(value) for value in case["field"]) <= 0.12
        rung_values = [bond["jxy"] for bond in case["bonds"] if bond["sites"][1] - bond["sites"][0] == 1]
        leg_values = [bond["jxy"] for bond in case["bonds"] if bond["sites"][1] - bond["sites"][0] == 2]
        assert min(rung_values) >= 0.53 and max(rung_values) <= 0.60
        assert min(leg_values) >= 1.6 and max(leg_values) <= 1.8
        return {"within_contract": True, "length": length, "rung_jxy": [min(rung_values), max(rung_values)], "leg_jxy": [min(leg_values), max(leg_values)], "rung_to_leg_envelope": [min(rung_values) / max(leg_values), max(rung_values) / min(leg_values)], "field_max_abs": max(abs(value) for value in case["field"])}
    assert set(pairs) == {(site, site + 1) for site in range(length - 1)}
    assert case["nmax"] == 4 and case["particles"] == length
    hopping = [bond["hopping"] for bond in case["bonds"]]
    assert 0.75 <= min(hopping) <= max(hopping) <= 1.25
    assert 4 <= min(case["interaction"]) <= max(case["interaction"]) <= 8
    assert max(abs(value) for value in case["potential"]) <= 0.8
    return {"within_contract": True, "length": length, "nmax": case["nmax"], "hopping": [min(hopping), max(hopping)], "interaction": [min(case["interaction"]), max(case["interaction"])], "interaction_to_hopping_envelope": [min(case["interaction"]) / max(hopping), max(case["interaction"]) / min(hopping)], "potential_max_abs": max(abs(value) for value in case["potential"])}


def without_stress(manifest):
    result = dict(manifest)
    result["splits"] = {name: entries for name, entries in manifest["splits"].items() if name != "stress"}
    return result


def prepare():
    manifest = json.loads(MANIFEST.read_text())
    snapshot_path = REFERENCE / "stress_preservation.json"
    if not snapshot_path.exists():
        protected = [PRIVATE / "evaluator.py", REFERENCE / "generate.py", REFERENCE / "cases.py"]
        frozen = json.loads((REFERENCE / "validation" / "participant_freeze.json").read_text())["files"]
        protected.extend(ROOT / "participant" / name for name in frozen)
        for split in ["core", "challenge"]:
            for entry in manifest["splits"][split]:
                protected.extend([PRIVATE / entry["input"], PRIVATE / entry["reference"]])
        hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        write_json(snapshot_path, {"files": hashes, "manifest_without_stress": without_stress(manifest)})
    cases = stress_cases()
    entries = []
    bounds = {}
    original_ids = {entry["id"] for split, values in manifest["splits"].items() if split != "stress" for entry in values}
    for case_id, case in cases.items():
        assert case_id not in original_ids
        bounds[case_id] = parameter_audit(case)
        input_name = f"challenge_pool/stress/{case_id}.json"
        write_json(PRIVATE / input_name, case)
        entries.append({"id": case_id, "family": case["family"], "input": input_name, "reference": f"reference/data/{case_id}.json"})
    if "stress" in manifest and manifest["splits"]["stress"] != entries:
        raise ValueError("refusing to overwrite a different stress split")
    manifest["splits"]["stress"] = entries
    write_json(MANIFEST, manifest)
    write_json(REFERENCE / "stress_bounds.json", bounds)
    return cases


def preservation_audit():
    snapshot = json.loads((REFERENCE / "stress_preservation.json").read_text())
    changed = [name for name, expected in snapshot["files"].items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    manifest_ok = without_stress(json.loads(MANIFEST.read_text())) == snapshot["manifest_without_stress"]
    return {"passed": not changed and manifest_ok, "changed_files": changed, "non_stress_manifest_unchanged": manifest_ok}


def quality_audit(case, result, weak, convergence):
    history = convergence["history"]
    sectors = history[-1]["sectors"]
    norm_error = max(item["norm_error"] for item in sectors)
    charge_error = max(abs(item["measured_sector"] - item["sector"]) for item in sectors)
    sweep_error = max(abs(item["last_sweep_energies"][-1] - item["last_sweep_energies"][-2]) / case["length"] for item in sectors)
    low_score, low_components = SCORING.score_output(case, result, weak, history[0]["result"])
    high_score, high_components = SCORING.score_output(case, result, weak, result)
    stages = []
    for stage in history:
        score, components = SCORING.score_output(case, result, weak, stage["result"])
        stages.append({"chi": stage["chi"], "score_against_final": score, "components": components, "difference_from_final": reference.differences(stage["result"], result, case["length"])})
    passed = convergence["ready"] and norm_error < 1e-7 and charge_error < 1e-7 and sweep_error < 1e-7
    return {"passed": passed, "norm_error": norm_error, "charge_error": charge_error, "last_sweep_energy_per_site_change": sweep_error, "chi128_score_against_final": low_score, "chi128_components": low_components, "strong_self_score": high_score, "strong_component_scales": {name: value["scale"] for name, value in high_components.items()}, "stages": stages}


def compute_one(case_id, case, chis):
    started = time.perf_counter()
    log_path = REFERENCE / "logs" / f"{case_id}.log"
    log_path.parent.mkdir(exist_ok=True)
    logging.basicConfig(filename=log_path, level=logging.INFO, force=True)
    original_optimize = reference.optimize
    completed = []

    def tracked_optimize(case, model, sector, chi, state=None):
        energy, state, statistics = original_optimize(case, model, sector, chi, state)
        entropies = state.entanglement_entropy()
        statistics["max_entropy"] = float(max(entropies))
        statistics["center_entropy"] = float(entropies[len(entropies) // 2])
        completed.append(statistics)
        write_json(REFERENCE / "progress" / f"{case_id}.json", {"case_id": case_id, "elapsed_seconds": time.perf_counter() - started, "completed_sectors": completed})
        return energy, state, statistics

    reference.optimize = tracked_optimize
    try:
        result, convergence = reference.calculate(case, chis)
        weak = reference.product_result(case)
        quality = quality_audit(case, result, weak, convergence)
        payload = {
            "case_id": case_id, "family": case["family"], "split": "stress", "ready": quality["passed"],
            "reference": result, "weak": weak, "convergence": convergence, "quality_audit": quality,
            "source": {"library": "TeNPy", "version": reference.tenpy.__version__, "commit": reference.TENPY_COMMIT},
            "input_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
            "generation_seconds": time.perf_counter() - started,
            "bounds": parameter_audit(case),
        }
    except Exception:
        payload = {"case_id": case_id, "ready": False, "error": traceback.format_exc(), "generation_seconds": time.perf_counter() - started}
    finally:
        reference.optimize = original_optimize
    write_json(REFERENCE / "data" / f"{case_id}.json", payload)
    return {"case_id": case_id, "ready": payload["ready"], "seconds": payload["generation_seconds"], "chis": [stage["chi"] for stage in payload.get("convergence", {}).get("history", [])], "error": payload.get("error")}


def audit():
    manifest = json.loads(MANIFEST.read_text())
    records = []
    for entry in manifest["splits"]["stress"]:
        path = PRIVATE / entry["reference"]
        case = json.loads((PRIVATE / entry["input"]).read_text())
        if not path.exists():
            records.append({"id": entry["id"], "ready": False, "reason": "reference_missing"})
            continue
        artifact = json.loads(path.read_text())
        expected_hash = hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()
        input_matches = artifact.get("input_sha256") == expected_hash
        record = {"id": entry["id"], "ready": artifact.get("ready", False) and input_matches, "input_hash_matches": input_matches, "bounds": parameter_audit(case), "generation_seconds": artifact.get("generation_seconds"), "last_chi_difference": artifact.get("convergence", {}).get("last_difference"), "quality": artifact.get("quality_audit"), "error": artifact.get("error")}
        records.append(record)
    preservation = preservation_audit()
    report = {"split": "stress", "ready": preservation["passed"] and all(record["ready"] for record in records), "case_count": len(records), "scoring_unchanged": True, "reference_limits_unchanged": reference.LIMITS, "preservation": preservation, "cases": records, "no_student_or_agent_run": True, "no_future_ratchet_cases_generated": True}
    write_json(REFERENCE / "stress_audit.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--chis", default="128,256,384,512")
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.audit:
        report = audit()
        print(json.dumps(report, indent=2), flush=True)
        raise SystemExit(0 if report["ready"] else 1)
    cases = prepare()
    if args.prepare:
        print(json.dumps({"prepared": list(cases), "preservation": preservation_audit()}), flush=True)
        return
    if args.case:
        cases = {args.case: cases[args.case]}
    chis = [int(value) for value in args.chis.split(",")]
    assert len(chis) >= 2 and chis[0] == 128 and chis[1] == 256 and chis == sorted(set(chis))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(compute_one, case_id, case, chis) for case_id, case in cases.items()]
        for future in as_completed(futures):
            print(json.dumps(future.result()), flush=True)
    report = audit()
    print(json.dumps({"ready": report["ready"], "case_count": report["case_count"], "preservation": report["preservation"]}), flush=True)
    raise SystemExit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
