import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "adversary/generations/generation_2/participant"
sys.path.insert(0, str(ASSETS / "workspace"))
import checker

spec = importlib.util.spec_from_file_location("baseline", ASSETS / "baseline/solve.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def run_profile(profile):
    degree, seed = profile
    directory = ROOT / "adversary/second_champion_stress" / f"degree_{degree}_seed_{seed}"
    directory.mkdir(parents=True, exist_ok=True)
    source = (ROOT / "champions/generation_2/tail_search.py").read_text()
    assert source.count("degree = 14") == 1 and source.count("default_rng(639405)") == 1
    source = source.replace("degree = 14", f"degree = {degree}").replace("default_rng(639405)", f"default_rng({seed})")
    (directory / "tail_search.py").write_text(source)
    shutil.copy2(ROOT / "champions/generation_2/search.py", directory / "search.py")
    (directory / "counterexample.json").write_text(json.dumps(baseline.candidate(degree=degree)))
    environment = os.environ.copy()
    environment.update({"ASSETS": str(ASSETS), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    with (directory / "search.log").open("w") as log:
        subprocess.run([sys.executable, str(directory / "tail_search.py")], cwd=directory,
                       env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=500)
    if (directory / "tail_best.json").exists():
        shutil.copy2(directory / "tail_best.json", directory / "counterexample.json")
    report = checker.evaluate(directory)
    (directory / "score.json").write_text(json.dumps(report, indent=2))
    row = {"degree": degree, "seed": seed, "trials": 5000, "minimum_rms_error": report.get("minimum_rms_error"),
           "core_score": report["core_score"], "admissible": report.get("admissible", False), "passed": report["passed"]}
    print(json.dumps(row), flush=True)
    return row


def main():
    profiles = [(degree, seed) for degree in (8, 10, 12, 13) for seed in (639405, 202648)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(run_profile, profiles))
    report = {"profiles": records, "adapter_changes": ["degree parameter", "random seed", "degree-matched weak initial candidate"],
              "algorithm_unchanged": True, "total_candidate_trials": sum(record["trials"] for record in records)}
    (ROOT / "adversary/second_champion_stress/report.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
