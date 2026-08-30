import json
from pathlib import Path
import subprocess


SIDE = Path(__file__).resolve().parent


def main():
    summary = json.loads((SIDE / "summary.json").read_text())
    initial = json.loads((SIDE / "initial_official_result.json").read_text())
    replay = summary["official_replay"]
    relaxed = summary["relaxed_diagnostic"]
    clock_rows = []
    for line in (SIDE / "cpu_clocks.jsonl").read_text().splitlines():
        try:
            clock_rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    clock_summary = {}
    for run in ["official_replay", "relaxed_diagnostic"]:
        finite = [row for row in clock_rows if row["run"] == run and all(value is not None for value in row["process_clocks_seconds"].values())]
        if finite:
            clock_summary[run] = dict(last_observed=finite[-1], max_prof_seconds=max(row["process_clocks_seconds"]["prof"] for row in finite),
                max_sched_seconds=max(row["process_clocks_seconds"]["sched"] for row in finite),
                max_prof_minus_sched_seconds=max(row["process_clocks_seconds"]["prof"] - row["process_clocks_seconds"]["sched"] for row in finite))
    unchanged = all(summary[name] for name in ["unchanged_protected_tree", "unchanged_v1_snapshot", "unchanged_v2_snapshot"])
    findings = dict(source_and_frozen_assets_unchanged=unchanged, official_replays=1, relaxed_runs=1,
        initial_termination=initial["execution"], replay_termination=replay["execution"], clock_observations=clock_summary,
        initial_signal_sender_proven=False, watchdog_caused_termination=summary["driver_watchdog"] or replay["execution"]["watchdog_timeout"],
        reference="Linux 5.15 RLIMIT_CPU uses CPUCLOCK_PROF; observed SCHED/proc/wait4 values need not be identical. Raw CPU clocks were queried from the trusted host, not injected into the candidate.")
    if relaxed and relaxed["valid"]:
        result = relaxed["evaluation"]
        comparison = relaxed["original_numeric_gate_comparison"]
        failed_quality = [name for name, passed in comparison.items() if name not in ["runtime", "final_suite"] and not passed]
        resource_overrun = result["execution"]["cpu_seconds"] > 132
        findings.update(full_quality_recovered=True, pooled=result["pooled"], families=result["families"], splits=result["splits"],
            relaxed_execution=result["execution"], failed_original_quality_gates=failed_quality,
            completed_run_measured_cpu_overrun=resource_overrun, cpu_overrun_seconds=result["execution"]["cpu_seconds"] - 132,
            original_numeric_gate_comparison=comparison, nonqualifying_diagnostic=True,
            original_target_conclusion="NOT_QUALIFIED: original replay is invalid; completed diagnostic fails original numerical gates" if not all(comparison.values()) else
                "NOT_OFFICIALLY_QUALIFIED: relaxed diagnostic meets numerical gates but original replay remains invalid")
        family_text = "; ".join(f"{name}: {entry['baseline_failures']} -> {entry['candidate_failures']}" for name, entry in result["families"].items())
        details = f"""- Completed relaxed run: **{result['pooled']['baseline_failures']} -> {result['pooled']['candidate_failures']} failures / {result['pooled']['shots']} shots**, reduction {100 * result['core_score']:.6f}%.
- Holdout reduction: {100 * result['splits']['holdout']['error_reduction']:.6f}%. Worst-family reduction: {100 * result['worst_family_score']:.6f}%.
- Family failures: {family_text}.
- Paired absolute 95% interval: {result['pooled']['paired_absolute_ci95']}.
- Full-run resource: **{result['execution']['cpu_seconds']:.6f} CPU seconds**, {result['execution']['wall_seconds']:.3f} wall seconds, {result['execution']['max_rss_kib']} KiB peak RSS; watchdog {result['execution']['watchdog_timeout']}.
- Compared with the original 132-second numerical cap: {result['execution']['cpu_seconds'] - 132:+.6f} seconds. Confirmed completed-run numerical overrun: {resource_overrun}.
- Failed original quality gates: {', '.join(failed_quality) if failed_quality else 'none'}.

Conclusion: **{findings['original_target_conclusion']}**. The relaxed run is nonqualifying and does not replace the official result.
"""
    else:
        findings.update(full_quality_recovered=False, original_target_conclusion="NOT_QUALIFIED; full quality remains unavailable", nonqualifying_diagnostic=True)
        details = "The bounded relaxed run did not produce a complete valid quality report. Its termination cannot be converted into an invented quality score.\n"
    (SIDE / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    clock = clock_summary.get("official_replay", {}).get("last_observed", {}).get("process_clocks_seconds")
    text = f"""# Frozen v2 diagnostic conclusion

Exactly one unchanged official replay and one relaxed-CPU isolated diagnostic were run. No source optimization, fresh agent, generation change or root/status edit was made. Protected tree plus both frozen submissions unchanged: **{unchanged}**.

## Termination evidence

- Initial official result: exit {initial['execution']['returncode']}, {initial['execution']['cpu_seconds']:.6f} measured CPU seconds, no worker log, no watchdog.
- Unchanged official replay: exit {replay['execution']['returncode']}, **{replay['execution']['cpu_seconds']:.6f} measured CPU seconds**, {replay['execution']['wall_seconds']:.3f} wall seconds, no watchdog.
- Replay worker's observed soft/hard CPU limit remained 133 seconds; it had one thread. The last live Linux CPU-clock sample was {clock}.
- This reproduces the near-limit kill. The replay's measured CPU exceeds the original 132-second score cap, independently of the initial sub-cap measurement. Linux 5.15's PROF-based hard limit and the other accounting observations are distinct; the initial 128.805497-second result alone was not proof of a numerical overrun. The exact signal sender in the initial run was not traced.

## Full quality and original targets

{details}

## Scope and raw evidence

Mandatory bwrap isolation, seccomp, private PID/network namespaces, data, model parameters, case order, native binary and all quality gates were retained. Only the private in-memory diagnostic ceiling changed to 180 CPU seconds, giving worker RLIMIT_CPU 181. The 900-second worker wall watchdog was unchanged. No driver watchdog fired: {not summary['driver_watchdog']}.

Raw scores: `official_replay.json` and `relaxed_diagnostic.json` (nested `evaluation` contains the complete paired scores). Predictions and the diagnostic worker response are in `relaxed_worker_outputs/`. Process and CPU-clock observations are in `*_processes.jsonl` and `cpu_clocks.jsonl`. Full source/freeze hashes are in `integrity_before.json` and `integrity_after.json`.

The frozen development log reports 130.12430454 seconds of decode/construction CPU, but its bench excludes imports and uses development data, not this official hidden replay. It is context, not a qualifying measurement.

All changed files are confined to `concept_1/adversary/second_attempt_diagnostic/`. The original `v_2_result.json`, frozen targets and status remain untouched. Main owns adjudication; this diagnostic is not a promotion or a retargeting.
"""
    path = SIDE / "DIAGNOSIS.md"
    if path.exists():
        raise RuntimeError("Do not overwrite a completed diagnosis")
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)
    print(json.dumps({name: value for name, value in findings.items() if name not in ["pooled", "families", "splits", "clock_observations"]}, indent=2))


if __name__ == "__main__":
    main()
