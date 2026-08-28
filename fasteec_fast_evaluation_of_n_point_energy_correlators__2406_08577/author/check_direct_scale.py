"""Bounded source-contribution scale evidence, never a submitted-solution score."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time
import traceback


ROOT = Path(__file__).resolve().parent.parent
MEMORY_BYTES = 3 * 1024 ** 3
ORDER = 7
KAPPA = 1.0
LOG_MIN = -4.0
BINS = 48


def write_json(path, contents):
    path.write_text(json.dumps(contents, indent=2, sort_keys=True, allow_nan=False) + "\n")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_largest_jet(dataset, artifacts):
    started = time.monotonic()
    cpu_started = time.process_time()
    initial_stat = dataset.stat()
    digest = hashlib.sha256()
    current_id = None
    current_rows = []
    largest_rows = []
    largest_id = None
    event_count = 0
    row_count = 0
    byte_count = 0
    ties = 0

    def consider(event_id, rows):
        nonlocal largest_rows, largest_id, event_count, ties
        if not rows:
            return
        event_count += 1
        if len(rows) > len(largest_rows):
            largest_rows = list(rows)
            largest_id = event_id
            ties = 1
        elif len(rows) == len(largest_rows):
            ties += 1

    with dataset.open("rb") as stream:
        for raw_line in stream:
            digest.update(raw_line)
            byte_count += len(raw_line)
            fields = raw_line.split()
            if not fields:
                continue
            if len(fields) != 4:
                raise ValueError("CMS input row must contain event_id, pt, rapidity, phi")
            event_id = int(fields[0])
            if event_id != current_id:
                if current_id is not None and event_id <= current_id:
                    raise ValueError("CMS event IDs are not ordered and contiguous by jet")
                consider(current_id, current_rows)
                current_id, current_rows = event_id, []
            current_rows.append(raw_line)
            row_count += 1
    consider(current_id, current_rows)
    final_stat = dataset.stat()
    if not largest_rows or (initial_stat.st_size, initial_stat.st_mtime_ns) != (
            final_stat.st_size, final_stat.st_mtime_ns) or byte_count != initial_stat.st_size:
        raise ValueError("dataset was empty, incomplete, or changed during selection")
    selected = artifacts / "largest_jet.txt"
    original = artifacts / "largest_jet_original_ids.txt"
    original.write_bytes(b"".join(largest_rows))
    selected.write_bytes(b"".join(b"0 " + b" ".join(row.split()[1:]) + b"\n"
                                  for row in largest_rows))
    particles = [tuple(map(float, row.split()[1:])) for row in largest_rows]
    if not all(particle[0] > 0 and all(math.isfinite(value) for value in particle)
               for particle in particles):
        raise ValueError("selected jet has invalid constituent kinematics")
    selection = {
        "method": "Full streaming scan; first jet attaining the maximum constituent count",
        "source_original_event_id": largest_id, "events_scanned": event_count,
        "constituent_rows_scanned": row_count, "bytes_scanned": byte_count,
        "max_constituents": len(largest_rows), "max_multiplicity_ties": ties,
        "source_data_sha256": digest.hexdigest(),
        "selected_input_sha256": file_hash(selected),
        "selected_original_rows_sha256": file_hash(original),
        "selected_constituent_count": len(particles),
        "constituents_removed": 0,
        "input_transformation": "Only event ID is remapped to zero and whitespace normalized; all pt, rapidity, phi tokens and constituent order are retained",
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "timing_scope": "Full data scan, selection, SHA-256, and selected-input serialization; excluded from process/loop timings",
    }
    write_json(artifacts / "selection.json", selection)
    return selected, particles, selection


def bounded_run(command, directory, wall_limit, cpu_limit):
    directory.mkdir(parents=True, exist_ok=True)
    stdout_path = directory / "stdout.txt"
    stderr_path = directory / "stderr.txt"
    cpu_soft = max(1, math.ceil(cpu_limit))
    cpu_hard = cpu_soft + 1
    grace_seconds = 0.75

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_soft, cpu_hard))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    started = time.monotonic()
    termination = None
    timeout_trigger = None
    kill_sent = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(list(map(str, command)), cwd=directory, stdout=stdout,
                                   stderr=stderr, preexec_fn=limits, start_new_session=True)
        try:
            while True:
                waited, status, usage = os.wait4(process.pid, os.WNOHANG)
                if waited:
                    process.returncode = os.waitstatus_to_exitcode(status)
                    break
                now = time.monotonic()
                if termination is None and now - started >= wall_limit:
                    timeout_trigger = "wall_limit"
                    termination = now
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                elif termination is not None and now - termination >= grace_seconds and not kill_sent:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    kill_sent = True
                time.sleep(0.005)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            unused, status, unused_usage = os.wait4(process.pid, 0)
            process.returncode = os.waitstatus_to_exitcode(status)
            raise
    elapsed = time.monotonic() - started
    if timeout_trigger is None and process.returncode in (124, -signal.SIGXCPU):
        timeout_trigger = "cpu_limit_or_cooperative_interrupt"
    result = {
        "command": list(map(str, command)), "returncode": process.returncode,
        "outcome": "timeout" if timeout_trigger else "completed" if process.returncode == 0 else "process_error",
        "timeout_trigger": timeout_trigger, "kill_after_grace": kill_sent,
        "wall_seconds": elapsed, "cpu_user_seconds": usage.ru_utime,
        "cpu_system_seconds": usage.ru_stime, "cpu_seconds": usage.ru_utime + usage.ru_stime,
        "peak_rss_kib": usage.ru_maxrss,
        "limits": {"wall_seconds": wall_limit, "cpu_soft_seconds": cpu_soft,
                   "cpu_hard_seconds": cpu_hard, "address_space_bytes": MEMORY_BYTES,
                   "termination_grace_seconds": grace_seconds},
        "timing_scope": "Measured launch-to-reap wall time and wait4 child CPU usage; includes startup, parsing, setup, loop, and output. Not extrapolated.",
        "stdout": str(stdout_path), "stderr": str(stderr_path),
    }
    write_json(directory / "process.json", result)
    return result


def pair_oracle(particles):
    scalar = math.fsum(particle[0] for particle in particles)
    terms = [[] for unused in range(BINS)]
    for first in particles:
        for second in particles:
            distance = math.hypot(first[1] - second[1],
                                  math.remainder(first[2] - second[2], math.tau))
            position = (0 if distance <= 10 ** LOG_MIN else min(BINS - 1, max(0, math.floor(
                (math.log10(distance) - LOG_MIN) * BINS / -LOG_MIN))))
            terms[position].append((first[0] / scalar) * (second[0] / scalar))
    return list(map(math.fsum, terms))


def run_evidence(root, seconds, report):
    author = root / "author"
    artifacts = author / "direct_scale"
    artifacts.mkdir(exist_ok=True)
    checks = report["integrity_checks"]
    cpp_source = author / "direct_baseline.cpp"
    dataset = author / "cms100k.txt"
    official = author / "bin" / "eec_fast"
    monitored = [cpp_source, author / "check_direct_scale.py", official,
                 author / "FastEEC" / "eec_fast.cc", author / "FastEEC" / "eec_compute.h",
                 author / "FastEEC" / "read_events.h", author / "fastjet" / "lib" / "libfastjet.a"]
    monitored += [path for path in (author / "reference_source" / "eec_fast.cc",
                                   author / "reference_source" / "eec_compute.h",
                                   author / "reference_source" / "read_events.h",
                                   author / "validate_projectors.py", author / "projector_validation.json")
                  if path.exists()]
    initial_hashes = {str(path.relative_to(root)): file_hash(path) for path in monitored}
    report["source_hashes_before"] = initial_hashes
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("g++ is required")
    executable = artifacts / "direct_baseline"
    print("Compiling exact multiset baseline; scanning the complete CMS data file", flush=True)
    compilation = bounded_run([compiler, "-O3", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
                               cpp_source, "-o", executable], artifacts / "build", 90.0, 60.0)
    report["compilation"] = compilation
    if compilation["returncode"] != 0:
        raise RuntimeError("baseline compilation did not complete successfully")
    report["baseline_binary_sha256"] = file_hash(executable)
    selected, particles, selection = select_largest_jet(dataset, artifacts)
    report["selection"] = selection
    multiplicity = len(particles)
    checks.append({"name": "all_constituents_retained", "passed": multiplicity == selection["max_constituents"]
                   and len(selected.read_text().splitlines()) == multiplicity})
    checks.append({"name": "observed_expected_CMS_max139", "passed": multiplicity == 139,
                   "observed": multiplicity})
    print(f"Selected original jet {selection['source_original_event_id']}, M={multiplicity}; no constituents removed", flush=True)
    report["integer_combinatorics"] = {
        "M": multiplicity, "N": ORDER,
        "sorted_multiset_formula": "binomial(M + N - 1, N)",
        "sorted_multiset_count": math.comb(multiplicity + ORDER - 1, ORDER),
        "ordered_with_replacement_formula": "M^N",
        "ordered_with_replacement_tuple_count": multiplicity ** ORDER,
        "interpretation": "Exact integer counts for the actual selected M, not extrapolated runtime estimates",
    }
    report["fractional_dense_storage_bound"] = {
        "M": multiplicity, "formula": "8 * 2^M", "bytes_per_subset": 8,
        "subset_count_decimal": str(1 << multiplicity),
        "minimum_payload_bytes_decimal": str(8 * (1 << multiplicity)),
        "equivalent_power_of_two_bytes": multiplicity + 3,
        "address_space_cap_bytes": MEMORY_BYTES,
        "exceeds_address_space_cap": 8 * (1 << multiplicity) > MEMORY_BYTES,
        "assumption": "One dense float64 value per full-jet subset, including the empty subset; additional geometry, work arrays, and container overhead are excluded",
        "interpretation": "Rigorous storage requirement for this naive full-subset representation, not a lower bound for all possible fractional algorithms",
        "astronomical_array_allocated": False,
    }
    sanity_dir = artifacts / "correctness_full_jet_n2"
    sanity_output = sanity_dir / "result.json"
    sanity_process = bounded_run([executable, selected, 2, KAPPA, LOG_MIN, BINS, sanity_output],
                                 sanity_dir, seconds, seconds)
    if sanity_process["returncode"] != 0 or not sanity_output.exists():
        raise RuntimeError("full-multiplicity N=2 correctness smoke test did not complete")
    sanity = json.loads(sanity_output.read_text())
    expected = pair_oracle(particles)
    observed = sanity["histogram"]
    if len(observed) != BINS or not all(math.isfinite(value) for value in observed):
        raise ValueError("invalid baseline smoke histogram")
    errors = [abs(actual - target) for actual, target in zip(observed, expected)]
    sanity_passed = (sanity["exact_full_particle_result"] and sanity["constituents"] == multiplicity
                     and sanity["multisets_completed"] == math.comb(multiplicity + 1, 2)
                     and sanity["ordered_tuples_accounted_for"] == multiplicity ** 2
                     and max(errors) <= 2e-12 and math.fsum(errors) <= 1e-11)
    report["correctness_smoke_test"] = {
        "role": "Correctness only, not scale evidence; same complete real jet, N=2, no reduction of M",
        "passed": sanity_passed, "process": sanity_process, "baseline": sanity,
        "independent_oracle": "Python explicitly enumerates all M^2 ordered pairs with replacement",
        "max_absolute_error": max(errors), "l1_error": math.fsum(errors),
        "histogram_total": math.fsum(observed),
    }
    checks.append({"name": "full_jet_ordered_pair_correctness", "passed": sanity_passed})
    print(f"Timing exact N=7, kappa=1 under {seconds:g}s wall/CPU and 3 GiB address-space limits", flush=True)
    naive_dir = artifacts / "exact_full_jet_n7"
    naive_output = naive_dir / "result.json"
    naive_process = bounded_run([executable, selected, ORDER, KAPPA, LOG_MIN, BINS, naive_output],
                                naive_dir, seconds, seconds)
    naive_result = json.loads(naive_output.read_text()) if naive_output.exists() else None
    report["exact_naive_integer"] = {
        "observable": "Exact full-particle ordered-with-replacement N=7, kappa=1 maximum-pair-distance histogram; no clustering, compression, pruning, or constituent truncation",
        "implementation": "Enumerate nondecreasing index multisets, weight each by N! / product(multiplicity!), retain repeated indices and contacts",
        "arithmetic": "Float64 histogram accumulation; exact here means combinatorial/full-particle semantics, not arbitrary-precision arithmetic",
        "process": naive_process, "result": naive_result,
        "partial_output_is_not_a_solution": naive_process["outcome"] == "timeout",
        "submitted_solution": False, "score": None,
        "completion_time_extrapolation": None,
    }
    checks.append({"name": "exact_baseline_bounded_run_recorded",
                   "passed": naive_process["outcome"] in ("completed", "timeout")})
    if naive_result is not None:
        checks.append({"name": "exact_baseline_uses_full_M_and_N7",
                       "passed": naive_result["constituents"] == multiplicity
                       and naive_result["order"] == ORDER and naive_result["kappa"] == KAPPA})
        checks.append({"name": "observed_tuple_counts_are_bounded_by_exact_counts",
                       "passed": 0 < naive_result["multisets_completed"] <= math.comb(multiplicity + ORDER - 1, ORDER)
                       and 0 < naive_result["ordered_tuples_accounted_for"] <= multiplicity ** ORDER})
        checks.append({"name": "partial_timeout_histogram_not_claimed_as_exact_result",
                       "passed": naive_process["outcome"] != "timeout" or not naive_result["exact_full_particle_result"]})
    print("Timing official C/A f=8 on the identical jet; this is a different, finite-resolution observable", flush=True)
    official_dir = artifacts / "official_ca_f8_n7"
    official_output = official_dir / "histogram.txt"
    official_process = bounded_run([official, selected, 1, ORDER, 8, LOG_MIN, BINS, official_output],
                                   official_dir, seconds, seconds)
    official_stdout = Path(official_process["stdout"]).read_text()
    official_stderr = Path(official_process["stderr"]).read_text()
    official_numbers = list(map(float, official_output.read_text().split())) if official_output.exists() else []
    official_success = (official_process["returncode"] == 0 and "Error:" not in official_stdout + official_stderr
                        and len(official_numbers) == BINS + 4
                        and official_numbers[:4] == [1.0, float(BINS), LOG_MIN, 0.0]
                        and all(math.isfinite(value) for value in official_numbers))
    report["official_ca_f8_integer"] = {
        "query": {"algorithm": "ca", "resolution": 8, "order": ORDER, "kappa": KAPPA,
                  "log_min": LOG_MIN, "bins": BINS, "recombination": "pt_scheme", "R": 1.5},
        "observable": "Official finite-resolution C/A f=8 observable: approximate relative to the exact uncompressed full-particle correlator, with different semantics",
        "same_exact_full_particle_semantics_as_naive": False,
        "same_complete_input_sha256": selection["selected_input_sha256"],
        "process": official_process, "completed_successfully": official_success,
        "histogram_mass": math.fsum(official_numbers[4:]) if official_success else None,
        "parsing_and_loop_timings_separated": False,
        "timing_note": "Unmodified official binary: reported runtime includes launch, input parsing, clustering, projection, and output",
        "accuracy_comparison_against_incomplete_naive_result": None,
        "submitted_solution": False, "score": None,
    }
    checks.append({"name": "official_completed_successfully", "passed": official_success})
    final_hashes = {str(path.relative_to(root)): file_hash(path) for path in monitored}
    report["source_hashes_after"] = final_hashes
    report["input_data_sha256_after"] = file_hash(dataset)
    checks.append({"name": "sources_binaries_and_validated_files_unchanged", "passed": initial_hashes == final_hashes})
    checks.append({"name": "full_CMS_data_unchanged", "passed": selection["source_data_sha256"] == report["input_data_sha256_after"]})
    checks.append({"name": "same_full_selected_input_unchanged", "passed": file_hash(selected) == selection["selected_input_sha256"]})
    report["artifact_sha256"] = {str(path.relative_to(root)): file_hash(path)
                                 for path in sorted(artifacts.rglob("*")) if path.is_file()}
    report["summary"] = {
        "integrity_passed": all(check["passed"] for check in checks),
        "failed_integrity_checks": [check["name"] for check in checks if not check["passed"]],
        "M": multiplicity, "N": ORDER, "exact_baseline_outcome": naive_process["outcome"],
        "exact_baseline_wall_seconds": naive_process["wall_seconds"],
        "exact_baseline_cpu_seconds": naive_process["cpu_seconds"],
        "exact_baseline_loop_wall_seconds": naive_result["loop_wall_seconds"] if naive_result else None,
        "exact_baseline_loop_cpu_seconds": naive_result["loop_cpu_seconds"] if naive_result else None,
        "official_completed_successfully": official_success,
        "official_wall_seconds": official_process["wall_seconds"],
        "official_cpu_seconds": official_process["cpu_seconds"],
        "source_contribution_scale_evidence_only": True,
        "fresh_agent_difficulty_evidence": False, "submission_failure": False, "score": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--seconds", type=float, default=15.0)
    arguments = parser.parse_args()
    if not math.isfinite(arguments.seconds) or not 0 < arguments.seconds <= 60:
        parser.error("--seconds must be in (0, 60]")
    root = arguments.root.resolve()
    started = time.monotonic()
    report = {
        "schema_version": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Realistic-scale generic-baseline evidence of source contribution, not fresh-agent difficulty evidence",
        "scope": {
            "source_files_created": ["author/direct_baseline.cpp", "author/check_direct_scale.py"],
            "persistent_outputs": ["author/direct_scale.json", "author/direct_scale/"],
            "existing_validated_files_modified": False,
            "interpretation": "The naive exact and official finite-resolution algorithms have different semantics. No same-task speedup, runtime extrapolation, solution-quality score, or submitted failure is inferred.",
            "astronomical_fractional_storage_allocated": False,
        },
        "integrity_checks": [],
    }
    try:
        run_evidence(root, arguments.seconds, report)
    except Exception as error:
        report["summary"] = {"integrity_passed": False, "sidecar_error": str(error),
                             "fresh_agent_difficulty_evidence": False,
                             "submission_failure": False, "score": None}
        report["traceback"] = traceback.format_exc()
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["total_sidecar_wall_seconds"] = time.monotonic() - started
    output = root / "author" / "direct_scale.json"
    write_json(output, report)
    print(json.dumps({"report": str(output), **report["summary"]}, sort_keys=True), flush=True)
    return 0 if report["summary"]["integrity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
