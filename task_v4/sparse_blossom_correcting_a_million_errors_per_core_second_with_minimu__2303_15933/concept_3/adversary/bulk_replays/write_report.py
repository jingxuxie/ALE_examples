import json
from pathlib import Path

from replay import check_unchanged


SIDE = Path(__file__).resolve().parent


def main():
    manifest = check_unchanged()
    analysis = json.loads((SIDE / "analysis.json").read_text())
    tapes = analysis["tapes"]
    for tape in ("tape_1", "tape_2", "tape_3"):
        raw = json.loads((SIDE / (tape + "_report.json")).read_text())
        for policy in ("candidate", "reference"):
            assert tapes[tape][policy]["episodes_completed"] == 12
            assert tapes[tape][policy]["valid"]
            for row in raw["policies"][policy]["episodes"]:
                assert row["source_unchanged"] and row["shots_used"] == 40000
                assert row["queries"] <= 64 and row["cpu_seconds"] <= 60
    candidate_passes = sum(tapes[tape]["candidate"]["passes_original_thresholds_on_this_tape"] for tape in ("tape_1", "tape_2", "tape_3"))
    reference_passes = sum(tapes[tape]["reference"]["passes_original_thresholds_on_this_tape"] for tape in ("tape_1", "tape_2", "tape_3"))
    repeat_failures = sum(tapes[tape]["candidate"]["chain_bulk_log_rmse"] > 0.095 for tape in ("tape_1", "tape_2", "tape_3"))
    diagnosis = analysis["diagnostics"]["official_reproduction/candidate/chain_hooks_0"]
    pair = next(item for item in diagnosis["bulk_pairs"] if item["indices"] == [7, 13])
    fraction = analysis["official_chain_bulk_episode_sse_fractions"]["chain_hooks_0"]
    cpu_candidate = max(tapes[tape]["candidate"]["maximum_cpu_seconds"] for tape in ("tape_1", "tape_2", "tape_3"))
    cpu_reference = max(tapes[tape]["reference"]["maximum_cpu_seconds"] for tape in ("tape_1", "tape_2", "tape_3"))
    lines = ["# Supplementary diagnosis of the official E fresh-v1 failure", "",
        "**The official score is unchanged.** This is a private, post-completion diagnostic, not a new generation, fresh attempt, retest that replaces the official score, or feedback to the fresh agent.", "",
        "## Official failure and directly observed mechanism", "",
        "The frozen program scored mean log-RMSE **0.05593327143062893** and worst regime/family log-RMSE **0.13307673088502028**, failing fixed limits 0.055 and 0.095. The failing cell is `chain_hooks/bulk`; every other cell is at most 0.0641068. Runtime was valid.", "",
        "An unmodified isolated replay of `chain_hooks_0` exactly reproduces its official metrics. An additional trace wrapper runs the frozen source inside the same isolated worker, never in the simulator process, and reproduces the entire query/observation transcript and final estimate exactly.", "",
        "- `chain_hooks_0` contributes **%.2f%%** of the official chain/bulk squared error." % (100 * fraction),
        "- Its channels **07 and 13** contribute **%.2f%%** of that episode's bulk squared error, or **%.2f%%** of the whole failing cell's squared error." % (100 * pair["fraction_of_episode_bulk_sse"], 100 * fraction * pair["fraction_of_episode_bulk_sse"]),
        "- They have identical primary/alternate detector masks `[12, 6]` and the same exposure sector 0. They are not exactly unidentifiable: known action-specific exposures/mixing distinguish them. Under the realized allocation their true-rate local Fisher correlation is **%.4f**." % pair["true_fisher_correlation"],
        "- True rates `[0.01079250, 0.01724413]` are estimated as `[0.01570201, 0.00981435]`: opposite log errors **+0.37494 / -0.56363**. This is unstable separation of an aliased pair, not general underestimation of all bulk channels.",
        "- The pair's log-rate contrast error is **0.93856** versus local Fisher SD **0.43501** (about **2.16** local SDs). Its sum has much smaller log error, **-0.09419**. This supports a contrast/aliasing diagnosis rather than missing the overall fault activity.", "",
        "## What the frozen algorithm actually did", "",
        "The source optimizes the mean of four predicted family RMS errors (`attempts/v_1_frozen_submission/solution.py:90` and `:102`), not the scored worst-cell guardrail. It uses a 910-shot effective pilot, then 2,500 and 9,000 additional shots, then the final 27,590 shots (`:194`, `:200`, `:246`). The last design is fixed from the estimate at 12,410 shots, without further refitting during that allocation.", "",
        "The initial pair estimates move along the weakly constrained contrast. At 12,410 shots the two log errors are -0.3654/+0.1546; after the final allocation the ML errors reverse to +0.4205/-0.6264. The final plan predicts per-episode bulk SD 0.09172 at its estimated parameters; evaluating information at the true parameters under the realized allocation gives 0.12171. The robust reference's realized allocation gives 0.10666 for this episode and pair-contrast SD 0.36205 instead of 0.43501. These are post-hoc local design diagnostics, not scored cell RMSEs or proof of a causal allocation effect.", "",
        "**Posterior averaging did not create the error.** It reduces this episode's bulk RMSE from **0.268256** to **0.240308**, with effective importance sample count **189.81** (fallback threshold 30). Three independent fits using the trusted likelihood, started at bounds midpoint, a fixed random point, and the candidate's pre-posterior estimate, recover the same ML point within **1.14e-5** in every log rate. There is no evidence here of solver nonconvergence or posterior fallback as the cause.", "",
        "## Three predeclared supplementary noise tapes", "",
        "Each tape uses all **12 original hidden parameter instances**. Only simulator sampling seeds differ. Each policy/episode uses a fresh, independent writable runtime copy with source SHA verified before and after; the original bubblewrap evaluator, API, 40,000-shot budget, 64-query cap, and 60-second CPU cap are unchanged. No candidate code is imported by the evaluator. Both policies receive only the public spec and observed syndromes.", "",
        "| Tape | Candidate mean / worst | Meets original limits on this tape | Robust reference mean / worst | Meets original limits on this tape |",
        "|---|---:|:---:|---:|:---:|"]
    for tape in ("tape_1", "tape_2", "tape_3"):
        candidate = tapes[tape]["candidate"]
        reference = tapes[tape]["reference"]
        lines.append("| %s | %.6f / %.6f | %s | %.6f / %.6f | %s |" % (
            tape, candidate["mean_family_log_rmse"], candidate["worst_family_log_rmse"],
            "Yes" if candidate["passes_original_thresholds_on_this_tape"] else "No",
            reference["mean_family_log_rmse"], reference["worst_family_log_rmse"],
            "Yes" if reference["passes_original_thresholds_on_this_tape"] else "No"))
    lines += ["", "Candidate chain/bulk cell errors on tapes 1–3 are **%.6f, %.6f, %.6f**. The specific official worst-cell failure recurs in **%d/3** replays. Full-suite limits are met by the candidate in **%d/3** and the robust reference in **%d/3** supplementary tapes. All 72 replay episodes are valid; maximum candidate/reference CPU is **%.4f / %.4f seconds**." % (
        tapes["tape_1"]["candidate"]["chain_bulk_log_rmse"], tapes["tape_2"]["candidate"]["chain_bulk_log_rmse"],
        tapes["tape_3"]["candidate"]["chain_bulk_log_rmse"], repeat_failures, candidate_passes, reference_passes, cpu_candidate, cpu_reference), "",
        "## Interpretation and limits", "",
        "The official failure is a real, exactly reproducible error concentrated in a noisy, strongly anti-correlated bulk-rate contrast. The supplementary tapes test whether that particular failure repeats; they do not invalidate the original result or demonstrate a systematic population-wide bulk bias. Three noise tapes on fixed parameters are too few to infer a reliable failure probability, establish a general performance ranking, or guarantee future success.", "",
        "Seeds are paired by tape/episode, but adaptive configurations and query grouping differ between policies; their observations are not identical or shotwise coupled. Fisher inverse calculations condition on realized allocations and are asymptotic/local, so the standardized contrast is not a calibrated p-value. The trace confirms this particular posterior step helped, not that its approximation is exact. No controlled allocation ablation was run, so the role of the mean-risk objective and point-estimated late design is supported descriptively, not established as a sole cause.", "",
        "`manifest.json` records all sampling seeds before replay and hashes the frozen code, original result, participant, and evaluator. `analysis.json` contains channel-wise errors, pair contrasts/correlations, allocation vectors, traces and optimizer checks. `tape_*_report.json` contains the supplementary full-suite reports; `transcripts/` and `workspaces/` retain private evidence. No files outside `adversary/` were edited, and no fresh feedback or new generation was produced.", ""]
    (SIDE / "REPORT.md").write_text("\n".join(lines))
    summary = {"complete": True, "supplementary_only": True, "replaces_official_score": False,
               "official_failed_cell": "chain_hooks/bulk", "official_failure_reproduced_exactly": True,
               "candidate_supplementary_passes": candidate_passes, "reference_supplementary_passes": reference_passes,
               "candidate_chain_bulk_failures_in_three_replays": repeat_failures,
               "valid_replay_episodes": 72, "frozen_files_unchanged": True,
               "candidate_sha256": manifest["candidate_sha256"], "reference_sha256": manifest["reference_sha256"],
               "new_generation_created": False, "fresh_agent_feedback": False}
    (SIDE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    check_unchanged()


if __name__ == "__main__":
    main()
