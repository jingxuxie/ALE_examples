import argparse
from concurrent.futures import ThreadPoolExecutor
import difflib
import hashlib
import subprocess
import time

from adapt import substitute
from sweep import ROOT, read_json, write_json, run_job, summarize


parser = argparse.ArgumentParser()
parser.add_argument("--case", default="n8192_b128_w18_pairs")
parser.add_argument("--seconds", type=int, default=120)
arguments = parser.parse_args()
construction = read_json(ROOT / "cases" / arguments.case / "construction.json")
original = (ROOT / "sources/bp_search.cpp").read_text()
source = substitute(original, "    auto start = std::chrono::steady_clock::now();", "    std::shuffle(impulses.begin(), impulses.end(), generator);\n    auto start = std::chrono::steady_clock::now();")
(ROOT / "sources/bp_shuffled.cpp").write_text(source)
(ROOT / "sources/bp_shuffled.patch").write_text("".join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile="adapted/bp_search.cpp", tofile="sensitivity/bp_shuffled.cpp")))
directory = ROOT / "bin" / construction["geometry_id"]
command = ["g++", "-O3", "-march=native", "-std=c++17", "-I", str(directory), str(ROOT / "sources/bp_shuffled.cpp"), "-o", str(directory / "bp_shuffled")]
completed = subprocess.run(command, capture_output=True, text=True)
write_json(ROOT / "sensitivity_adaptation.json", {"command": command, "returncode": completed.returncode, "stderr": completed.stderr, "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "change": "Additional sensitivity variant only: randomize initial impulse order using the recorded public seed; standard BP remains untouched and independently tested."})
assert completed.returncode == 0
jobs = []
for method, seed, grouping_pass, chosen_groups in (("bp_shuffled", 998244353, None, None), ("bp_shuffled", 1000000007, None, None), ("group", 104729, 0, 3), ("group", 130363, 5, 3)):
    label = f"{method}_s{seed}" + (f"_p{grouping_pass}_g{chosen_groups}" if grouping_pass is not None else "")
    jobs.append({"case": arguments.case, "phase": "sensitivity", "method": method, "seed": seed, "grouping_pass": grouping_pass, "chosen_groups": chosen_groups, "seconds": arguments.seconds, "label": label})
write_json(ROOT / "sensitivity_plan.json", jobs)
started = time.monotonic()
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run_job, jobs))
write_json(ROOT / "sensitivity_results.json", {"wall_seconds": time.monotonic() - started, "workers": 4, "results": results})
summarize()
