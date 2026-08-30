import concurrent.futures
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import checker


def run_degree(degree):
    directory = ROOT / "adversary/compact_stress" / f"degree_{degree}"
    directory.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update({"ASSETS": str(ROOT / "participant"), "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    started = time.monotonic()
    with (directory / "search.log").open("w") as log:
        subprocess.run([sys.executable, str(ROOT / "champions/generation_1/search.py"),
                        "--degree", str(degree), "--kind", "amplitude", "--count", "5000",
                        "--start", "174500", "--output", "counterexample.json"],
                       cwd=directory, env=environment, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=600)
    data = json.loads((directory / "counterexample.json").read_text())
    polynomial, certificate = checker.coefficients(data["P"]), checker.coefficients(data["H"])
    records = checker.audit_pair(polynomial)
    residual = checker.exact_residual(polynomial, certificate, Fraction(16, 25))
    minimum = min(record["rms_error"] for record in records)
    qualifies = residual <= Fraction(1, 10**12) and all(record["completion_valid"] and record["guard_valid"] for record in records) and minimum >= 0.05
    report = {"degree": degree, "minimum_rms_error": minimum, "certificate_residual": float(residual),
              "qualifies_except_original_degree_restriction": qualifies, "inside_original_domain": 32 <= degree <= 48,
              "elapsed_seconds": time.monotonic() - started, "configurations": records}
    (directory / "report.json").write_text(json.dumps(report, indent=2))
    print(degree, minimum, qualifies, flush=True)
    return report


def main():
    degrees = [16, 20, 24, 28, 32, 36, 40, 44]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        reports = list(executor.map(run_degree, degrees))
    good = [report["degree"] for report in reports if report["qualifies_except_original_degree_restriction"]]
    summary = {"degrees_tested": degrees, "champion_samples_per_degree": 5000,
               "smallest_verified_degree": min(good) if good else None, "profiles": reports,
               "root_cause": "counterexample degree efficiency versus exponentially sensitive phase extraction"}
    (ROOT / "adversary/compact_stress/report.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
