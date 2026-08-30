import argparse
import hashlib
import importlib.util
import json
import multiprocessing
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


for environment_name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[environment_name] = "1"
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))

import numpy as np

from model import CONFIG, compile_experiments, draw_parameters, probabilities
from runtime import run_episode


SANDBOX_COMMAND = None


class SearchDeadline(Exception):
    pass


def overlaps(first, second):
    return first == second or first in second.parents or second in first.parents


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def submission_hashes(submission):
    hashes = {}
    total_bytes = 0
    for directory, subdirectories, filenames in os.walk(submission, followlinks=False):
        for name in subdirectories + filenames:
            if (Path(directory) / name).is_symlink():
                raise ValueError("submission must be a self-contained snapshot without symlinks")
        for filename in sorted(filenames):
            path = Path(directory) / filename
            total_bytes += path.stat().st_size
            if len(hashes) >= 1024 or total_bytes > 1024**3:
                raise ValueError("submission snapshot exceeds 1024 files or 1 GiB")
            if not path.is_file():
                raise ValueError("submission contains a nonregular file")
            hashes[str(path.relative_to(submission))] = file_hash(path)
    return hashes


def trusted_command(submission):
    helper_path = ROOT.parent / "authoring" / "sandbox.py"
    specification = importlib.util.spec_from_file_location("trusted_search_sandbox", helper_path)
    if specification is None or specification.loader is None:
        raise RuntimeError("trusted sandbox helper unavailable")
    helper = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(helper)
    command = helper.sandbox_command(ROOT / "participant", submission, entrypoint="solution.py", args=(), ready_marker=True)
    if Path(command[0]).name != "bwrap" or not os.access(command[0], os.X_OK):
        raise RuntimeError("search requires the trusted bwrap command; no unsafe fallback")
    if "--die-with-parent" not in command or "--unshare-all" not in command:
        raise RuntimeError("required sandbox lifetime or namespace isolation is absent")
    return command, helper_path


def initialize_worker(command):
    global SANDBOX_COMMAND
    SANDBOX_COMMAND = command


def evaluate_point(job):
    try:
        result = run_episode(SANDBOX_COMMAND, job["parameters"], job["measurement_seed"], startup_handshake=True)
    except Exception as error:
        result = {"valid": False, "infrastructure_error": True, "reason": "worker exception: " + repr(error), "nrmse": None}
    if result.get("infrastructure_error"):
        result["nrmse"] = None
    return {**job, "result": result}


def generate_points(seed, episodes):
    streams = np.random.SeedSequence(seed).spawn(episodes + 1)
    points = []
    for point_index in range(episodes):
        children = streams[point_index].spawn(5)
        parameter_seed = int(children[0].generate_state(1, dtype=np.uint64)[0])
        measurement_seeds = [int(child.generate_state(1, dtype=np.uint64)[0]) for child in children[1:]]
        family = CONFIG["suite"]["families"][point_index % 4]
        parameters = draw_parameters(np.random.default_rng(parameter_seed), family)
        points.append({"case_id": "case_" + str(point_index).zfill(5), "family": family,
                       "parameter_seed": parameter_seed, "parameters": parameters.tolist(),
                       "screening_seed": measurement_seeds[0], "repeat_seeds": measurement_seeds[1:]})
    np.random.default_rng(streams[-1]).shuffle(points)
    return points


def make_job(point, phase, measurement_seed, repeat_index=None):
    return {"case_id": point["case_id"], "family": point["family"], "parameters": point["parameters"],
            "parameter_seed": point["parameter_seed"], "phase": phase, "repeat_index": repeat_index,
            "measurement_seed": measurement_seed}


def collect(pool, jobs, destination, records, deadline):
    with destination.open("x") as stream:
        pending = pool.imap_unordered(evaluate_point, jobs, chunksize=1)
        for job_index in range(len(jobs)):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SearchDeadline("global search wall deadline reached")
                try:
                    record = pending.next(timeout=min(1.0, remaining))
                    break
                except multiprocessing.TimeoutError:
                    continue
            records.append(record)
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            stream.flush()
            result = record["result"]
            print(json.dumps({"phase": record["phase"], "done": job_index + 1, "total": len(jobs),
                              "case_id": record["case_id"], "family": record["family"], "nrmse": result["nrmse"],
                              "valid": result["valid"], "infrastructure_error": bool(result.get("infrastructure_error"))}),
                  file=sys.stderr, flush=True)


def fixed_schedule():
    calibration = [(["X+", "X+"], "IX"), (["X+", "X-"], "IX"),
                   (["X+", "X+"], "XI"), (["X-", "X+"], "XI"),
                   (["X+", "X+"], "XX"), (["X-", "X+"], "XX"),
                   (["Z+", "Z+"], "ZZ"), (["Z-", "Z+"], "ZZ")] * 2
    experiments = [{"prep": prep, "measure": measure, "time": 0.0, "shots": 128} for prep, measure in calibration]
    settings = [([control, target], "I" + axis) for control in ("Z+", "Z-") for target in ("X+", "Z+") for axis in "XYZ"]
    settings += [(["X+", target], axis + "I") for target in ("X+", "Z+") for axis in "XY"]
    for duration in [0.10, 0.19, 0.34, 0.58, 0.97, 1.53, 2.39, 3.71, 5.63, 8.17, 11.77]:
        experiments.extend({"prep": prep, "measure": measure, "time": duration, "shots": 128} for prep, measure in settings)
    return experiments


def local_fisher(parameters):
    batch = compile_experiments(fixed_schedule())
    parameters = np.asarray(parameters)
    center = probabilities(parameters, batch)
    columns = []
    for parameter_index in range(9):
        step = np.zeros(9)
        step[parameter_index] = 1e-5
        columns.append((probabilities(parameters + step, batch) - probabilities(parameters - step, batch)) / 2e-5)
    jacobian = np.stack(columns, axis=1) * np.array(CONFIG["normalization"] + [1, 1, 1, 1])
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    rank = int(np.linalg.matrix_rank(jacobian, tol=1e-7))
    fisher = jacobian.T @ ((128 / (center * (1 - center)))[:, None] * jacobian)
    bound = None
    if rank == 9:
        covariance = np.linalg.inv(fisher)
        bound = float(np.sqrt(max(0.0, np.trace(covariance[:5, :5]) / 5)))
    return {"rank": rank, "minimum_singular_value": float(singular_values[-1]), "local_crlb_rms": bound,
            "limited_fixed_design_information": rank < 9 or bound > CONFIG["target"]["worst_family_mean_nrmse"],
            "warning": "Nuisance-profiled local unbiased fixed-design bound only; not a fundamental limit or proof of algorithmic failure"}


def summarize_screening(records):
    usable = [record for record in records if not record["result"].get("infrastructure_error")]
    valid = [record for record in usable if record["result"]["valid"]]
    return {"completed": len(records), "infrastructure_errors": len(records) - len(usable), "valid": len(valid),
            "invalid": len(usable) - len(valid),
            "mean_valid_nrmse": float(np.mean([record["result"]["nrmse"] for record in valid])) if valid else None,
            "family_mean_valid_nrmse": {family: float(np.mean([record["result"]["nrmse"] for record in valid if record["family"] == family]))
                                        for family in CONFIG["suite"]["families"] if any(record["family"] == family for record in valid)}}


def repeat_summary(screen, repeats, fisher=None):
    usable = [record for record in repeats if not record["result"].get("infrastructure_error")]
    valid = [record for record in usable if record["result"]["valid"]]
    errors = [record["result"]["nrmse"] for record in valid]
    cutoff = CONFIG["target"]["worst_family_mean_nrmse"]
    summary = {"case_id": screen["case_id"], "family": screen["family"], "parameters": screen["parameters"],
               "screening_nrmse": screen["result"]["nrmse"], "repeat_count": len(repeats),
               "repeat_valid_count": len(valid), "repeat_infrastructure_errors": len(repeats) - len(usable),
               "repeat_invalid_count": len(usable) - len(valid), "repeat_errors": errors,
               "repeat_measurement_seeds": [record["measurement_seed"] for record in repeats],
               "median_repeat_nrmse": float(np.median(errors)) if errors else None,
               "diagnostic_cutoff": cutoff, "above_cutoff": sum(error > cutoff for error in errors),
               "fisher": fisher, "cluster": "inconclusive_repeats"}
    if len(repeats) != 3 or len(usable) != 3:
        return summary
    if len(valid) < 2:
        summary["cluster"] = "repeatable_protocol_or_resource_failure"
        return summary
    if len(valid) != 3:
        summary["cluster"] = "mixed_validity"
        return summary
    estimates = np.array([record["result"]["omega"] for record in valid])
    truth = np.array(screen["parameters"][:5])
    normalization = np.array(CONFIG["normalization"])
    median_estimate = np.median(estimates, axis=0)
    signed_bias = (median_estimate - truth) / normalization
    spread = float(np.sqrt(np.mean(((estimates - median_estimate) / normalization)**2)))
    frequencies = lambda omega: np.array([np.hypot(omega[0] + omega[1], omega[2] + omega[3]),
                                          np.hypot(omega[0] - omega[1], omega[2] - omega[3]), omega[4]])
    frequency_error = float(np.max(np.abs(frequencies(median_estimate) - frequencies(truth))))
    summary.update({"median_estimate": median_estimate.tolist(), "normalized_signed_bias": signed_bias.tolist(),
                    "dominant_coefficient": CONFIG["parameter_order"][int(np.argmax(np.abs(signed_bias)))],
                    "normalized_repeat_spread": spread, "maximum_frequency_or_zi_error": frequency_error})
    if summary["above_cutoff"] < 2:
        summary["cluster"] = "not_reproduced_above_cutoff"
    elif spread < 0.5 * summary["median_repeat_nrmse"]:
        summary["cluster"] = "stable_alias_or_frequency_mode_candidate" if frequency_error > 0.25 else "stable_axis_or_spam_bias_candidate"
    elif screen["family"] == "nuisance_decoherence":
        summary["cluster"] = "repeatable_nuisance_precision_candidate"
    else:
        summary["cluster"] = "repeatable_estimation_error"
    return summary


def grouped_clusters(summaries):
    groups = {}
    for summary in summaries:
        key = summary["family"] + "/" + summary["cluster"] + "/" + summary.get("dominant_coefficient", "unavailable")
        groups.setdefault(key, []).append(summary)
    return [{"cluster": key, "case_ids": [item["case_id"] for item in items], "count": len(items),
             "median_case_repeat_nrmse": float(np.median([item["median_repeat_nrmse"] for item in items if item["median_repeat_nrmse"] is not None]))
             if any(item["median_repeat_nrmse"] is not None for item in items) else None,
             "fixed_design_information_flags": sum(bool(item["fisher"] and item["fisher"]["limited_fixed_design_information"]) for item in items)}
            for key, items in sorted(groups.items())]


def main():
    parser = argparse.ArgumentParser(description="Private generation-only search; run champions only after a completed, scored passing submission is authorized")
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=128)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repeat-worst", type=int, default=12)
    parser.add_argument("--fisher", action="store_true", help="fixed-schedule local Fisher diagnostics at selected parameter points")
    parser.add_argument("--max-wall-seconds", type=int, default=900)
    arguments = parser.parse_args()
    if not 1 <= arguments.episodes <= 512 or not 1 <= arguments.jobs <= 8:
        parser.error("episodes must be 1..512; jobs must be 1..8")
    if not 0 <= arguments.repeat_worst <= min(64, arguments.episodes):
        parser.error("repeat-worst must be 0..min(64,episodes); use 0 for a two-episode smoke run")
    if not 30 <= arguments.max_wall_seconds <= 3600 or (arguments.seed is not None and not 0 <= arguments.seed < 2**128):
        parser.error("wall limit must be 30..3600 seconds; seed must be a nonnegative 128-bit integer")
    submission = arguments.submission.resolve(strict=True)
    output = arguments.output_dir.resolve()
    if not submission.is_dir() or not (submission / "solution.py").is_file():
        parser.error("submission must be a completed directory containing solution.py")
    for protected in (ROOT / "adversary", ROOT / "evaluator", ROOT.parent / "authoring"):
        if overlaps(submission, protected):
            parser.error("submission must be outside private authoring/evaluator/adversary directories; use champions or a dedicated /tmp snapshot")
    if overlaps(submission, ROOT / "participant") and submission != ROOT / "participant" / "baseline":
        parser.error("only the public baseline may be submitted from participant")
    if overlaps(output, submission) or any(overlaps(output, protected) for protected in (ROOT / "participant", ROOT / "evaluator", ROOT.parent / "authoring")):
        parser.error("private output must not overlap submission, participant, evaluator, or shared authoring")
    if output.exists():
        parser.error("output-dir must be new; refusing to overwrite private search data")
    command, helper_path = trusted_command(submission)
    hashes_before = submission_hashes(submission)
    seed = arguments.seed if arguments.seed is not None else secrets.randbits(128)
    points = generate_points(seed, arguments.episodes)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "seed": seed, "submission": str(submission),
                "submission_hashes": hashes_before, "episodes": arguments.episodes, "jobs": arguments.jobs,
                "repeat_worst": arguments.repeat_worst, "fresh_noise_repeats_per_selected_point": 3,
                "max_wall_seconds": arguments.max_wall_seconds, "fisher_enabled": arguments.fisher,
                "budget": CONFIG["budget"], "resources": CONFIG["resources"], "target_reference": CONFIG["target"],
                "family_counts": {family: sum(point["family"] == family for point in points) for family in CONFIG["suite"]["families"]},
                "trusted_source_sha256": {str(path): file_hash(path) for path in [Path(__file__).resolve(), helper_path,
                    ROOT / "participant/input/model.py", ROOT / "participant/input/runtime.py", ROOT / "participant/input/config.json"]},
                "warning": "Private generation-only selection, not an official score or automatic ratchet; never expose to a fresh agent"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "points.json").write_text(json.dumps(points, indent=2) + "\n")
    started = time.monotonic()
    screening = []
    repetitions = []
    selected = []
    termination_reason = "completed"
    context = multiprocessing.get_context("spawn")
    pool = context.Pool(arguments.jobs, initializer=initialize_worker, initargs=(command,))
    try:
        jobs = [make_job(point, "screening", point["screening_seed"]) for point in points]
        collect(pool, jobs, output / "screening.jsonl", screening, started + arguments.max_wall_seconds)
        eligible = [record for record in screening if not record["result"].get("infrastructure_error")]
        selected = sorted(eligible, key=lambda record: (-record["result"]["nrmse"], record["case_id"]))[:arguments.repeat_worst]
        points_by_id = {point["case_id"]: point for point in points}
        repeat_jobs = [make_job(points_by_id[record["case_id"]], "repeat", measurement_seed, repeat_index)
                       for record in selected for repeat_index, measurement_seed in enumerate(points_by_id[record["case_id"]]["repeat_seeds"])]
        collect(pool, repeat_jobs, output / "repeats.jsonl", repetitions, started + arguments.max_wall_seconds)
    except (SearchDeadline, KeyboardInterrupt) as error:
        termination_reason = type(error).__name__
    finally:
        pool.terminate()
        pool.join()
    hashes_unchanged = submission_hashes(submission) == hashes_before
    if not hashes_unchanged:
        termination_reason = "submission changed during search; do not use these results"
    summaries = []
    for record in selected:
        fisher = local_fisher(record["parameters"]) if arguments.fisher and time.monotonic() < started + arguments.max_wall_seconds else None
        repeats = sorted([item for item in repetitions if item["case_id"] == record["case_id"]], key=lambda item: item["repeat_index"])
        summaries.append(repeat_summary(record, repeats, fisher))
    report = {"completed": termination_reason == "completed", "termination_reason": termination_reason,
              "wall_seconds": time.monotonic() - started, "submission_unchanged": hashes_unchanged,
              "screening": summarize_screening(screening), "repeats": summarize_screening(repetitions),
              "selected_count": len(selected), "robust_cases": summaries, "robust_clusters": grouped_clusters(summaries),
              "interpretation": "Three fresh noise seeds exclude the selecting observation. Clusters are heuristic candidates, not proven failure mechanisms. The .09 diagnostic cutoff is not a new per-episode pass condition. Infrastructure failures are unscored. Local Fisher flags concern only the fixed reference design. Main must decide any ratchet after empirical review."}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("robust_cases", "robust_clusters")}, indent=2))
    return 0 if report["completed"] else 2


if __name__ == "__main__":
    sys.exit(main())
