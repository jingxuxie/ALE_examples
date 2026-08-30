"""Evaluate sealed public-data outputs without importing any fitting program."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


SIDE = Path(__file__).resolve().parent
CONCEPT = SIDE.parents[1]


def main():
    if (SIDE / "results.json").exists():
        raise SystemExit("Already scored; no adaptive portfolio reruns are permitted.")
    seal = json.loads((SIDE / "OUTPUTS_FROZEN.json").read_text())
    protocol = json.loads((SIDE / "PREREGISTRATION.json").read_text())
    for relative, digest in seal["files_sha256"].items():
        assert hashlib.sha256((SIDE / relative).read_bytes()).hexdigest() == digest, relative
    scores = SIDE / "scores"
    scores.mkdir(exist_ok=True)
    results = []
    for variant in protocol["variants"]:
        name = variant["name"]
        artifact = SIDE / name / "predictions.npz"
        if not artifact.exists():
            results.append({"variant": name, "completed": False, "passed": False,
                            "reason": "no completed frozen prediction artifact"})
            continue
        expected = seal["files_sha256"][str(artifact.relative_to(SIDE))]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == expected
        environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
        process = subprocess.run([sys.executable, "-I", str(CONCEPT / "evaluator" / "evaluate.py"),
                                  "--submission", str(artifact.parent)],
                                 capture_output=True, text=True, timeout=15, env=environment)
        if process.returncode not in (0, 2):
            raise RuntimeError("trusted evaluator failed for " + name)
        score = json.loads(process.stdout)
        (scores / (name + ".json")).write_text(json.dumps(score, indent=2, allow_nan=False) + "\n")
        fit_report = json.loads((artifact.parent / "fit_report.json").read_text())
        results.append({"variant": name, "completed": True, "valid": score["valid"],
                        "passed": score["passed"], "metrics": score.get("metrics"),
                        "family_mean_kl": score.get("family_mean_kl"),
                        "runtime_seconds": fit_report["runtime_seconds"],
                        "objective_evaluations": fit_report.get("objective_evaluations"),
                        "stop_reason": fit_report.get("stop_reason"),
                        "prediction_sha256": expected})
    for relative, digest in seal["files_sha256"].items():
        assert hashlib.sha256((SIDE / relative).read_bytes()).hexdigest() == digest, relative
    passing = [record["variant"] for record in results if record["passed"]]
    inference_passing = [name for name in passing if name.startswith("latent_fit_")]
    report = {"scored_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "known_achievable": bool(passing), "passing_variants": passing,
              "exact_latent_inference_passes": inference_passing, "variants": results,
              "portfolio_runtime_before_scoring_seconds": seal["runtime_seconds"],
              "provenance": "All outputs sealed before the first trusted evaluation; no scores used for fitting, initialization, tuning, or variant selection.",
              "scope": "Only adversary/public_data_portfolio was written; no fresh agents or fresh submissions used.",
              "interpretation": "A passing public-data variant demonstrates attainability; no pass leaves practical attainability unknown, not disproved."}
    (SIDE / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    lines = ["# Public-data-only attainability portfolio", "", "Known achievable: **" + ("yes" if passing else "not established") + "**.", "",
             "All variants were preregistered, fitted from participant observations and public priors only, and hash-sealed before any trusted scoring.",
             "No hidden parameters, generation seeds, query labels, or fresh submissions were read by the fitter. No scores informed training or tuning.", "",
             "| Variant | Fit/control seconds | Mean KL | Worst-family KL | Max TV | Pass |", "|---|---:|---:|---:|---:|---|"]
    for record in results:
        if not record["completed"]:
            lines.append("| " + record["variant"] + " | — | — | — | — | incomplete |")
            continue
        metrics = record["metrics"]
        lines.append("| {} | {:.2f} | {:.8f} | {:.8f} | {:.8f} | {} |".format(
            record["variant"], record["runtime_seconds"], metrics["mean_forward_kl"],
            metrics["worst_family_mean_kl"], metrics["max_tv"], record["passed"]))
    lines.extend(["", "Fixed gates: mean KL <= 0.020; worst-family mean KL <= 0.035; maximum TV <= 0.120.", "",
                  "The latent fits optimize the exact visible marginal likelihood of all 16,384 configurations, summing over adjacent hidden spins with a batched transfer recursion.",
                  "Both start independently at the public bound midpoints. Normalized quadratic penalties have fixed coefficients 0.001 and 0.01. CPU affinity uses four cores; each fit has a predeclared 360-second cap.",
                  "The other variants are an unfitted public-prior midpoint control and a Jeffreys-smoothed empirical log-probability temperature bridge with local field reweighting.", "",
                  "See PREREGISTRATION.json, STARTED.json, implementation_checks.json, OUTPUTS_FROZEN.json, individual fit_report.json files, and scores/*.json for the audit trail."])
    (SIDE / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
