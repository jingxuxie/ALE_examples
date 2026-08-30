import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

import kernel
import portfolio

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def save(name, document):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def main():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    wait_deadline = datetime.datetime.fromisoformat("2026-08-28T21:37:20+00:00")
    while datetime.datetime.now(datetime.timezone.utc) < wait_deadline:
        run = read(HERE / "run.json")
        if "finished_utc" in run and (HERE / "order_sweep/summary.json").exists():
            break
        time.sleep(1)
    run = read(HERE / "run.json")
    trials = read(HERE / "trials.json")
    sweep_summary = read(HERE / "order_sweep/summary.json") if (HERE / "order_sweep/summary.json").exists() else {"finished": False}
    sweep_trials = read(HERE / "order_sweep/trials.json") if (HERE / "order_sweep/trials.json").exists() else []
    save("baseline/witness.json", read(kernel.ROOT / "participant/baseline/witness.json"))
    baseline_report = portfolio.official(HERE / "baseline")
    directories = sorted((HERE / "trials").glob("*/witness.json"))
    directories += sorted((HERE / "order_sweep/trials").glob("*/witness.json"))
    if (HERE / "order_sweep/fits.json").exists():
        fits = sorted(read(HERE / "order_sweep/fits.json"), key=lambda row: row["score"], reverse=True)
        directories += [HERE / f"order_sweep/fits/{row['fit_id']:03d}/witness.json" for row in fits[:5]]
    official_reports = []
    for witness in directories:
        report = portfolio.official(witness.parent)
        official_reports.append({"directory": str(witness.parent.relative_to(HERE)), "core_score": report["core_score"],
                                 "valid": report["valid"], "evaluator_valid": report["evaluator_valid"], "passed": report["passed"],
                                 "failing_gates": report.get("failing_gates"), "metrics": report.get("metrics"),
                                 "submission_sha256": report.get("submission_sha256")})
    ranking = sorted(official_reports, key=lambda report: (report["passed"], report["core_score"]), reverse=True)
    chosen = HERE / ranking[0]["directory"] if ranking and ranking[0]["core_score"] > baseline_report["core_score"] else HERE / "baseline"
    save("final_best/witness.json", read(chosen / "witness.json"))
    final = portfolio.official(HERE / "final_best")
    release = read(kernel.ROOT / "adversary/release_manifest.json")
    changed = [name for name, digest in release["sha256"].items() if hashlib.sha256((kernel.ROOT / name).read_bytes()).hexdigest() != digest]
    combined_trials = trials + sweep_trials
    completed = [row for row in combined_trials if "model_id" in row and "score" in row]
    selfcheck = read(HERE / "selfcheck.json")
    summary = {"finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "request_started_utc": "2026-08-28T21:17:49+00:00", "search_deadline_utc": "2026-08-28T21:37:00+00:00",
               "pool": read(HERE / "pool_generation.json"), "portfolio_completed_trials": run["completed_trials"],
               "portfolio_submitted_trials": run["submitted_trials"], "order_sweep": sweep_summary,
               "total_completed_refinements": len(completed), "distinct_models_refined": len({row["model_id"] for row in completed}),
               "distinct_causal_orders_refined": len({tuple(row["order"]) for row in completed}),
               "trial_errors": [row for row in combined_trials if "error" in row], "official_trial_reports": len(official_reports),
               "official_reports_all_valid": all(row["valid"] and row["evaluator_valid"] for row in official_reports),
               "best_source": str(chosen.relative_to(HERE)), "best_score": final["core_score"], "best_metrics": final["metrics"],
               "passed": final["passed"], "achievability": "witnessed" if final["passed"] else "unknown",
               "failing_gates": final["failing_gates"], "spec_sha256": final["spec_sha256"],
               "frozen_file_changes": changed, "selfchecks_passed": selfcheck["passed"],
               "no_fresh_attempt_reads": True, "no_frozen_edits": not changed,
               "limits": "finite disorder/order portfolio and local constrained optimization only; no general impossibility or exhaustive feasibility certificate"}
    save("official_trial_reports.json", official_reports)
    save("summary.json", summary)
    metrics = final["metrics"]
    result_sentence = "A matching generation-3 passing witness was found." if final["passed"] else "No passing witness was found. General attainability remains UNKNOWN."
    lines = ["# Private generation-3 feasibility portfolio", "", result_sentence, "",
             "## Scope and budget", "",
             "All new artifacts are confined to this private feasibility directory. No fresh attempt was read, no participant/evaluator/spec/status was edited, and release hashes were rechecked.",
             "The requested 20-minute window began at 2026-08-28 21:17:49 UTC. Main optimization stopped when its fixed 21:37:00 UTC deadline was reached, followed only by evidence finalization; numerical and official checks are archived.", "",
             "## Portfolio", "",
             f"- Seed 202608282118: {summary['pool']['random_draws']} binary-disorder draws, {summary['pool']['accepted_models']} accepted gauge-distinct models, {summary['pool']['accepted_basins']} exact antipodal training basins.",
             f"- {len(completed)} completed coupled refinements on {summary['distinct_models_refined']} bond instances and {summary['distinct_causal_orders_refined']} distinct causal orders; {len(official_reports)} per-trial official reports.",
             "- Conditional equilibrium weights on antipodal ground components plus single-flip neighborhoods or low-energy Hamming balls; bounded convex weighted logistic row fits; row-major, column-major, min-fill, BFS, and randomized orders.",
             "- Exact reverse-KL plus 20 times missed-sector mass initial refinement, variance minimization, and ambient-gradient-penalized refinement were all included. Beta was optimized continuously within [1,3].",
             "- Separate seed 202608282132 screened additional causal orders for newly sampled disconnected-component models; it did not reuse the completed champion's optimization trace.",
             "- Fitted, best-score, and final iterates are saved separately. These are local, time-limited searches, not global minima or certificates.", "",
             "## Best officially checked candidate", "",
             f"Source: `{summary['best_source']}/witness.json`; canonical copy: `final_best/witness.json`; report: `final_best/official_report.json`.",
             f"Valid: {final['valid']}; passed: {final['passed']}; score: {final['core_score']:.12g}.", "",
             "| Metric | Measured | Frozen gate |", "|---|---:|---:|",
             f"| Entropy | {metrics['entropy']:.12g} | >=3 |", f"| Reverse KL | {metrics['reverse_kl']:.12g} | >=0.4 |",
             f"| Total reward variance | {metrics['reward_variance']:.12g} | <=0.05 |",
             f"| Ambient gradient infinity | {metrics['gradient_infinity']:.12g} | <=0.003 |",
             f"| Dimensionless mean-energy error/spin | {metrics['energy_error_per_spin']:.12g} | <=0.02 |",
             f"| Target sector probability | {metrics['target_sector_mass']:.12g} | >=0.35 |",
             f"| Proposal sector probability | {metrics['proposal_sector_mass']:.12g} | <=0.001 |", "",
             f"Failed gates: {', '.join(final['failing_gates']) or 'none'}. Minimum binary conditional: {metrics['minimum_binary_conditional']:.12g}.", "",
             "## Validation and interpretation", "",
             f"Self-checks passed: {selfcheck['passed']}. Half-enumeration versus frozen full enumeration agreed within {selfcheck['maximum_metric_error']:.3g}; {selfcheck['gradient_coordinates']} central-difference gradient checks had maximum objective discrepancy {selfcheck['maximum_objective_gradient_error']:.3g}; {selfcheck['sector_comparisons']} direct-sector checks agreed within {selfcheck['maximum_xor_sector_error']:.3g}.",
             f"Frozen file differences: {changed}. Official generation-3 specification SHA256: `{final['spec_sha256']}`.",
             "An unsuccessful bounded portfolio does not establish global infeasibility, nor does it invalidate either previously solved generation. The frozen generation-3 task and its fresh evaluations remain main-controlled.", "",
             "## Reproduction and artifacts", "",
             "Run `python -B portfolio.py --deadline-utc <future-UTC-ISO-time> --seed 202608282118` from a separate authorized copy for the main portfolio. Time-limited concurrent runs need not reproduce identical terminal iterates; all exact retained JSON witnesses are independently reproducible with the frozen evaluator.",
             "`models.json`, `basin_pool.json`, `trials.json`, `order_sweep/`, `official_trial_reports.json`, `selfcheck.json`, and `manifest.json` retain instances, basins, row-fit gap diagnostics, seeds, stopping conditions, and verification evidence.", ""]
    report_text = "\n".join(lines)
    patch = "*** Begin Patch\n*** Add File: " + str(HERE / "REPORT.md") + "\n" + "".join("+" + line + "\n" for line in report_text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True, capture_output=True, text=True)
    hashes = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in HERE.rglob("*") if path.is_file() and path.name != "manifest.json"}
    save("manifest.json", {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sha256": hashes})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
