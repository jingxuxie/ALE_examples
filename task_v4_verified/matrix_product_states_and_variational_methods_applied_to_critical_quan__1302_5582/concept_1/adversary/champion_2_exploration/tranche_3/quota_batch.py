import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import concurrent.futures
import json
from pathlib import Path
import resource
import signal
import subprocess
import time

from focused_search import ROOT, allocation_differences, atomic_json, concept_path, measured_record, read_json, stamp
from harness import diagnostics, launch, limits, load_mps, measure, sha256, write_json


def run_quota(case, cuts, even_quota, seed_label, budget=35.0):
    label = "quota_" + "_".join(map(str, cuts)) + "_even_" + str(even_quota)
    directory = ROOT / "runs" / case / label
    directory.mkdir(parents=True, exist_ok=False)
    original_path = ROOT / "requests" / (case + ".json")
    request = read_json(original_path)
    request.update(budget_seconds=budget, wall_seconds=120.0)
    request_path = directory / "request.json"
    write_json(request_path, request)
    seed_path = ROOT / "runs" / case / seed_label / "state.npz"
    state_path = directory / "state.npz"
    command = [sys.executable, "-B", str(ROOT / "quota_teacher.py"), "--request", str(request_path),
               "--output", str(state_path), "--seed", str(seed_path), "--cuts", *map(str, cuts),
               "--even-quota", str(even_quota), "--budget", str(budget - 3)]
    started = time.monotonic()
    timed_out = False
    with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                   start_new_session=True, preexec_fn=lambda: limits(budget))
        while True:
            waited, status, usage = os.wait4(process.pid, os.WNOHANG)
            if waited:
                break
            if time.monotonic() - started > 150:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(0.05)
        process.returncode = os.waitstatus_to_exitcode(status)
    result = {
        "case_id": case, "solver": "quota_teacher", "run_label": label, "budget_seconds": budget,
        "mode": "private source-native direct child, not frozen evaluator certification", "command": command,
        "cpu_seconds": usage.ru_utime + usage.ru_stime, "wall_seconds": time.monotonic() - started,
        "returncode": process.returncode, "outer_wall_timeout": timed_out, "peak_rss_kib": usage.ru_maxrss,
        "ground_energy_certified": False, "request_sha256": sha256(request_path),
        "original_request_sha256": sha256(original_path), "seed_sha256": sha256(seed_path),
        "seed_path": concept_path(seed_path), "forced_quota_cuts": cuts, "even_quota": even_quota,
        "source_hash_manifest_sha256": sha256(ROOT / "SOURCE_HASHES.json"),
        "quota_source_manifest_sha256": sha256(ROOT / "QUOTA_SOURCE_HASHES.json"),
    }
    result["resource_observation_valid"] = (process.returncode == 0 and not timed_out
        and result["cpu_seconds"] <= budget and result["wall_seconds"] <= request["wall_seconds"])
    result["physical_validity"] = False
    if state_path.exists():
        try:
            tensors = load_mps(state_path, request)
            result.update(measurement=measure(tensors, request), physical_validity=True,
                          state_sha256=sha256(state_path), state_bytes=state_path.stat().st_size)
            result["diagnostics"] = diagnostics(tensors, request, result["measurement"]["energy"])
        except Exception as error:
            result["physical_validity"] = False
            result["measurement_error"] = repr(error)
    write_json(directory / "result.json", result)
    print(json.dumps({key: result.get(key) for key in ("case_id", "run_label", "measurement", "physical_validity", "cpu_seconds", "wall_seconds")}), flush=True)
    return result


def main():
    started = time.monotonic()
    original_cpu = read_json(ROOT / "ALLOCATION_ACCOUNTING.json")["cumulative_search_cpu_seconds"]
    write_json(ROOT / "QUOTA_SOURCE_HASHES.json", {
        path.name: sha256(path) for path in (ROOT / "quota_teacher.py", ROOT / "quota_batch.py")})
    findings = []
    selected = None
    trials = [(4, [2, 62], 7, "v4_40"), (5, [3, 61], 7, "v4_40"),
              (6, [2, 62], 7, "v4_40"), (1, [5, 59], 8, "v3_40")]

    def accounting():
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        total = usage.ru_utime + usage.ru_stime + time.process_time()
        return {"child_cpu_seconds": usage.ru_utime + usage.ru_stime, "controller_cpu_seconds": time.process_time(),
                "total_cpu_seconds": total, "wall_seconds": time.monotonic() - started,
                "cumulative_search_cpu_seconds": original_cpu + total, "cpu_limit_seconds": 1200}

    def checkpoint(active):
        current = read_json(ROOT / "CHECKPOINT.json")
        current.update(status="dimer_quota_refinement", controller_pid=os.getpid(), controller_running=True,
                       active=active, quota_findings=findings, quota_accounting=accounting(), updated_utc=stamp())
        atomic_json(ROOT / "CHECKPOINT.json", current)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for suffix, cuts, quota, seed_label in trials:
            if accounting()["cumulative_search_cpu_seconds"] + 210 > 1200:
                break
            case = "f3_dimerized_even_ground_" + str(suffix)
            baseline = read_json(ROOT / "runs" / case / "v4_40/result.json")
            checkpoint({"case": case, "forced_even_quota": quota, "cuts": cuts, "new_configuration": False})
            trial = run_quota(case, cuts, quota, seed_label)
            finding = {"case_id": case, "label": trial["run_label"], "physical_validity": trial["physical_validity"]}
            if trial["physical_validity"]:
                gap = baseline["measurement"]["energy"] - trial["measurement"]["energy"]
                finding.update(reference_energy=trial["measurement"]["energy"], v4_gap=gap, screen_ratio=gap / 6.4e-6,
                               allocation_difference_cuts=allocation_differences(baseline, trial))
            findings.append(finding)
            checkpoint(None)
            if not trial["physical_validity"] or finding["v4_gap"] < 12.8e-6:
                continue
            checkpoint({"case": case, "solvers": ["repeat_v4_40", "quota_warm_teacher_60"]})
            repeat_job = pool.submit(launch, case, "v4", 40, run_label="repeat_v4_40")
            refine_job = pool.submit(launch, case, "teacher", 60,
                                     seed=ROOT / "runs" / case / trial["run_label"] / "state.npz",
                                     run_label="quota_warm_teacher_60")
            repeat = repeat_job.result()
            refined = refine_job.result()
            if not (repeat["physical_validity"] and repeat["resource_observation_valid"] and refined["physical_validity"]):
                continue
            if min(baseline["measurement"]["energy"], repeat["measurement"]["energy"]) - refined["measurement"]["energy"] < 12.8e-6:
                continue
            selected = measured_record("dimerized_even_ground", case, ROOT, "quota_warm_teacher_60")
            selected["provenance"]["reference_type"] = seed_label + "_seed_prescribed_quota_then_corrected_warm_teacher"
            selected["provenance"]["quota_result"] = concept_path(ROOT / "runs" / case / trial["run_label"] / "result.json")
            selected["provenance"]["forced_quota_cuts"] = cuts
            selected["provenance"]["forced_even_quota"] = quota
            selected["provenance"]["v3_portfolio_alone_certifies_this_gap"] = False
            break
    final_accounting = accounting()
    final_accounting.update(stop_reason="confirmed_fourth_family_partner" if selected else "bounded_existing_case_quota_refinement_exhausted")
    write_json(ROOT / "QUOTA_ACCOUNTING.json", final_accounting)
    write_json(ROOT / "QUOTA_FINDINGS.json", {"findings": findings, "accounting": final_accounting, "selected": selected})
    proposal = read_json(ROOT / "PROPOSAL.json")
    if selected:
        proposal["cases"].append(selected)
    proposal.update(suite_complete=len(proposal["cases"]) == 8, quota_findings=concept_path(ROOT / "QUOTA_FINDINGS.json"),
                    quota_accounting=final_accounting)
    atomic_json(ROOT / "PROPOSAL.json", proposal)
    current = read_json(ROOT / "CHECKPOINT.json")
    confirmed = {record["family"] for record in proposal["cases"] if record["provenance"]["source_scope"] == "tranche_3"}
    current.update(status="complete" if selected else "bounded_search_partial", active=None,
                   family_partners_confirmed=sorted(confirmed), actual_proposal_records=proposal["cases"],
                   suite_complete=proposal["suite_complete"], controller_running=False,
                   quota_findings=findings, quota_accounting=final_accounting, updated_utc=stamp())
    atomic_json(ROOT / "CHECKPOINT.json", current)
    print(json.dumps({"final_records": len(proposal["cases"]), "accounting": final_accounting}), flush=True)


if __name__ == "__main__":
    main()
