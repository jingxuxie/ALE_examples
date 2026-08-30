from common import ROOT, CONCEPT, LimitedSandbox, checked_field, energy_gradient, lower_bound, read_case, scratch_usage, write_json

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import signal
import tempfile
import time

import numpy as np

from evaluate import invalid_case, score_field


FOCUS = ROOT / "focused_proposal"
SELECTED = ("nf01", "nf02", "nf04")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze():
    if (FOCUS / "manifest.json").exists():
        raise RuntimeError("focused proposal already frozen")
    previous = read_case(ROOT / "proposal/manifest.json")
    for relative, expected in previous["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("prior proposal modified: " + relative)
    for name in ("cases", "baseline_fields", "witness_fields"):
        (FOCUS / name).mkdir(parents=True, exist_ok=True)
    target = read_case(ROOT / "proposal/target.json")
    target.update({
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(SELECTED),
        "families": ["collective_fluxoid"],
        "family_cardinality": {"collective_fluxoid": len(SELECTED)},
        "family_definitions": {
            "collective_fluxoid": "Connected narrow-bridge arrays of 48, 49, or 64 near-half-flux perforations with physical hole solenoids; weak flux/material perturbations and staggered geometry test collective winding order rather than raw grid scale."
        },
        "single_family_note": "Core and worst-family scores coincide. The unchanged 0.65 core threshold is binding; 0.45 worst-family remains explicit.",
    })
    write_json(FOCUS / "target.json", target)
    records = []
    for reference in previous["cases"]:
        if reference["case_id"] not in SELECTED:
            continue
        reference = dict(reference)
        reference["family"] = "collective_fluxoid"
        for key in ("case_path", "baseline_path", "witness_path"):
            source = ROOT / reference[key]
            destination = FOCUS / source.parent.name / source.name
            shutil.copyfile(source, destination)
            reference[key] = str(destination.relative_to(ROOT))
        records.append(reference)
    manifest = {
        "schema_version": 1,
        "status": "frozen_focused_proposal_pending_main_approval",
        "approval_required": True,
        "frozen_at": target["frozen_at"],
        "case_count": len(records),
        "source_cases_searched": previous["source_cases_searched"],
        "fresh_sessions_launched": 0,
        "champion_sha256": previous["champion_sha256"],
        "reference_kind": previous["reference_kind"],
        "baseline_repeatability": previous["baseline_repeatability"],
        "revision_reason": "User permits one genuine family rather than manufactured diversity. Select the three strongest collective-loop gaps before sequential unchanged-champion repeats and before any fresh launch. Baselines, witnesses, input bytes, quality thresholds and resource limits are unchanged from the prior proposal.",
        "supersedes": "proposal/manifest.json",
        "prior_manifest_sha256": digest(ROOT / "proposal/manifest.json"),
        "cases": records,
        "sha256": {str(path.relative_to(ROOT)): digest(path) for path in sorted(FOCUS.rglob("*")) if path.is_file()},
    }
    write_json(FOCUS / "manifest.json", manifest)
    return load()


def load():
    manifest = read_case(FOCUS / "manifest.json")
    target = read_case(FOCUS / "target.json")
    references = manifest["cases"]
    if len(references) != target["case_count"] or len({reference["case_id"] for reference in references}) != len(references):
        raise ValueError("invalid frozen case cardinality")
    counts = {family: sum(reference["family"] == family for reference in references) for family in target["families"]}
    if counts != target["family_cardinality"] or sum(counts.values()) != len(references):
        raise ValueError("invalid frozen family cardinality")
    for relative, expected in manifest["sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("focused proposal modified: " + relative)
    for reference in manifest["cases"]:
        case = read_case(ROOT / reference["case_path"])
        baseline = None
        for kind in ("baseline", "witness"):
            field = checked_field(ROOT / reference[kind + "_path"], case, target["result_max_bytes"])
            energy, unused, rms = energy_gradient(case, field)
            if abs(energy - reference[kind + "_energy"]) > 1e-9:
                raise ValueError("reference energy mismatch")
            if rms > target["stationarity_rms_max"] or energy < lower_bound(case) - 1e-8:
                raise ValueError("invalid stationary reference")
            if kind == "baseline":
                baseline = field
        initial = np.asarray(case["initial_real"]) + 1j * np.asarray(case["initial_imag"])
        if not np.array_equal(initial, baseline):
            raise ValueError("provided initial state differs from frozen baseline")
        if reference["baseline_energy"] - reference["witness_energy"] < target["minimum_reference_gap"]:
            raise ValueError("reference gap too small")
    return manifest, target


def aggregate(records, target):
    if len(records) != target["case_count"] or len({record["case_id"] for record in records}) != len(records):
        raise ValueError("all unique cases must contribute")
    if set(record["family"] for record in records) != set(target["families"]):
        raise ValueError("unexpected families")
    families = {}
    for family in target["families"]:
        members = [record["case_score"] for record in records if record["family"] == family]
        if len(members) != target["family_cardinality"][family]:
            raise ValueError("family cardinality mismatch")
        families[family] = float(np.mean(members))
    core = float(np.mean(list(families.values())))
    worst = min(families, key=families.get)
    reasons = [record["case_id"] + ": " + record["reason"] for record in records if not record["valid"]]
    if core < target["core_min"]:
        reasons.append("core_score below " + str(target["core_min"]))
    if families[worst] < target["worst_family_min"]:
        reasons.append("worst_family_score below " + str(target["worst_family_min"]))
    return {
        "verification_mode": target["verification_mode"],
        "valid": all(record["valid"] for record in records),
        "status": "failed" if reasons else "passed",
        "core_score": core,
        "worst_family": worst,
        "worst_family_score": families[worst],
        "family_scores": families,
        "runtime_score": float(np.mean([record["runtime_score"] for record in records])),
        "passed": not reasons,
        "reason": "; ".join(reasons) if reasons else "all frozen energy, stationarity, and resource goals met",
        "cases": records,
    }


def cpu_counters():
    counters = {}
    for line in Path("/proc/stat").read_text().splitlines():
        fields = line.split()
        if fields and fields[0].startswith("cpu") and fields[0][3:].isdigit():
            values = [int(value) for value in fields[1:9]]
            counters[int(fields[0][3:])] = (sum(values), values[3] + values[4])
    return counters


def utilization(before, after, core):
    total = after[core][0] - before[core][0]
    idle = after[core][1] - before[core][1]
    return float((total - idle) / total) if total > 0 else 0.0


def siblings(core):
    path = Path("/sys/devices/system/cpu") / ("cpu" + str(core)) / "topology/thread_siblings_list"
    if not path.exists():
        return [core]
    result = []
    for part in path.read_text().strip().split(","):
        endpoints = [int(value) for value in part.split("-")]
        result.extend(range(endpoints[0], endpoints[-1] + 1))
    return result


def idle_core():
    allowed = sorted(os.sched_getaffinity(0))
    before = cpu_counters()
    time.sleep(1)
    after = cpu_counters()
    rates = {core: utilization(before, after, core) for core in after}
    chosen = min(allowed, key=lambda core: (max(rates.get(other, 1) for other in siblings(core)), rates[core], core))
    return chosen, {str(other): rates[other] for other in siblings(chosen)}, after


class IdleSandbox(LimitedSandbox):
    selected_core = None

    def command(self, arguments):
        command = super().command(arguments)
        position = command.index("--chdir")
        command[position:position] = ["--ro-bind", str(ROOT / "cpu_monitor"), "/trusted_cpu", "--cap-drop", "ALL"]
        return command

    def limits(self):
        super().limits()
        os.sched_setaffinity(0, {self.selected_core})


def run_case(reference, target, submission, directory):
    case = read_case(ROOT / reference["case_path"])
    destination = directory / reference["case_id"]
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "record.json").exists():
        raise RuntimeError("refusing to replace an existing repeat")
    selected, before_load, counters = idle_core()
    accounting = {"selected_cpu": selected, "pre_run_cpu_busy_fraction": before_load}
    reason = None
    usage = None
    with tempfile.TemporaryDirectory(prefix="focused-public-", dir=ROOT / "scratch") as temporary:
        staging = Path(temporary)
        shutil.copyfile(ROOT / reference["case_path"], staging / "case.json")
        with IdleSandbox(CONCEPT / "participant", submission, input_dir=staging, seconds=int(target["cpu_seconds_per_case"]), memory_gib=2) as sandbox:
            sandbox.selected_core = selected
            log_path = destination / "trusted_accounting.json"
            with log_path.open("wb") as log:
                started = time.monotonic()
                process = sandbox.start(["/usr/bin/python3", "/trusted_cpu/run.py"], stdout=log, stderr=log)
                while True:
                    waited, status, usage = os.wait4(process.pid, os.WNOHANG)
                    if waited:
                        process.returncode = os.waitstatus_to_exitcode(status)
                        break
                    if time.monotonic() - started > target["wall_seconds_per_case"]:
                        reason = "wall deadline exceeded"
                    try:
                        if scratch_usage(sandbox.output) + log_path.stat().st_size > target["scratch_mib"] * 1024**2:
                            reason = "scratch/log byte limit exceeded"
                    except ValueError as error:
                        reason = str(error)
                    if reason:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        waited, status, usage = os.wait4(process.pid, 0)
                        process.returncode = os.waitstatus_to_exitcode(status)
                        break
                    time.sleep(0.02)
                elapsed = time.monotonic() - started
                sandbox.stop()
            outer_cpu = usage.ru_utime + usage.ru_stime
            payload = {}
            if process.returncode == 0 and reason is None:
                try:
                    payload = read_case(log_path)
                    if payload["schema_version"] != 1 or payload["returncode"] != 0:
                        raise ValueError("unexpected accounting protocol")
                except Exception as error:
                    reason = "trusted accounting unavailable: " + str(error)[:200]
            cpu_seconds = payload.get("cpu_seconds", 0.0) + payload.get("monitor_cpu_seconds", 0.0) + outer_cpu
            if (sandbox.output / "solver.log").exists():
                shutil.copyfile(sandbox.output / "solver.log", destination / "solver.log")
            after = cpu_counters()
            accounting.update({
                "wall_seconds": elapsed,
                "cpu_seconds": cpu_seconds,
                "cpu_user_seconds": payload.get("cpu_user_seconds"),
                "cpu_system_seconds": payload.get("cpu_system_seconds"),
                "outer_bubblewrap_cpu_seconds": outer_cpu,
                "monitor_cpu_seconds": payload.get("monitor_cpu_seconds"),
                "cpu_to_wall_ratio": cpu_seconds / elapsed,
                "maximum_rss_kib": payload.get("maximum_rss_kib"),
                "during_run_cpu_busy_fraction": {str(other): utilization(counters, after, other) for other in siblings(selected)},
                "returncode": process.returncode,
                "timing_source": "read-only non-dumpable trusted parent inside namespace collects solver wait4 rusage; parent stdout descriptor never inherited by solver; outer Bubblewrap CPU added separately",
                "cpu_monitor_sha256": digest(ROOT / "cpu_monitor/run.py"),
            })
            if process.returncode != 0:
                reason = reason or ("nonzero exit: " + str(process.returncode))
            if cpu_seconds > target["cpu_seconds_per_case"]:
                reason = "trusted CPU deadline exceeded"
            try:
                if scratch_usage(sandbox.output) + log_path.stat().st_size > target["scratch_mib"] * 1024**2:
                    reason = "scratch/log byte limit exceeded"
                if reason:
                    record = invalid_case(reference, reason, elapsed)
                else:
                    field = checked_field(sandbox.output / "result.npz", case, target["result_max_bytes"])
                    np.savez_compressed(destination / "field.npz", psi=field)
                    record = score_field(reference, case, field, elapsed, target)
            except Exception as error:
                record = invalid_case(reference, "invalid output: " + str(error)[:300], elapsed)
    record["resource_accounting"] = accounting
    record["input_sha256"] = digest(ROOT / reference["case_path"])
    write_json(destination / "record.json", record)
    print({key: record.get(key) for key in ("case_id", "valid", "checked_energy", "case_score", "wall_seconds")}, "cpu", cpu_seconds, flush=True)
    return record


def execute(submission, label, repeats):
    manifest, target = load()
    if not label or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in label):
        raise ValueError("label must contain only letters, digits, underscores or hyphens")
    if repeats < 1:
        raise ValueError("at least one repeat is required")
    submission = submission.resolve()
    sources = {path.name: digest(path) for path in sorted(submission.glob("*.py"))}
    for repeat in range(1, repeats + 1):
        directory = ROOT / "runs" / (label + "_" + str(repeat))
        directory.mkdir(exist_ok=True)
        records = [run_case(reference, target, submission, directory) for reference in manifest["cases"]]
        report = aggregate(records, target)
        report.update({"submission": str(submission), "source_sha256": sources, "proposal_manifest_sha256": digest(FOCUS / "manifest.json"), "repeat": repeat})
        write_json(directory / "score.json", report)
        print({key: report[key] for key in ("valid", "status", "core_score", "worst_family_score", "runtime_score")}, flush=True)


def rescore(label):
    manifest, target = load()
    source = ROOT / "runs" / label
    original = read_case(source / "score.json")
    by_name = {record["case_id"]: record for record in original["cases"]}
    records = []
    for reference in manifest["cases"]:
        case = read_case(ROOT / reference["case_path"])
        if digest(ROOT / reference["case_path"]) != digest(ROOT / "proposal/cases" / (reference["case_id"] + ".json")):
            raise ValueError("qualification input bytes differ")
        previous = by_name[reference["case_id"]]
        if not previous["valid"]:
            raise ValueError("prior run invalid")
        field = checked_field(source / reference["case_id"] / "field.npz", case, target["result_max_bytes"])
        records.append(score_field(reference, case, field, previous["wall_seconds"], target))
    report = aggregate(records, target)
    report.update({"source_report": str((source / "score.json").relative_to(ROOT)), "source_report_sha256": digest(source / "score.json"), "source_sha256": original["source_sha256"], "qualification": "Independent recheck of same-budget executable outputs on byte-identical focused inputs; no additional run or private field lookup.", "proposal_manifest_sha256": digest(FOCUS / "manifest.json")})
    write_json(FOCUS / "qualified_challenger_score.json", report)
    print({key: report[key] for key in ("valid", "status", "core_score", "worst_family_score", "runtime_score")})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "run", "rescore", "validate"))
    parser.add_argument("--submission", type=Path, default=ROOT / "baseline")
    parser.add_argument("--label", default="focused_champion_repeat")
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze()
    elif args.action == "run":
        execute(args.submission, args.label, args.repeats)
    elif args.action == "rescore":
        rescore(args.label)
    else:
        manifest, target = load()
        print("valid frozen proposal", target["case_count"], "cases")


if __name__ == "__main__":
    main()
