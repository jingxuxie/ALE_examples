import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
CONTROLLER = 221
REPLACED = (230, 232)
EXACT_LAUNCHER = 250


def active(pid):
    path = Path("/proc") / str(pid) / "stat"
    if not path.exists():
        return False
    return path.read_text().split(")", 1)[1].split()[0] != "Z"


def stop_private(pid, sig=signal.SIGTERM):
    if active(pid):
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes()
        if b"adversary/generation_3/private" not in command:
            raise RuntimeError("refusing to signal a non-private-search process")
        os.kill(pid, sig)


started = time.monotonic()
stop_private(CONTROLLER, signal.SIGSTOP)
try:
    for pid in REPLACED:
        stop_private(pid)
    time.sleep(1)
    original = (ROOT / "attempts/v_2/search.cpp").read_text()
    pair_begin = original.index("FaultResult faults(")
    pair_end = original.index("void save(", pair_begin)
    pair_code = original[pair_begin:pair_end].replace("FaultResult faults(", "FaultResult faults_pair(", 1)
    source = (WORK / "search.cpp").read_text()
    insertion = source.index("FaultResult faults(")
    source = source[:insertion] + pair_code + source[insertion:]
    old = "if(candidatecost<=ceiling) { circuit=std::move(candidate); metrics=observed; penalty=candidatepenalty; current=candidatecost; accepted++; }"
    new = "if(candidatecost<=ceiling && faults_pair(candidate,false,0).failures==0) { circuit=std::move(candidate); metrics=observed; penalty=candidatepenalty; current=candidatecost; accepted++; }"
    if old not in source:
        raise RuntimeError("counterexample-loop guard insertion failed")
    source = source.replace(old, new)
    destination = WORK / "search_guard.cpp"
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n"
    patch += "".join("+" + line + "\n" for line in source.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)
    subprocess.run(["g++", "-std=c++17", "-O3", "-march=native", "-DNDEBUG", str(destination), "-o", str(WORK / "search_guard")], check=True)
    jobs = []
    configurations = [("ladder16", "ladder16_seed2026082831", 2026082851),
                      ("bridge18", "bridge18_seed2026082833", 2026082853)]
    for family, slot, seed in configurations:
        archive = WORK / (slot + "_cex_archive")
        archive.mkdir(exist_ok=True)
        for suffix in (".raw", ".json", "_search.raw", "_search.json", ".log"):
            source_path = WORK / (slot + suffix)
            if source_path.exists():
                shutil.copy2(source_path, archive / source_path.name)
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                       "CEX": "1", "TEMP": "2.5", "PERIOD": "45", "FAULT_SCALE": "1", "SOFT_SCALE": "0.5"}
        for key in ("EXACT", "FIXED", "VERIFY", "REPORT"):
            environment.pop(key, None)
        command = [str(WORK / "search_guard"), family + ".cfg", slot, "1200", str(seed), family + "_g2.raw"]
        log = (WORK / (slot + ".log")).open("w")
        process = subprocess.Popen(command, cwd=WORK, env=environment, stdout=log, stderr=subprocess.STDOUT)
        jobs.append({"family": family, "slot": slot, "seed": seed, "seed_sha256": hashlib.sha256(str(seed).encode()).hexdigest(),
                     "command": command, "process": process, "log": log})
    record = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "method": "counterexample-guided triple search with exact up-to-two-omission feasibility preserved at every accepted mutation",
              "maximum_total_active_search_workers": 4, "seconds_per_new_worker": 1200,
              "adapted_source_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
              "adapted_binary_sha256": hashlib.sha256((WORK / "search_guard").read_bytes()).hexdigest(),
              "controller_paused_for_safe_candidate_selection": True,
              "jobs": [{key: value for key, value in job.items() if key not in ("process", "log")} for job in jobs]}
    (WORK / "phase2_config.json").write_text(json.dumps(record, indent=2) + "\n")
    while any(job["process"].poll() is None for job in jobs):
        solved = {family: any("SUCCESS" in path.read_text() for path in WORK.glob(family + "_seed*.log"))
                  for family in ("ladder16", "grid20", "bridge18")}
        if all(solved.values()):
            for job in jobs:
                if job["process"].poll() is None:
                    job["process"].terminate()
            stop_private(231)
            children = Path("/proc") / str(EXACT_LAUNCHER) / "task" / str(EXACT_LAUNCHER) / "children"
            if children.exists():
                for child in children.read_text().split():
                    stop_private(int(child))
        (WORK / "phase2_progress.json").write_text(json.dumps({"elapsed_seconds": time.monotonic() - started,
                                                              "solved_by_private_checker": solved,
                                                              "returncodes": {job["slot"]: job["process"].poll() for job in jobs}}, indent=2) + "\n")
        time.sleep(10)
    for job in jobs:
        job["process"].wait()
        job["log"].close()
    while active(EXACT_LAUNCHER):
        time.sleep(5)
    record.update(runtime_seconds=time.monotonic() - started,
                  returncodes={job["slot"]: job["process"].returncode for job in jobs})
    (WORK / "phase2_config.json").write_text(json.dumps(record, indent=2) + "\n")
finally:
    stop_private(CONTROLLER, signal.SIGCONT)
