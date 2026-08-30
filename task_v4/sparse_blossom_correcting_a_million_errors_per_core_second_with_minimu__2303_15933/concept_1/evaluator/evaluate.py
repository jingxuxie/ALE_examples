import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PARTICIPANT = ROOT / "participant"
sys.path.insert(0, str(PARTICIPANT / "input/runtime"))

import numpy as np
from scipy.stats import binomtest


def paired_report(baseline_wrong, candidate_wrong):
    baseline_wrong = np.asarray(baseline_wrong, dtype=bool)
    candidate_wrong = np.asarray(candidate_wrong, dtype=bool)
    shots = len(baseline_wrong)
    baseline_count = int(baseline_wrong.sum())
    candidate_count = int(candidate_wrong.sum())
    corrected = int((baseline_wrong & ~candidate_wrong).sum())
    spoiled = int((~baseline_wrong & candidate_wrong).sum())
    differences = baseline_wrong.astype(float) - candidate_wrong.astype(float)
    improvement = float(differences.mean())
    standard_error = float(differences.std(ddof=1) / math.sqrt(shots))
    baseline_rate = baseline_count / shots
    candidate_rate = candidate_count / shots
    relative = 1 - candidate_count / baseline_count if baseline_count else None
    relative_interval = None
    if baseline_count:
        influence = candidate_rate / baseline_rate ** 2 * (baseline_wrong - baseline_rate) - (candidate_wrong - candidate_rate) / baseline_rate
        relative_error = float(influence.std(ddof=1) / math.sqrt(shots))
        relative_interval = [relative - 1.96 * relative_error, relative + 1.96 * relative_error]
    return dict(shots=shots, baseline_failures=baseline_count, candidate_failures=candidate_count,
                baseline_rate=baseline_rate, candidate_rate=candidate_rate, corrected=corrected, spoiled=spoiled,
                error_reduction=relative, paired_absolute_improvement=improvement,
                paired_absolute_ci95=[improvement - 1.96 * standard_error, improvement + 1.96 * standard_error],
                paired_relative_ci95=relative_interval,
                discordant_binomial_p=float(binomtest(corrected, corrected + spoiled, 0.5, alternative="greater").pvalue) if corrected + spoiled else 1.0)


def verify_freeze():
    frozen = json.loads((ROOT / "evaluator/hidden/frozen.json").read_text())
    for entry in frozen["artifacts"]:
        path = ROOT / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError("Frozen artifact changed: " + entry["path"])
    return frozen


def snapshot_submission(submission, destination):
    source = submission.resolve().parent
    for private in [ROOT / "hidden", ROOT / "evaluator"]:
        if source == private or source in private.parents or private in source.parents:
            raise ValueError("Submission directory overlaps privileged assets")
    if source in [ROOT / "attempts", ROOT / "champions", ROOT / "adversary"]:
        raise ValueError("Use an isolated candidate subdirectory, not a privileged collection root")
    total = 0
    count = 0
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Submission symlinks are forbidden")
        if path.is_file():
            total += path.stat().st_size
            count += 1
    if total > 256 * 1024 ** 2 or count > 4096:
        raise ValueError("Submission directory exceeds artifact limit")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))


def sandbox_command(participant, submission, request, output):
    command = ["/usr/bin/bwrap", "--unshare-user", "--unshare-pid", "--unshare-net", "--unshare-ipc", "--unshare-uts",
               "--die-with-parent", "--as-pid-1", "--new-session", "--cap-drop", "ALL", "--clearenv"]
    for path in ["/usr", "/lib", "/lib64", "/bin", "/etc"]:
        if Path(path).exists():
            command += ["--ro-bind", path, path]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--ro-bind", str(participant), "/participant", "--ro-bind", str(submission), "/submission",
                "--ro-bind", str(request), "/request", "--bind", str(output), "/out", "--chdir", "/submission"]
    environment = dict(PATH="/usr/bin:/bin", HOME="/tmp", TMPDIR="/tmp", MPLCONFIGDIR="/tmp/matplotlib",
                       PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                       MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
    for name, value in environment.items():
        command += ["--setenv", name, value]
    command += ["/usr/bin/python3", "-I", "/participant/input/worker.py", "/request/request.json", "/out/response.json"]
    return command


def export_process_filter(output):
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_rule_add.restype = ctypes.c_int
    library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.seccomp_export_bpf.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("seccomp_init failed")
    try:
        for name in [b"clone", b"clone3", b"fork", b"vfork", b"ptrace", b"process_vm_readv", b"process_vm_writev"]:
            syscall = library.seccomp_syscall_resolve_name(name)
            if syscall >= 0 and library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, syscall, 0):
                raise RuntimeError("seccomp_rule_add failed")
        if library.seccomp_export_bpf(context, output.fileno()):
            raise RuntimeError("seccomp_export_bpf failed")
        output.seek(0)
    finally:
        library.seccomp_release(context)


def run_isolated(command, log_path, wall_limit):
    started = time.monotonic()
    timed_out = False
    with log_path.open("wb") as log, tempfile.TemporaryFile() as process_filter:
        export_process_filter(process_filter)
        command = command[:1] + ["--seccomp", str(process_filter.fileno())] + command[1:]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   close_fds=True, pass_fds=(process_filter.fileno(),), start_new_session=True)
        while True:
            waited, status, usage = os.wait4(process.pid, os.WNOHANG)
            if waited:
                break
            if time.monotonic() - started > wall_limit:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                waited, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(0.05)
        process.returncode = os.waitstatus_to_exitcode(status)
    return dict(returncode=process.returncode, wall_seconds=time.monotonic() - started,
                cpu_seconds=usage.ru_utime + usage.ru_stime, max_rss_kib=usage.ru_maxrss,
                watchdog_timeout=timed_out, cpu_accounting="trusted wait4 with bwrap --as-pid-1; process/thread creation blocked by seccomp")


def read_predictions(path, shots):
    if path.is_symlink() or path.stat().st_size > 8 * 1024 ** 2:
        raise ValueError("invalid prediction artifact")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != 1 or infos[0].filename != "predictions.npy" or infos[0].file_size > shots * 4 * 8 + 8192:
            raise ValueError("invalid or oversized prediction archive")
    with np.load(path, allow_pickle=False) as data:
        predictions = data["predictions"]
    if predictions.shape != (shots, 4) or predictions.dtype.kind not in "biu" or not np.isin(predictions, [0, 1]).all():
        raise ValueError("invalid predictions")
    return predictions


def evaluate(submission, split):
    frozen = verify_freeze()
    limits = frozen["limits"]
    selected_splits = ["challenge", "holdout"] if split == "both" else [split]
    with tempfile.TemporaryDirectory(prefix="logical-decoder-") as temporary:
        temporary = Path(temporary)
        request_dir, output_dir = temporary / "request", temporary / "out"
        request_dir.mkdir()
        output_dir.mkdir()
        snapshot_submission(submission, temporary / "submission")
        records = []
        items = []
        for case in frozen["cases"]:
            case_id = case["case_id"]
            syndromes = []
            for current_split in selected_splits:
                with np.load(ROOT / "evaluator/hidden" / current_split / (case_id + ".npz"), allow_pickle=False) as data:
                    syndromes.append(data["syndromes"])
            np.savez_compressed(request_dir / (case_id + ".npz"), syndromes=np.concatenate(syndromes))
            items.append(dict(case_id=case_id, syndromes=f"/request/{case_id}.npz", predictions=f"/out/{case_id}.npz"))
        request = dict(submission="/submission/" + submission.name, participant_root="/participant", items=items, limits=limits)
        (request_dir / "request.json").write_text(json.dumps(request))
        command = sandbox_command(PARTICIPANT, temporary / "submission", request_dir, output_dir)
        execution = run_isolated(command, temporary / "worker.log", limits["wall_watchdog_seconds"])
        if execution["returncode"] or execution["watchdog_timeout"]:
            return dict(valid=False, passed=False, core_score=None, worst_family_score=None, runtime_score=0, resource_score=0,
                        reason="Isolated worker failed; no unsandboxed fallback", execution=execution, error="Isolated worker failed; no unsandboxed fallback",
                        worker_log=(temporary / "worker.log").read_text(errors="replace")[-12000:])
        for case in frozen["cases"]:
            case_id = case["case_id"]
            shots = frozen["shots_per_case_per_split"]
            predictions = read_predictions(output_dir / (case_id + ".npz"), shots * len(selected_splits))
            for index, current_split in enumerate(selected_splits):
                with np.load(ROOT / "evaluator/hidden" / current_split / (case_id + ".npz"), allow_pickle=False) as data:
                    labels, baseline = data["labels"], data["baseline"]
                candidate = predictions[index * shots:(index + 1) * shots]
                records.append(dict(case_id=case_id, family=case["family"], split=current_split,
                                    baseline_wrong=np.any(baseline != labels, axis=1), candidate_wrong=np.any(candidate != labels, axis=1)))

        def combine(entries):
            return paired_report(np.concatenate([entry["baseline_wrong"] for entry in entries]),
                                 np.concatenate([entry["candidate_wrong"] for entry in entries]))

        pooled = combine(records)
        families = {family: combine([entry for entry in records if entry["family"] == family]) for family in sorted({entry["family"] for entry in records})}
        splits = {current_split: combine([entry for entry in records if entry["split"] == current_split]) for current_split in selected_splits}
        gates = dict(pooled_improvement=pooled["error_reduction"] >= frozen["targets"]["pooled_error_reduction"],
                     independent_holdout="holdout" in splits and splits["holdout"]["error_reduction"] >= frozen["targets"]["holdout_error_reduction"],
                     family_nonregression=all(entry["candidate_failures"] <= frozen["targets"]["max_family_failure_ratio"] * entry["baseline_failures"] for entry in families.values()),
                     paired_confidence=pooled["paired_absolute_ci95"][0] > 0,
                     runtime=execution["cpu_seconds"] <= limits["cpu_seconds"] and not execution["watchdog_timeout"],
                     final_suite=split == "both")
        passed = all(gates.values())
        runtime_score = min(1.0, limits["cpu_seconds"] / max(execution["cpu_seconds"], 1e-9))
        return dict(valid=True, passed=passed, score=100 * pooled["error_reduction"], core_score=pooled["error_reduction"],
                    worst_family_score=min(entry["error_reduction"] for entry in families.values()),
                    runtime_score=runtime_score, resource_score=runtime_score,
                    reason="All frozen gates passed" if passed else "Failed gates: " + ", ".join(name for name, value in gates.items() if not value), gates=gates,
                    split=split, pooled=pooled, families=families, splits=splits, execution=execution,
                    cases=[dict(case_id=entry["case_id"], split=entry["split"], **paired_report(entry["baseline_wrong"], entry["candidate_wrong"])) for entry in records],
                    freeze_sha256=hashlib.sha256((ROOT / "evaluator/hidden/frozen.json").read_bytes()).hexdigest(),
                    uncertainty="Paired normal/delta-method 95% intervals; exact one-sided discordant-pair binomial test. No correction for adaptive reuse.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--split", choices=["challenge", "holdout", "both"], default="both")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(args.submission.resolve(), args.split)
    except Exception as error:
        report = dict(valid=False, passed=False, core_score=None, worst_family_score=None, runtime_score=0, resource_score=0,
                      reason=f"{type(error).__name__}: {error}", error=f"{type(error).__name__}: {error}")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report.get("valid") else 2


if __name__ == "__main__":
    raise SystemExit(main())
