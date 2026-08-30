import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
FAMILIES = ("ladder16", "grid20", "bridge18")
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def write(name, value):
    (WORK / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def report(family, raw):
    started = time.monotonic()
    result = subprocess.run([str(WORK / "search"), family + ".cfg", "unused", "0", "0", raw],
                            cwd=WORK, env={**ENV, "REPORT": "1"}, check=True, capture_output=True, text=True)
    fields = {key: float(value) for key, value in re.findall(r"(\w+)=([0-9.e+-]+)", result.stdout)}
    return {"raw": raw, "runtime_seconds": time.monotonic() - started, "fields": fields, "stdout": result.stdout}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=1700)
    args = parser.parse_args()
    started = time.monotonic()
    frozen = json.loads((ROOT / "evaluator/hidden/freeze_manifest.json").read_text())
    frozen_hashes = {**frozen["public_file_sha256"], **frozen["trusted_source_sha256"]}
    for path in ("status.json", "evaluator/hidden/freeze_manifest.json", "evaluator/hidden/frozen_spec.json"):
        frozen_hashes[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    write("frozen_hashes_at_start.json", frozen_hashes)
    small = subprocess.run([str(WORK / "search"), "small.cfg", "verify", "0", "2026082830", "small.raw"],
                           cwd=WORK, env={**ENV, "VERIFY": "1"}, capture_output=True, text=True, check=True)
    (WORK / "small_validation.log").write_text(small.stdout + small.stderr)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        initial = list(pool.map(lambda family: report(family, family + "_g2.raw"), FAMILIES))
    sweep = json.loads((ROOT / "adversary/generation_3/champion_triple_sweep.json").read_text())
    for family, result in zip(FAMILIES, initial):
        expected = sweep["families"][family]
        assert result["fields"]["scenarios"] == expected["scenarios"]
        assert result["fields"]["failed_scenarios"] == expected["by_omission_count"]["3"]["failed_scenarios"]
        assert abs(result["fields"]["score"] - 1 / 3) < 1e-6
    write("optimizer_validation.json", {"small_circuits": "30 mutations, every up-to-three omission, sparse conjugated errors versus explicit deletion symplectic rows",
                                        "small_seed": 2026082830, "small_seed_sha256": hashlib.sha256(b"2026082830").hexdigest(),
                                        "actual_champion_full_sweep_parity": initial,
                                        "official_reference": "adversary/generation_3/champion_triple_sweep.json"})
    jobs = []
    configurations = [("ladder16", 2026082831, 3.0, 0.5, False),
                      ("grid20", 2026082832, 3.0, 0.5, False),
                      ("bridge18", 2026082833, 3.0, 0.5, False),
                      ("grid20", 2026082834, 6.0, 0.25, True)]
    for family, seed, temperature, soft_scale, fixed in configurations:
        output = family + "_seed" + str(seed)
        environment = {**ENV, "CEX": "1", "TEMP": str(temperature), "SOFT_SCALE": str(soft_scale), "PERIOD": "50", "FAULT_SCALE": "1"}
        if fixed:
            environment["FIXED"] = "1"
        log = (WORK / (output + ".log")).open("w")
        command = [str(WORK / "search"), family + ".cfg", output, str(args.seconds), str(seed), family + "_g2.raw"]
        process = subprocess.Popen(command, cwd=WORK, env=environment, stdout=log, stderr=subprocess.STDOUT)
        jobs.append({"family": family, "seed": seed, "seed_sha256": hashlib.sha256(str(seed).encode()).hexdigest(),
                     "temperature": temperature, "soft_scale": soft_scale, "fixed_matchings": fixed,
                     "output": output, "command": command, "process": process, "log": log})
    config = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "maximum_workers": 4,
              "search_seconds_per_worker": args.seconds, "frozen_spec_sha256": frozen["spec_sha256"],
              "initialization": "previous-generation champion; privileged generation asymmetry",
              "jobs": [{key: value for key, value in job.items() if key not in ("process", "log")} for job in jobs]}
    write("config.json", config)
    print("Private optimizer verified; four bounded workers launched", flush=True)
    deadline = time.monotonic() + args.seconds + 45
    while any(job["process"].poll() is None for job in jobs):
        solved = {family: next((job["output"] for job in jobs if job["family"] == family and "SUCCESS" in (WORK / (job["output"] + ".log")).read_text()), None)
                  for family in FAMILIES}
        for job in jobs:
            if solved[job["family"]] and job["process"].poll() is None:
                job["process"].terminate()
        if time.monotonic() > deadline:
            for job in jobs:
                if job["process"].poll() is None:
                    job["process"].terminate()
        write("progress.json", {"elapsed_seconds": time.monotonic() - started, "solved_by_private_exact_checker": solved,
                                "jobs": [{"output": job["output"], "returncode": job["process"].poll(),
                                          "latest": (WORK / (job["output"] + ".log")).read_text().splitlines()[-1:]}
                                         for job in jobs]})
        time.sleep(10)
    for job in jobs:
        job["process"].wait()
        job["log"].close()
    selected = {}
    candidates = {}
    for family in FAMILIES:
        raw_files = [family + "_g2.raw"]
        raw_files += [job["output"] + suffix for job in jobs if job["family"] == family for suffix in (".raw", "_search.raw")
                      if (WORK / (job["output"] + suffix)).exists()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda raw: report(family, raw), raw_files))
        candidates[family] = results
        selected[family] = max(results, key=lambda result: (result["fields"]["score"], -result["fields"]["faults"], -result["fields"]["cost"]))
    write("candidate_selection.json", {"selected": selected, "candidates": candidates})
    circuits = [json.loads((WORK / selected[family]["raw"]).with_suffix(".json").read_text()) for family in FAMILIES]
    write("artifact.json", {"schema_version": 1, "circuits": circuits})
    print("Official independent exhaustive evaluation starting", flush=True)
    official_started = time.monotonic()
    evaluation = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), "--submission", str(WORK / "artifact.json"),
                                 "--output", str(WORK / "official_report.json")], cwd=WORK, env=ENV, check=True, capture_output=True, text=True)
    official = json.loads(evaluation.stdout)
    unchanged = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected for path, expected in frozen_hashes.items()}
    summary = {"state": "complete", "official_valid": official["valid"], "official_passed": official["passed"],
               "official_core_score": official["core_score"], "solvability": "demonstrated" if official["passed"] else "unknown",
               "best_artifact": "artifact.json", "independent_official_report": "official_report.json",
               "runtime_seconds": time.monotonic() - started, "official_runtime_seconds": time.monotonic() - official_started,
               "maximum_cpu_workers": 4, "all_frozen_files_unchanged": all(unchanged.values()),
               "frozen_hash_checks": unchanged, "no_fresh_attempts_accessed": True,
               "privileged_initialization": "G2 champion and G2 solver source only",
               "search_config": "config.json", "optimizer_validation": "optimizer_validation.json",
               "provenance": "provenance.json"}
    write("summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
