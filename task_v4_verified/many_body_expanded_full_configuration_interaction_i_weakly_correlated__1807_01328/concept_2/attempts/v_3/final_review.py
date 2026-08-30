import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
import resource
import stat
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PARTICIPANT = Path("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/many_body_expanded_full_configuration_interaction_i_weakly_correlated__1807_01328/concept_2/adversary/ratchet_2/participant")
sys.path.insert(0, str(PARTICIPANT / "workspace"))
import model


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


def run_checker(name, options):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["TMPDIR"] = str(ROOT)
    started = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    completed = subprocess.run([sys.executable, "-B", str(PARTICIPANT / "workspace" / "check.py"),
                                str(ROOT / "witness.json"), "--report", str(ROOT / name), *options],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=ROOT, env=environment, timeout=90, preexec_fn=limits, check=True, text=True)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = json.loads(completed.stdout)
    assert report["valid"], report
    print(name, "passed", report["passed"],
          {family: values["successes"] for family, values in report["robustness_families"].items()}, flush=True)
    return dict(report=name, valid=report["valid"], passed=report["passed"],
                core_score=report["core_score"], families=report["robustness_families"],
                wall_seconds=time.monotonic() - started,
                cpu_seconds=(after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
                peak_rss_kib=after.ru_maxrss, stderr=completed.stderr)


def main():
    path = ROOT / "witness.json"
    information = path.lstat()
    assert stat.S_ISREG(information.st_mode) and not path.is_symlink()
    assert information.st_size <= 32768
    candidate = model.load_witness(path)
    model.decode_witness(candidate)
    metrics = model.compute(candidate, complete=True)
    assessment = model.score(metrics)
    assert assessment["passed"], assessment
    energies, hopping, density = model.full_coefficients(candidate)
    independent_values = np.linalg.eigvalsh(model.hamiltonian(127, hopping, density, energies))
    independent_error = abs(float(independent_values[0]) - metrics["full_energy_eh"])
    independent_gap_error = abs(float(independent_values[1] - independent_values[0]) - metrics["spectral_gap_eh"])
    assert max(independent_error, independent_gap_error, metrics["closure_error_eh"], metrics["eigen_residual_eh"]) <= 5e-10
    (ROOT / "nominal_diagnostic.json").write_text(json.dumps(dict(assessment=assessment, metrics=metrics), indent=2) + "\n")
    checks = [run_checker("public_diagnostic.json", []),
              run_checker("holdout_diagnostic.json", ["--seed", "419628", "--samples", "128"])]
    verification = dict(artifact="witness.json", bytes=information.st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        nominal_passed=assessment["passed"], independent_full_energy_error_eh=independent_error,
                        independent_gap_error_eh=independent_gap_error, checks=checks,
                        all_public_targets_met=all(check["passed"] for check in checks),
                        hidden_assay_available=False)
    (ROOT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(json.dumps({key: value for key, value in verification.items() if key != "checks"}), flush=True)


if __name__ == "__main__":
    main()
