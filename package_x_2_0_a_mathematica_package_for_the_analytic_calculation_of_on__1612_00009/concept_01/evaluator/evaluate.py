import argparse
import csv
import hashlib
import json
import math
import os
import resource
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("uv", "ir2", "ir1", "finite")


def load(path):
    return json.loads(Path(path).read_text())


def vector(values):
    return np.array([complex(*values[channel]) for channel in CHANNELS])


def execute(submission, request_path, destination, profile="production", timeout=240, runner="run.sh"):
    destination.mkdir(parents=True, exist_ok=True)
    scratch = destination / "scratch"
    scratch.mkdir(exist_ok=True)
    command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
               "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
               "--symlink", "usr/bin", "/bin", "--dir", "/etc",
               "--ro-bind", "/etc/alternatives", "/etc/alternatives",
               "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
               "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
               "--ro-bind", str(submission), "/submission", "--ro-bind", str(request_path), "/requests.json",
               "--bind", str(scratch), "/scratch", "--chdir", "/submission",
               "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
               "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
               "--setenv", "MKL_NUM_THREADS", "1", "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
               "--", "/usr/bin/time", "-f", "%e %U %S %M", "-o", "/scratch/resource.txt",
               "bash", "/submission/" + runner, "--requests", "/requests.json",
               "--output", "/scratch/predictions.json", "--profile", profile]
    started = time.perf_counter()

    def one_cpu():
        available = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(available)})

    with (destination / "stdout.txt").open("w") as output, (destination / "stderr.txt").open("w") as error:
        try:
            completed = subprocess.run(command, stdout=output, stderr=error, timeout=timeout, preexec_fn=one_cpu)
            returncode = completed.returncode
        except subprocess.TimeoutExpired:
            returncode = 124
    elapsed = time.perf_counter() - started
    usage = {"wall_seconds": elapsed, "peak_rss_kib": None}
    try:
        wall, user, system, memory = (scratch / "resource.txt").read_text().strip().splitlines()[-1].split()
        usage.update({"user_seconds": float(user), "system_seconds": float(system), "peak_rss_kib": int(memory)})
    except (ValueError, FileNotFoundError):
        pass
    payload = None
    try:
        if returncode == 0:
            payload = load(scratch / "predictions.json")
    except (ValueError, FileNotFoundError):
        pass
    return payload, usage, returncode


def core_score(predicted, truth):
    if not isinstance(predicted, dict):
        predicted = {}
    actual = {case["id"]: case for case in (predicted or {}).get("cases", [])}
    families = {}
    details = []
    for case in truth["cases"]:
        scores = []
        for identifier, integral in case["integrals"].items():
            for order, expected in integral["coefficients"].items():
                error = float("inf")
                try:
                    returned = vector(actual[case["id"]]["integrals"][identifier]["coefficients"][order])
                    target = vector(expected)
                    error = float(np.max(np.abs(returned - target)) / max(float(np.max(np.abs(target))), 1e-100))
                    if not math.isfinite(error):
                        error = float("inf")
                except (KeyError, ValueError, TypeError):
                    pass
                score = max(0.0, min(1.0, -math.log10(max(error, 1e-15)) / 9)) if math.isfinite(error) else 0.0
                scores.append(score)
                details.append({"case_id": case["id"], "integral": identifier, "order": order,
                                "relative_error": error if math.isfinite(error) else None, "score": score})
        families[case["family"]] = float(np.mean(scores))
    mean = float(np.mean(list(families.values())))
    worst = min(families.values())
    return 0.8 * mean + 0.2 * worst, families, details


def table_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def table_matches(rows, predictions, profile):
    lookup = {case["id"]: case for case in predictions["cases"]}
    selected = [row for row in rows if row["profile"] == profile]
    if not selected:
        return False
    expected_keys = {(case["id"], identifier, order) for case in predictions["cases"]
                     for identifier, integral in case["integrals"].items() for order in integral["coefficients"]}
    keys = {(row["case_id"], row["integral_id"], row["order"]) for row in selected}
    if keys != expected_keys or len(keys) != len(selected):
        return False
    for row in selected:
        result = lookup[row["case_id"]]["integrals"][row["integral_id"]]
        expected = vector(result["coefficients"][row["order"]])
        returned = np.array([complex(float(row[channel + "_re"]), float(row[channel + "_im"])) for channel in CHANNELS])
        if np.max(np.abs(returned - expected)) > 1e-6 * max(float(np.max(np.abs(expected))), 1e-100):
            return False
        if float(row["work"]) != result["work"]:
            return False
        measured = float(row["seconds"])
        if measured < 0 or measured > max(0.2, 20 * result["seconds"]):
            return False
    return True


def extended_table_checker(submission, destination, reruns, tables):
    requests = {}
    for path in (submission / "workspace").glob("*.json"):
        payload = load(path)
        if isinstance(payload, dict):
            for case in payload.get("cases", []):
                if isinstance(case, dict) and isinstance(case.get("integrals"), list):
                    requests[case["id"]] = case
    requests.update({case["id"]: case for case in load(ROOT / "participant/v_01/input/release.json")["cases"]})
    profiles = load(submission / "workspace/profiles.json")
    manifest = {name: {"runner": "run.sh", "profile": name, "settings_file": "workspace/profiles.json"}
                for name in profiles}
    if (submission / "configuration_manifest.json").exists():
        manifest.update(load(submission / "configuration_manifest.json"))
    cache = {(profile, case["id"]): case for profile, payload in reruns.items() if payload is not None
             for case in payload["cases"]}
    needed = {}
    for rows in tables:
        for row in rows:
            needed.setdefault(row["profile"], set()).add(row["case_id"])
            for column in row:
                if column.startswith("relative_to_") or column.startswith("max_relative_to_"):
                    target = column.split("relative_to_", 1)[1]
                    needed.setdefault(target, set()).add(row["case_id"])

    def resolve_profile(profile):
        entry = manifest[profile]
        for key in ("runner", "settings_file"):
            path = (submission / entry[key]).resolve()
            if submission not in path.parents:
                raise ValueError("Evidence manifest path leaves the submission")
        settings = load(submission / entry["settings_file"])[entry["profile"]]
        config_hash = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
        return entry, config_hash

    def ensure(profile, case_id):
        if (profile, case_id) not in cache:
            entry, config_hash = resolve_profile(profile)
            identifiers = sorted(needed.get(profile, {case_id}) | {case_id})
            identifiers = [identifier for identifier in identifiers if (profile, identifier) not in cache]
            directory = destination / ("extra_" + hashlib.sha256(profile.encode()).hexdigest()[:12])
            directory.mkdir(parents=True, exist_ok=True)
            request_path = directory / "requests.json"
            request_path.write_text(json.dumps({"cases": [requests[identifier] for identifier in identifiers]}))
            payload, _, returncode = execute(submission, request_path, directory, profile=entry["profile"], runner=entry["runner"])
            if payload is None:
                raise ValueError("Supplementary evidence rerun failed: " + profile)
            cache.update({(profile, case["id"]): case for case in payload["cases"]})
        return cache[profile, case_id]

    def components(values):
        return np.array([coordinate for channel in CHANNELS for coordinate in values[channel]])

    def disagreement(first, second, identifier, order):
        measured = components(first["integrals"][identifier]["coefficients"][order])
        reference = components(second["integrals"][identifier]["coefficients"][order])
        return float(np.max(np.abs(measured - reference)) / max(float(np.max(np.abs(reference))), 1e-300))

    def check(rows):
        valid = bool(rows)
        for row in rows:
            case = ensure(row["profile"], row["case_id"])
            entry, config_hash = resolve_profile(row["profile"])
            if "config_hash" in row:
                valid &= row["config_hash"] == config_hash
            trace = max([value["residual"] for value in case.get("observables", {}).values()] + [0.0])
            expected = {"trace_residual": trace}
            if row.get("integral_id"):
                identifier, order = row["integral_id"], row["order"]
                integral = case["integrals"][identifier]
                expected.update({"work": integral["work"], "estimated_error": integral["estimated_error"]})
                scale = max(float(np.max(np.abs(components(integral["coefficients"][order])))), 1e-300)
                for channel in CHANNELS:
                    for axis, suffix in enumerate(("_re", "_im")):
                        column = channel + suffix
                        if column in row:
                            valid &= abs(float(row[column]) - integral["coefficients"][order][channel][axis]) <= 1e-6 * scale
                for column in row:
                    if column.startswith("relative_to_"):
                        other = ensure(column[len("relative_to_"):], row["case_id"])
                        expected[column] = disagreement(case, other, identifier, order)
            else:
                expected["work"] = sum(value["work"] for value in case["integrals"].values())
                expected["max_internal_error"] = max(value["estimated_error"] for value in case["integrals"].values())
                for column in row:
                    if column.startswith("max_relative_to_"):
                        other = ensure(column[len("max_relative_to_"):], row["case_id"])
                        expected[column] = max(disagreement(case, other, identifier, order)
                                               for identifier, integral in case["integrals"].items() for order in integral["coefficients"])
            for column, value in expected.items():
                if column in row:
                    valid &= abs(float(row[column]) - value) <= 1e-8 * max(1, abs(value))
        return bool(valid)

    return check


def evidence(submission, destination):
    checks = {}
    try:
        profiles = load(submission / "workspace/profiles.json")
        primary, resource_usage, returncode = execute(submission, ROOT / "participant/v_01/input/release.json", destination / "public")
        if primary is None:
            return 0.0, {"public_rerun": False}
        results = table_rows(submission / "results.csv")
        ablation = table_rows(submission / "ablation.csv")
        scaling = table_rows(submission / "scaling.csv")
        checks["results_match_rerun"] = table_matches(results, primary, "production")
        used_profiles = sorted(set(row["profile"] for row in ablation))
        hashes = {name: hashlib.sha256(json.dumps(profiles[name], sort_keys=True).encode()).hexdigest() for name in used_profiles}
        checks["distinct_configurations"] = len(set(hashes.values())) >= 2
        checks["configuration_hashes"] = all(row["config_hash"] == hashes[row["profile"]] for row in ablation)
        reruns = {"production": primary}
        for profile in used_profiles:
            if profile != "production":
                reruns[profile], _, _ = execute(submission, ROOT / "participant/v_01/input/release.json", destination / profile, profile=profile)
        checks["ablation_matches_rerun"] = all(reruns[profile] is not None and table_matches(ablation, reruns[profile], profile)
                                                  for profile in used_profiles)
        resource_rows_valid = bool(scaling)
        for row in scaling:
            case = next(case for case in reruns[row["profile"]]["cases"] if case["id"] == row["case_id"])
            work = sum(integral["work"] for integral in case["integrals"].values())
            resource_rows_valid &= float(row["work"]) == work
            resource_rows_valid &= 0 <= float(row["seconds"]) <= max(0.2, 20 * case["seconds"])
        checks["scaling_matches_work"] = bool(resource_rows_valid)
        claims = load(submission / "claims.json")["claims"]
        claim_tables = {}
        for claim in claims:
            path = (submission / claim["table"]).resolve()
            if path.parent != submission or path.suffix != ".csv":
                raise ValueError("Claim tables must be submitted root-level CSV files")
            claim_tables[claim["table"]] = table_rows(path)
        figure_rows = table_rows(submission / "figures/primary_result.csv")
        scaling_source = table_rows(submission / "figures/robustness_or_scaling.csv")
        check_extended = extended_table_checker(submission, destination, reruns,
                                                [ablation, scaling, figure_rows, scaling_source] + list(claim_tables.values()))
        valid_claims = bool(claims)
        for claim in claims:
            rows = claim_tables[claim["table"]]
            selected = [row for row in rows if not claim["case_ids"] or row["case_id"] in claim["case_ids"]]
            first = [float(row[claim["metric"]]) for row in selected if row["profile"] == claim["left_profile"]]
            second = [float(row[claim["metric"]]) for row in selected if row["profile"] == claim["right_profile"]]
            if not first or not second:
                valid_claims = False
                continue
            left, right = float(np.mean(first)), float(np.mean(second))
            valid_claims &= (left <= right + 1e-10) if claim["relation"] == "<=" else (left >= right - 1e-10)
        valid_claims &= all(check_extended(rows) for rows in claim_tables.values())
        checks["quantitative_claims_supported"] = bool(valid_claims)
        figure_data_valid = all((submission / "figures" / (name + ".png")).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
                                for name in ("primary_result", "robustness_or_scaling"))
        figure_data_valid &= check_extended(figure_rows) and check_extended(scaling_source)
        checks["figure_source_data"] = bool(figure_data_valid)
        baseline_files = list((submission / "baseline").rglob("*.json"))
        baseline_target = load(ROOT / "evaluator/baseline_predictions.json")
        matching_baseline = False
        for path in baseline_files:
            try:
                score, _, _ = core_score(load(path), baseline_target)
                matching_baseline |= score > 0.999
            except (ValueError, KeyError, TypeError):
                pass
        checks["baseline_reproduced"] = matching_baseline
        checks["technical_report"] = (submission / "report.md").is_file() and len((submission / "report.md").read_text()) > 400
    except (KeyError, ValueError, FileNotFoundError, TypeError, StopIteration) as error:
        checks["artifact_error"] = str(error)
    booleans = [value for value in checks.values() if isinstance(value, bool)]
    return sum(booleans) / 9, checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--reference-cpu-seconds", type=float, default=5.13)
    arguments = parser.parse_args()
    submission = Path(arguments.submission).resolve()
    output = Path(arguments.output).resolve()
    destination = output.parent / (output.stem + "_runs")
    destination.mkdir(parents=True, exist_ok=True)
    truth = load(ROOT / "solution/v_01/hidden_predictions.json")
    predicted, usage, returncode = execute(submission, ROOT / "evaluator/hidden/requests.json", destination / "hidden")
    score, families, details = core_score(predicted, truth)
    cpu_seconds = usage.get("user_seconds", usage["wall_seconds"]) + usage.get("system_seconds", 0)
    efficiency = min(1.0, (arguments.reference_cpu_seconds + 0.05) / (cpu_seconds + 0.05)) ** 0.25
    memory_ok = usage["peak_rss_kib"] is not None and usage["peak_rss_kib"] < 1024 ** 2
    if not memory_ok or returncode:
        efficiency = 0.0
    evidence_score, checks = (0.0, {}) if arguments.core_only else evidence(submission, destination / "evidence")
    memory_factor = min(1.0, 1024 ** 2 / max(usage["peak_rss_kib"] or 1, 1))
    overall = score * (0.82 + 0.10 * efficiency + 0.08 * evidence_score) * memory_factor
    classification = "too_easy" if score >= 0.90 else "moderate" if score >= 0.60 else "potentially_hard"
    if predicted is None:
        classification = "execution_failure_requires_audit"
    result = {"core_score": score, "overall_score": overall, "per_family": families, "minimum_family_score": min(families.values()),
              "efficiency_score": efficiency, "evidence_score": evidence_score, "resource_metrics": usage,
              "returncode": returncode, "classification": classification, "evidence_checks": checks,
              "scoring": {"relative_digit_target": 9, "mean_family_weight": 0.8, "minimum_family_weight": 0.2,
                          "reference_cpu_seconds": arguments.reference_cpu_seconds, "candidate_cpu_seconds": cpu_seconds,
                          "wall_limit_seconds": 240, "rss_limit_kib": 1024 ** 2}, "details": details}
    output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({key: value for key, value in result.items() if key != "details"}, indent=2))


if __name__ == "__main__":
    main()
