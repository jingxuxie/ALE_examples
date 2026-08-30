import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
STAGE = ROOT / "generations/generation_3"
sys.path.insert(0, str(STAGE / "participant/workspace"))

from search_api import certificate_screen, parse_submission, screen


def main():
    started = time.monotonic()
    payload = json.loads((ROOT / "champions/generation_2/submission.json").read_text())
    payload["parameters"]["population"] -= 0.005
    parameters = parse_submission(json.dumps(payload))
    guards = certificate_screen(parameters, all_members=True)
    coarse = screen(parameters, all_members=True)
    report = {
        "purpose": "Private passing-path resource-calibration candidate, not a participant baseline or a claimed solution before full references",
        "proposals": 1,
        "change": {"population_add": -0.005},
        "all_guards_passed": all(item["guard_passed"] for item in guards.values()),
        "minimum_uncertified_gap": min(item["observable_gap"] for item in coarse.values()),
        "maximum_certificate": max(item["certificate"] for item in guards.values()),
        "maximum_tail": max(item["tail_mass"] for item in guards.values()),
        "guards": guards,
        "uncertified_screen": coarse,
        "runtime_seconds": time.monotonic() - started,
    }
    files = {"calibration_candidate.json": payload, "calibration_candidate.screening.json": report}
    patch = ["*** Begin Patch"]
    for name, data in files.items():
        assert not (AUDIT / name).exists()
        patch.append("*** Add File: " + str(AUDIT / name))
        patch.extend("+" + line for line in json.dumps(data, indent=2, allow_nan=False).splitlines())
    patch.append("*** End Patch")
    subprocess.run(["apply_patch"], input="\n".join(patch) + "\n", text=True, check=True)
    print(json.dumps({name: value for name, value in report.items() if name not in ("guards", "uncertified_screen")}), flush=True)
    command = ["/usr/bin/python3", "-B", str(STAGE / "evaluator/evaluate.py"), "--submission", str(AUDIT / "calibration_candidate.json"), "--exhaustive", "--output", str(STAGE / "adversary/resource_calibration.json")]
    with (AUDIT / "resource_calibration.log").open("w") as output:
        subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=True)
    result = json.loads((STAGE / "adversary/resource_calibration.json").read_text())
    print(json.dumps({name: result[name] for name in ("core_score", "valid", "passed", "reason", "runtime_seconds", "resource")}), flush=True)


if __name__ == "__main__":
    main()
