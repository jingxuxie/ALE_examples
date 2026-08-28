import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rms(values):
    return math.hypot(*values) / math.sqrt(len(values))


def component_score(actual, expected, weak, floor, relative=0.01):
    scale = max(floor, relative * rms([value - baseline for value, baseline in zip(expected, weak)]))
    if actual is None or len(actual) != len(expected) or not all(finite_number(value) for value in actual):
        return {"score": 0.0, "rms_error": None, "max_error": None, "scale": scale, "status": "missing_or_invalid"}
    errors = [value - truth for value, truth in zip(actual, expected)]
    error = rms(errors)
    ratio = error / scale
    score = 0.0 if ratio > 1e150 else 1 / (1 + ratio * ratio)
    return {"score": score, "rms_error": error, "max_error": max(abs(value) for value in errors), "scale": scale, "status": "ok"}


def score_output(case, reference, weak, output):
    length = case["length"]
    energy = output.get("energy")
    gap = output.get("gap")
    components = {
        "energy_per_site": component_score([energy / length] if finite_number(energy) else None, [reference["energy"] / length], [weak["energy"] / length], 2e-5, 0.002),
        "gap": component_score([gap] if finite_number(gap) else None, [reference["gap"]], [weak["gap"]], 2e-3),
    }
    predicted = output.get("correlations")
    valid_vector = isinstance(predicted, list) and len(predicted) == len(case["observables"])
    kinds = sorted(set(observable["kind"] for observable in case["observables"]))
    for kind in kinds:
        indices = [index for index, observable in enumerate(case["observables"]) if observable["kind"] == kind]
        components[kind] = component_score([predicted[index] for index in indices] if valid_vector else None, [reference["correlations"][index] for index in indices], [weak["correlations"][index] for index in indices], 1.5e-3)
    score = 0.20 * components["energy_per_site"]["score"] + 0.30 * components["gap"]["score"]
    score += 0.50 * sum(components[kind]["score"] for kind in kinds) / len(kinds)
    return score, components


def locate_solver(submission):
    if submission.is_file():
        return submission
    for relative in ["solve.py", "workspace/solve.py"]:
        candidate = submission / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("submission must contain solve.py or workspace/solve.py")


def stage_submission(submission, solver, work):
    if submission.is_symlink():
        raise ValueError("submission symlinks are not allowed")
    source = submission if submission.is_dir() else submission.parent
    destination = work / "submission"

    def ignore_entries(directory, names):
        excluded = {".git", ".agents", ".codex"}.intersection(names)
        for name in names:
            if name not in excluded and (Path(directory) / name).is_symlink():
                raise ValueError(f"submission symlink is not allowed: {Path(directory) / name}")
        return excluded

    shutil.copytree(source, destination, symlinks=True, ignore=ignore_entries)
    for path in [destination, *destination.rglob("*")]:
        if path.is_symlink():
            raise ValueError(f"staged submission symlink is not allowed: {path}")
        permissions = stat.S_IMODE(path.stat().st_mode) | stat.S_IRUSR | stat.S_IWUSR
        if path.is_dir():
            permissions |= stat.S_IXUSR
        path.chmod(permissions)
    return destination / solver.relative_to(source)


def invoke(case, submission, solver, timeout):
    with tempfile.TemporaryDirectory(prefix="c03_mps_input_") as temporary:
        work = Path(temporary)
        staging_started = time.perf_counter()
        try:
            staged_solver = stage_submission(submission, solver, work)
        except (OSError, ValueError) as error:
            seconds = time.perf_counter() - staging_started
            return {}, {"status": "staging_error", "returncode": None, "seconds": seconds, "evaluator_wall_seconds": seconds, "max_rss_kib": None, "resource": {}, "stderr_tail": str(error)}
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(json.dumps(case, allow_nan=False) + "\n")
        launcher = "import os, sys; os.chdir(os.path.dirname(sys.argv[1])); os.execv(sys.executable, [sys.executable] + sys.argv[1:])"
        command = [sys.executable, "-c", launcher, str(staged_solver), "--input", str(input_path), "--output", str(output_path)]
        wrapper = os.environ.get("ALPS_EVAL_WRAPPER")
        if wrapper:
            wrapper = str(Path(wrapper).resolve())
            participant = Path(os.environ.get("ALPS_PARTICIPANT_DIR") or ROOT / "participant").resolve()
            command = [sys.executable, wrapper, "--participant", str(participant), "--submission", str(staged_solver), "--work", str(work), "--timeout", str(timeout), "--memory-mb", "8192", "--threads", "4", "--"] + command
        environment = {key: value for key, value in os.environ.items() if key in ["PATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH"]}
        environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "OPENBLAS_NUM_THREADS": "4", "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4", "NUMEXPR_NUM_THREADS": "4", "HOME": str(work), "TMPDIR": str(work)})
        started = time.perf_counter()
        output = {}
        status = "ok"
        returncode = None
        with (work / "stdout.txt").open("w") as stdout, (work / "stderr.txt").open("w") as stderr:
            try:
                completed = subprocess.run(command, cwd=staged_solver.parent, env=environment, stdout=stdout, stderr=stderr, timeout=timeout + (20 if wrapper else 0), check=False)
                returncode = completed.returncode
                if completed.returncode != 0:
                    status = "nonzero_exit"
                elif not output_path.is_file():
                    status = "missing_output"
                elif output_path.stat().st_size > 1_000_000:
                    status = "oversized_output"
                else:
                    try:
                        output = json.loads(output_path.read_text())
                        if not isinstance(output, dict):
                            output = {}
                            status = "invalid_json_object"
                    except (ValueError, OSError):
                        status = "invalid_json"
            except subprocess.TimeoutExpired:
                status = "timeout"
        seconds = time.perf_counter() - started
        resources = {}
        resource_path = work / "_resource.json"
        if resource_path.is_file():
            try:
                resources = json.loads(resource_path.read_text())
            except (ValueError, OSError):
                resources = {}
        if resources.get("timed_out"):
            status = "timeout"
        stderr_path = work / "stderr.txt"
        with stderr_path.open("rb") as handle:
            handle.seek(max(0, stderr_path.stat().st_size - 3000))
            error_tail = handle.read().decode(errors="replace")
        return output if status == "ok" else {}, {"status": status, "returncode": returncode, "seconds": resources.get("seconds", seconds), "evaluator_wall_seconds": seconds, "max_rss_kib": resources.get("max_rss_kib"), "resource": resources, "stderr_tail": error_tail}


def evaluate(submission, split, timeout=None, jobs=1):
    if jobs < 1:
        raise ValueError("jobs must be at least 1")
    manifest = json.loads((PRIVATE / "challenge_pool" / "manifest.json").read_text())
    if split not in manifest["splits"]:
        raise ValueError(f"unknown manifest split: {split}")
    entries = manifest["splits"][split]
    loaded = []
    small_validation = PRIVATE / "reference" / "validation" / "small_exact.json"
    if not small_validation.exists() or not json.loads(small_validation.read_text()).get("passed"):
        raise RuntimeError("author reference validation is not ready: small exact checks missing or failed")
    for entry in entries:
        case = json.loads((PRIVATE / entry["input"]).read_text())
        artifact = json.loads((PRIVATE / entry["reference"]).read_text())
        if not artifact.get("ready"):
            raise RuntimeError(f"author reference is not ready: {entry['id']}")
        digest = hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()
        if artifact.get("input_sha256") != digest:
            raise RuntimeError(f"author reference input mismatch: {entry['id']}")
        loaded.append((entry, case, artifact))
    solver = locate_solver(submission)

    def evaluate_case(item):
        entry, case, artifact = item
        output, execution = invoke(case, submission, solver, timeout or manifest["timeout_seconds"])
        score, components = score_output(case, artifact["reference"], artifact["weak"], output)
        weak_score, _ = score_output(case, artifact["reference"], artifact["weak"], artifact["weak"])
        return {"id": entry["id"], "family": case["family"], "score": score, "weak_score": weak_score, "components": components, "execution": execution}

    records = []
    families = {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for record in executor.map(evaluate_case, loaded):
            records.append(record)
            families.setdefault(record["family"], []).append(record["score"])
            execution = record["execution"]
            print(json.dumps({"case": record["id"], "score": record["score"], "status": execution["status"], "seconds": execution["seconds"]}), flush=True)
    family_report = {family: {"score": sum(scores) / len(scores), "worst_case_score": min(scores), "cases": len(scores)} for family, scores in families.items()}
    return {
        "split": split, "reference_ready": True, "jobs": jobs,
        "mean_core_score": sum(record["score"] for record in records) / len(records),
        "worst_family_score": min(value["score"] for value in family_report.values()),
        "families": family_report, "cases": records,
        "total_seconds": sum(record["execution"]["seconds"] for record in records),
        "wall_seconds": time.perf_counter() - started,
        "score_note": "mean_core_score is the mean on the requested split; runtime is not scored below the declared cutoff",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    try:
        result = evaluate(Path(args.submission).absolute(), args.split, jobs=args.jobs)
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        write_json(Path(args.report), {"split": args.split, "reference_ready": False, "author_error": str(error)})
        raise SystemExit(2)
    write_json(Path(args.report), result)


if __name__ == "__main__":
    main()
