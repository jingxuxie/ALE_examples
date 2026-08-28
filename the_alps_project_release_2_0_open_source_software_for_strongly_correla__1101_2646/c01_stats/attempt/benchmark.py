"""Exercise the complete CLI at the contract's maximum input dimensions."""

import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np

from test_solve import EXPRESSIONS


def main():
    root = Path(__file__).resolve().parent
    scratch = root / "benchmark_artifacts"
    scratch.mkdir(exist_ok=True)
    random = np.random.default_rng(103)
    replicas = []
    for length in [19003, 23011, 27007, 24001, 26978]:
        latent = np.repeat(random.normal(size=((length + 31) // 32, 1)), 32, axis=0)[:length]
        values = 4 + np.arange(8) + 0.1 * latent + 0.05 * random.normal(size=(length, 8))
        signs = np.where(np.arange(length) % 12 < 10, 1, -1)
        replicas.append({"signs": signs.tolist(), "measurements": values.tolist()})
    data = {"schema_version": 1, "block_sizes": [1, 31, 997, 4096],
            "expressions": EXPRESSIONS, "replicas": replicas}
    input_path = scratch / "input.json"
    output_path = scratch / "output.json"
    input_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    start = time.perf_counter()
    subprocess.run([sys.executable, str(root / "solve.py"), "--input", str(input_path),
                    "--output", str(output_path)], cwd=scratch, timeout=120, check=True)
    elapsed = time.perf_counter() - start
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert [analysis["block_size"] for analysis in result["analyses"]] == data["block_sizes"]
    for analysis in result["analyses"]:
        assert len(analysis["replicas"]) == 5
        for statistics in [analysis["pooled"]] + analysis["replicas"]:
            mean = np.asarray(statistics["mean"])
            covariance = np.asarray(statistics["covariance"])
            assert mean.shape == (6,) and covariance.shape == (6, 6)
            assert np.isfinite(mean).all() and np.isfinite(covariance).all()
            np.testing.assert_array_equal(covariance, covariance.T)
            assert np.linalg.eigvalsh(covariance).min() >= -1e-12
    peak_mib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
    report = {"rows": 120000, "columns": 8, "expressions": 6, "replicas": 5,
              "scales": 4, "cli_seconds": elapsed, "peak_child_mib": peak_mib}
    (scratch / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
