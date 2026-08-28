import json
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "sources/MBP_ADOSD"
reports = []
for name, variant in (("dem", "ADOSD_DEM"), ("pauli", "ADOSD")):
    working = ROOT / f"run_{name}"
    working.mkdir(exist_ok=True)
    codes = working / "codes"
    if not codes.exists():
        codes.symlink_to(SOURCE / variant / "BPOSD_CB_proj/codes", target_is_directory=True)
    for suffix in ("Results", "Results/St", "Results/Scrn", "Results/Last"):
        (working / suffix).mkdir(parents=True, exist_ok=True)
    command = ["/usr/bin/timeout", "--signal=TERM", "--kill-after=2", "8",
               "/usr/bin/stdbuf", "-oL", "-eL", str(ROOT / "bin" / f"adosd_{name}")]
    started = time.perf_counter()
    with (ROOT / f"logs/{name}_smoke.log").open("w") as output:
        process = subprocess.run(command, cwd=working, stdout=output, stderr=subprocess.STDOUT, timeout=15)
    text = (ROOT / f"logs/{name}_smoke.log").read_text(errors="replace")
    report = {"variant": name, "command": command, "returncode": process.returncode,
              "wall_seconds": time.perf_counter() - started, "bounded_stop": process.returncode == 124,
              "log_bytes": len(text), "first_lines": text.splitlines()[:16],
              "last_lines": text.splitlines()[-12:]}
    reports.append(report)
    print(json.dumps(report), flush=True)
(ROOT / "smoke.json").write_text(json.dumps(reports, indent=2) + "\n")
