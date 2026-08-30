"""Bounded, private, reproducible stress test of an already passing frozen policy."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
import queue
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path[:0] = [str(BASE / "evaluator"), str(BASE / "participant/input")]

import numpy as np

from evaluate import run_case
from hidden.generator import suite
from model import FAMILIES
from scoring import aggregate


def save(name, value):
    (HERE / name).write_text(json.dumps(value, allow_nan=False, indent=2) + "\n")


def tree_hash(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or any(part in ("__pycache__", ".scratch") for part in path.parts):
            continue
        digest.update(str(path.relative_to(directory)).encode())
        digest.update(b"\x00")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def fingerprints():
    result = {
        name: tree_hash(BASE / name)
        for name in ("participant", "evaluator", "attempts/v_1.frozen")
    }
    result["wrapper"] = hashlib.sha256((BASE.parent / "authoring/sandbox.py").read_bytes()).hexdigest()
    result["status"] = hashlib.sha256((BASE / "status.json").read_bytes()).hexdigest()
    return result


def numeric_summary(cases):
    valid = [case for case in cases if case["status"] == "ok"]
    result = {"count": len(cases), "valid": len(valid)}
    for key in ("loss", "point_loss", "interval_loss", "coverage90"):
        values = [case[key] for case in valid]
        result[key] = float(np.mean(values)) if values else None
        result[key + "_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
    result["target_point_losses"] = {
        target: float(np.mean([case["target_point_losses"][target] for case in valid]))
        for target in ("delta0", "log_gap", "log_a0", "theta0")
    } if valid else {}
    result["high_point_repeats"] = sum(case["point_loss"] > 0.22 for case in valid)
    result["low_coverage_repeats"] = sum(case["coverage90"] < 0.75 for case in valid)
    result["sustained_point_failure"] = bool(
        len(valid) == 10 and result["point_loss"] > 0.22 and result["loss"] > 0.165
        and result["high_point_repeats"] >= 6
    )
    result["sustained_calibration_failure"] = bool(
        len(valid) == 10 and result["coverage90"] < 0.6 and result["low_coverage_repeats"] >= 6
    )
    return result


def main():
    started = time.monotonic()
    deadline = started + 13 * 60
    official = json.loads((BASE / "attempts/v_1.evaluation.json").read_text())
    if not all(official.get(key) is True for key in ("passed", "valid", "official")):
        save("report.json", {
            "status": "no_champion_ratchet_needed", "official_result": official,
            "reason": "The completed official v1 report is not a valid official pass.",
        })
        print("No passing official champion; no stress cases run.", flush=True)
        return
    target_bytes = (BASE / "participant/input/target.json").read_bytes()
    target = json.loads(target_bytes)
    if official["target"] != target:
        raise RuntimeError("Official report target differs from current frozen target")
    assert target["max_robust_loss"] == 0.165
    assert target["max_worst_family_point_loss"] == 0.22
    before = fingerprints()
    wrapper = BASE.parent / "authoring/sandbox.py"
    scratch = HERE / "scratch"
    scratch.mkdir(exist_ok=True)
    key_file = BASE / "evaluator/hidden/seeds.json"
    private_key = bytes.fromhex(json.loads(key_file.read_text())["master_key_hex"])
    records = suite("adversary-v1", 64)
    records_by_id = {record["id"]: record for record in records}
    allowed_cpus = sorted(os.sched_getaffinity(0))
    worker_count = min(8, len(allowed_cpus))
    selected_cpus = [allowed_cpus[min(len(allowed_cpus) - 1, 1 + index * len(allowed_cpus) // worker_count)]
                     for index in range(worker_count)]
    cpu_queue = queue.Queue()
    for cpu in selected_cpus:
        cpu_queue.put(cpu)
    metadata = {
        "date": "2026-08-28", "split": "adversary-v1", "per_family": 64,
        "planned_cases": 384, "workers": worker_count, "worker_cpus": selected_cpus,
        "policy": "attempts/v_1.frozen/policy.py", "seconds_per_case": 45,
        "response_seconds": 15, "budget": 72, "wrapper_memory_mib": 2048,
        "official_pass_confirmed": True, "official_robust_loss": official["robust_loss"],
        "target_sha256": hashlib.sha256(target_bytes).hexdigest(),
        "seed_file_sha256": hashlib.sha256(key_file.read_bytes()).hexdigest(),
        "integrity_before": before,
        "counterexample_rule": "At least 3 same-family parameter instances with sustained fresh-noise failure; isolated misses excluded.",
    }
    save("metadata.json", metadata)
    private_records = []
    for record in records:
        parameters = asdict(record["instance"])
        parameters = {key: value.tolist() if isinstance(value, np.ndarray) else value
                      for key, value in parameters.items()}
        private_records.append({"id": record["id"], "instance": parameters,
                                "noise_seed": record["noise_seed"]})
    save("private_realizations.json", private_records)

    def initialize_worker():
        os.sched_setaffinity(0, {cpu_queue.get_nowait()})

    def execute(record):
        if time.monotonic() >= deadline:
            return {"id": record["id"], "family": record["instance"].family,
                    "status": "not_examined_deadline", "calls": 0}
        result = run_case(
            record, BASE / "attempts/v_1.frozen", "policy.py", BASE / "participant",
            scratch, seconds=45, line_seconds=15, sandbox_wrapper=wrapper,
        )
        result["worker_cpu"] = min(os.sched_getaffinity(0))
        if "parameter_id" in record:
            result["parameter_id"] = record["parameter_id"]
            result["repeat_index"] = record["repeat_index"]
        return result

    def batch(executor, entries, name):
        results = []
        with (HERE / (name + "_cases.jsonl")).open("w") as stream:
            futures = [executor.submit(execute, record) for record in entries]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                stream.write(json.dumps(result, allow_nan=False) + "\n")
                stream.flush()
                if len(results) % 24 == 0 or len(results) == len(entries):
                    print(f"{name}: {len(results)}/{len(entries)}, "
                          f"valid={sum(item['status'] == 'ok' for item in results)}, "
                          f"wall={time.monotonic() - started:.1f}s", flush=True)
        return results

    repeat_report = {"run": False, "reason": "No predeclared failure-cluster trigger.", "parameters": []}
    with ThreadPoolExecutor(max_workers=worker_count, initializer=initialize_worker) as executor:
        broad = batch(executor, records, "broad")
        completed = [case for case in broad if case["status"] != "not_examined_deadline"]
        measured = aggregate(completed, target, official=False)
        scientific_checks = {key: value for key, value in measured.get("target_checks", {}).items()
                             if key != "official_suite"}
        scientific_pass = bool(measured["valid"] and scientific_checks and all(scientific_checks.values()))
        complete_scope = len(completed) == 384
        broad_report = {
            "split": "adversary-v1", "scope_complete": complete_scope,
            "cases_examined": len(completed), "aggregate": measured,
            "scientific_checks": scientific_checks,
            "all_frozen_scientific_checks_pass": scientific_pass,
            "official": False, "cases": sorted(completed, key=lambda case: case["id"]),
            "note": "The official_suite flag is intentionally false; this is an independent private stress split.",
        }
        save("broad_report.json", broad_report)
        flagged = set()
        cluster_counts = {}
        for family in FAMILIES:
            selected = [case for case in completed if case["family"] == family and case["status"] == "ok"]
            high = [case for case in selected if case["point_loss"] > 0.22 and case["loss"] > 0.165]
            cluster_counts[family] = len(high)
            group = measured["families"][family]
            if len(high) >= 3 or (group["valid"] and (
                group["point_loss"] > 0.22 or group["loss"] > 0.165 or group["coverage90"] < 0.6
            )):
                flagged.add(family)
        if complete_scope and measured["valid"] and not scientific_pass and not flagged:
            flagged.add(min(FAMILIES, key=lambda family: measured["families"][family]["coverage90"]))
            flagged.add(max(FAMILIES, key=lambda family: measured["families"][family]["loss"]))
        candidates = [case for case in completed if case["status"] != "ok" or case["family"] in flagged]
        candidates.sort(key=lambda case: (
            case["status"] != "ok", case.get("point_loss", float("inf")), case.get("loss", float("inf")),
        ), reverse=True)
        candidates = candidates[:8]
        save("screening.json", {
            "high_error_counts": cluster_counts, "flagged_families": sorted(flagged),
            "selected_ids": [case["id"] for case in candidates],
            "worst_eight_broad_cases": sorted(
                [case for case in completed if case["status"] == "ok"],
                key=lambda case: case["loss"], reverse=True,
            )[:8],
            "note": "Worst individual observations are not independently claimed as counterexamples.",
        })
        if candidates and time.monotonic() < deadline - 50:
            repeat_records = []
            for candidate in candidates:
                original = records_by_id[candidate["id"]]
                for repeat_index in range(10):
                    label = f"noise/adversary-v1/repeat/{candidate['id']}/{repeat_index}"
                    noise_seed = int.from_bytes(hmac.new(private_key, label.encode(), hashlib.sha256).digest()[:16], "big")
                    repeat_records.append({
                        **original, "id": candidate["id"] + f"-repeat-{repeat_index}",
                        "parameter_id": candidate["id"], "repeat_index": repeat_index,
                        "noise_seed": noise_seed,
                    })
            repeated = batch(executor, repeat_records, "repeat")
            summaries = []
            for candidate in candidates:
                selected = [case for case in repeated if case.get("parameter_id") == candidate["id"]]
                summaries.append({"parameter_id": candidate["id"], "family": candidate["family"],
                                  "screening_case": candidate, **numeric_summary(selected)})
            repeat_report = {
                "run": True, "reason": "Predeclared family/error/validity trigger fired.",
                "parameters": summaries, "cases": repeated,
                "selected_parameters_are_not_a_population_sample": True,
            }
        elif candidates:
            repeat_report["reason"] = "Repeat trigger fired, but scheduling deadline prevented confirmation."
    save("repeat_report.json", repeat_report)
    sustained = {family: [] for family in FAMILIES}
    for parameter in repeat_report["parameters"]:
        if parameter["sustained_point_failure"] or parameter["sustained_calibration_failure"]:
            sustained[parameter["family"]].append(parameter["parameter_id"])
    reproduced = {family: identities for family, identities in sustained.items() if len(identities) >= 3}
    after = fingerprints()
    integrity = {key: before[key] == after[key] for key in before}
    if not all(integrity.values()):
        conclusion = "Artifact changes detected; main must assess integrity before interpreting this run."
    elif not complete_scope:
        conclusion = "Bounded run incomplete; do not claim a full 384-case stress pass."
    elif reproduced:
        conclusion = "A conditional same-family failure cluster reproduced; inspect cause and discuss with main before any new generation."
    elif scientific_pass:
        conclusion = "No meaningful counterexample found in this bounded search; the existing E task can remain solved."
    else:
        conclusion = "Broad scientific failure observed, but no sustained same-family cluster certified by the repeat rule."
    final = {
        "status": "complete", "scope": "384 independent private instances, 64 per public family",
        "scope_complete": complete_scope, "conclusion": conclusion,
        "all_frozen_scientific_checks_pass": scientific_pass,
        "core_score": measured["core_score"], "robust_loss": measured["robust_loss"],
        "worst_family_loss": measured.get("worst_family_loss"),
        "worst_family_score": measured.get("worst_family_score"),
        "worst_family_point_loss": measured.get("worst_family_point_loss"),
        "coverage90": measured.get("coverage90"),
        "worst_family_coverage90": measured.get("worst_family_coverage90"),
        "valid_cases": sum(case["status"] == "ok" for case in completed),
        "invalid_cases": sum(case["status"] != "ok" for case in completed),
        "call_counts": {str(count): sum(case["calls"] == count for case in completed)
                        for count in sorted({case["calls"] for case in completed})},
        "broad_case_runtime_seconds": measured["runtime_seconds"],
        "broad_runtime_score": measured["runtime_score"],
        "wall_seconds": time.monotonic() - started,
        "repeated_parameters": len(repeat_report["parameters"]),
        "reproduced_clusters": reproduced, "integrity_unchanged": integrity,
        "integrity_after": after, "families": measured["families"],
        "limitations": [
            "Finite private sampling does not prove uniform correctness over the continuous public domain.",
            "Isolated interval misses and selected extreme noise observations are not counterexamples.",
            "Any selected-parameter repeats are conditional diagnostics, not a replacement population score.",
            "No participant/evaluator/status files were written, and no new generation or agents were launched.",
        ],
    }
    save("report.json", final)
    lines = ["# Champion stress search 1", "", conclusion, "",
             f"- Official gate: passed, robust loss {official['robust_loss']:.8f}.",
             f"- Private scope: {len(completed)}/384 cases, 64 planned per family.",
             f"- Robust loss: {measured['robust_loss']}; frozen cap 0.165.",
             f"- Core score: {measured['core_score']:.6f}.",
             f"- Worst-family point loss: {measured.get('worst_family_point_loss')}; cap 0.22.",
             f"- Coverage: {measured.get('coverage90')}; worst family {measured.get('worst_family_coverage90')}.",
             f"- Valid cases: {final['valid_cases']}; invalid: {final['invalid_cases']}.",
             f"- Repeated parameter instances: {final['repeated_parameters']} (10 new noise draws each).",
             f"- Total search wall time: {final['wall_seconds']:.1f}s.",
             f"- Protected-tree integrity unchanged: {all(integrity.values())}.", "",
             "No participant edits or task ratchet are authorized by this report. This is finite-scope empirical evidence, not a proof."]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({key: value for key, value in final.items() if key not in ("families", "integrity_after")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
