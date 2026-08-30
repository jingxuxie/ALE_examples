import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
jobs = []
for family in ("ladder16", "bridge18"):
    ranked = []
    for path in sorted(ROOT.glob(family + "_exact*_search.raw")):
        result = subprocess.check_output(["./search_rebase", family + ".cfg", "report", "0", "0", path.name],
                                         env={**os.environ, "REPORT": "1"}, text=True)
        cost = float(re.search(r" cost=([0-9.e+-]+)", result).group(1))
        ranked.append((cost, path))
    ranked.sort()
    print(family, [(cost, path.name) for cost, path in ranked[:4]], flush=True)
    for index, seed in enumerate(range(17, 33)):
        source = ranked[(index // 4) % min(3, len(ranked))][1]
        initial = ROOT / (family + "_initial" + str(seed) + ".raw")
        initial.write_text(source.read_text())
        name = family + "_exact" + str(seed)
        env = {**os.environ, "EXACT": "1", "REBASE": "1", "PERIOD": "35",
               "TEMP": str((1.5, 3, 6, 10)[index % 4]), "NEAR": "0.002" if index < 8 else "0",
               "FAULT_SCALE": "1" if index < 12 else "2"}
        log = (ROOT / (name + ".log")).open("w")
        jobs.append(subprocess.Popen(["./search_rebase", family + ".cfg", name, "900", str(300 + seed), initial.name],
                                     env=env, stdout=log, stderr=subprocess.STDOUT))
for job in jobs:
    job.wait()
