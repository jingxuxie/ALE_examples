import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

WORK = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--pid", type=int, required=True)
parser.add_argument("--family", required=True)
parser.add_argument("--slot", required=True)
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--seconds", type=int, required=True)
parser.add_argument("--mode", choices=("exact", "guard"), default="exact")
args = parser.parse_args()
command_line = Path("/proc") / str(args.pid) / "cmdline"
if command_line.exists():
    command = command_line.read_bytes()
    if str(WORK / "search").encode() not in command or args.family.encode() not in command:
        raise RuntimeError("refusing to stop any process except this private family search")
    os.kill(args.pid, signal.SIGTERM)
    time.sleep(1)
archive = WORK / (args.slot + "_cex_archive")
archive.mkdir(exist_ok=True)
for suffix in (".raw", ".json", "_search.raw", "_search.json", ".log"):
    source = WORK / (args.slot + suffix)
    if source.exists():
        shutil.copy2(source, archive / source.name)
environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
               "EXACT": "1", "REBASE": "1", "TEMP": "2", "PERIOD": "45", "FAULT_SCALE": "1", "NEAR": "0"}
for key in ("CEX", "FIXED", "VERIFY", "REPORT"):
    environment.pop(key, None)
if args.mode == "guard":
    environment.pop("EXACT", None)
    environment.pop("REBASE", None)
    environment.update(CEX="1", TEMP="2.5", SOFT_SCALE="0.5")
binary = WORK / ("search_guard" if args.mode == "guard" else "search")
command = [str(binary), args.family + ".cfg", args.slot, str(args.seconds), str(args.seed), args.family + "_g2.raw"]
started = time.monotonic()
record = {"family": args.family, "slot": args.slot, "seed": args.seed, "seconds": args.seconds,
          "seed_sha256": hashlib.sha256(str(args.seed).encode()).hexdigest(),
          "method": "pair-feasible counterexample search" if args.mode == "guard" else "exact exhaustive triple-fault Metropolis optimization from G2",
          "replaces_worker_pid": args.pid, "old_worker_archive": str(archive.relative_to(WORK)),
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "command": command,
          "temperature": float(environment["TEMP"]), "period_seconds": 45,
          "rebase": args.mode == "exact", "no_additional_cpu_slot": True}
record_path = WORK / (args.slot + "_" + args.mode + "_adaptation.json")
record_path.write_text(json.dumps(record, indent=2) + "\n")
with (WORK / (args.slot + ".log")).open("w") as log:
    completed = subprocess.run(command, cwd=WORK, env=environment, stdout=log, stderr=subprocess.STDOUT)
record.update(returncode=completed.returncode, runtime_seconds=time.monotonic() - started)
record_path.write_text(json.dumps(record, indent=2) + "\n")
