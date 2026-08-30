import datetime
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percent(value):
    return "%.6f%%" % (100 * value)


def main():
    results = []
    for path in sorted((HERE / "results").glob("*.json")):
        record = json.loads(path.read_text())
        if "spec" in record and "valid" in record:
            results.append(record)
    by_name = {record["spec"]["name"]: record for record in results}
    pair = by_name["fresh_pair_actual"]
    actual = by_name["candidate_actual"]
    oracle = json.loads((HERE / "summary.json").read_text())["oracle_union"]
    assert pair["valid"] and actual["valid"]
    fields = ["name", "valid", "core", "worst_family", "cost", "wall_s", "cpu_s", "peak_AS_KiB", "peak_RSS_KiB", "timeout", "config"]
    rows = ["\t".join(fields)]
    for record in results:
        values = [record["spec"]["name"], str(record["valid"]), str(record.get("core_score", "")), str(record.get("worst_family_score", "")), str(record.get("cost", "")), "%.6f" % record["elapsed_seconds"], "%.6f" % record["cpu_seconds"], str(record["peak_sampled_as_kib"]), str(record["peak_sampled_rss_kib"]), str(record["timed_out"]), json.dumps(record["spec"], sort_keys=True, separators=(",", ":"))]
        rows.append("\t".join(values))
    (HERE / "VARIANTS.tsv").write_text("\n".join(rows) + "\n")
    manifest = {
        "created_at": datetime.datetime.now().astimezone().isoformat(),
        "fixed_targets": {"core": 0.20, "worst_family": 0.08, "wall_seconds": 120, "cpu_count": 1, "aggregate_AS_bytes": 1024 ** 3},
        "candidate_files": {path.name: {"sha256": digest(path), "bytes": path.stat().st_size} for path in sorted((HERE / "candidate").iterdir()) if path.is_file()},
        "fresh_pair_files": {path.name: {"sha256": digest(path), "bytes": path.stat().st_size} for path in sorted((HERE / "fresh_pair").iterdir()) if path.is_file()},
        "reviewed_originals": {},
        "hidden_sha256": digest(ROOT / "evaluator" / "hidden" / "cases.json"),
        "baseline_source_sha256": digest(ROOT / "participant" / "baseline" / "solve.py"),
        "public_model_sha256": digest(ROOT / "participant" / "workspace" / "model.py"),
        "runtime_validation": "Direct authoring test, not the official isolated evaluator",
    }
    for version, filename in [("v_1", "engine.cpp"), ("v_2", "planner.cpp")]:
        original = ROOT / "attempts" / version / filename
        copied = HERE / "sources" / version.replace("_", "") / filename
        manifest["reviewed_originals"][str(original.relative_to(ROOT))] = {"sha256": digest(original), "copied_source_identical": original.read_bytes() == copied.read_bytes()}
    assert manifest["baseline_source_sha256"] == digest(HERE / "candidate" / "baseline.py")
    (HERE / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    achieved = actual["cost_targets_met"] and actual["elapsed_seconds"] <= 120 and not actual.get("resource_violation")
    lines = [
        "# Privileged fresh-A refinement evidence",
        "",
        "Generated " + manifest["created_at"] + ". Writes are confined to `concept_1/adversary/refine_fresh/`. No fresh agents were launched; original attempts, participant, evaluator, hidden cases, and status were not edited.",
        "",
        "## Fixed target and conclusion",
        "",
        "Generation-1 target is unchanged: overall `1 - geometric_mean(cost / baseline_cost) >= 0.20`, every family >= 0.08, all 30 hidden instances within 120 seconds on one CPU and 1 GiB aggregate address space. Hidden baseline total remains 345617.",
        "",
        ("**Direct measured target achieved; official isolated validation still required.**" if achieved else "**No passing planner found. Achievability remains unknown, not disproved.**"),
        "",
        "The resource-tested generic bundle scores **%s core, %s worst family**, total cost **%d**, versus baseline **%d**; wall **%.3f s**, CPU **%.3f s**, sampled aggregate AS **%.2f MiB**, sampled aggregate RSS **%.2f MiB**. All 30 answers pass the exact public checker." % (percent(actual["core_score"]), percent(actual["worst_family_score"]), actual["cost"], actual["baseline_cost"], actual["elapsed_seconds"], actual["cpu_seconds"], actual["peak_sampled_as_kib"] / 1024, actual["peak_sampled_rss_kib"] / 1024),
        "",
        "## Actual original-pair portfolio",
        "",
        "`fresh_pair/solve.py` actually reruns both independently rebuilt fresh planners on every supplied instance, verifies each plan, and selects the lower cost, with baseline fallback. It is not an offline per-case schedule selection.",
        "",
        "Measured **%s core, %s worst family**, cost **%d**, wall **%.3f s**, CPU **%.3f s**, aggregate AS **%.2f MiB**. Complementarity is real but insufficient for the fixed 20%% overall target." % (percent(pair["core_score"]), percent(pair["worst_family_score"]), pair["cost"], pair["elapsed_seconds"], pair["cpu_seconds"], pair["peak_sampled_as_kib"] / 1024),
        "",
        "The main-reported official fresh scores were v1 core 0.1728140863 / worst 0.0917104841 / runtime 19.47 s and v2 core 0.1798711714 / worst 0.0932101553 / runtime 13.28 s. Those are main-provided context, not results of this harness. Time-bounded search can produce slightly different schedules under host contention.",
        "",
        "## Search and cost-only evidence",
        "",
        "Reviewed both fresh Python and C++ sources before execution; copied only relevant sources and rebuilt our own binaries. Searches tested original modes, larger forward/reverse beams, separate widths and horizons, memoized pair roots, optional reverse merges, forward-guided reverse estimates, triple-root merging, graph search, rollout search, reverse heuristic scales, and generic runtime portfolios. All configurations and outcomes, including timeouts, are in `VARIANTS.tsv` and `results/*.json`.",
        "",
        "The exact-checked per-instance oracle union of completed valid experiments reaches **%s core, %s worst family**, cost **%d**. This is cost potential only: it combines saved experimental schedules and is not a runtime-compliant submission or hidden-case lookup permitted in a submission. Even this union falls below 20%%." % (percent(oracle["core_score"]), percent(oracle["worst_family_score"]), oracle["cost"]),
        "",
        "Native modes with no internal deadline may time out; those failures are retained, not assigned scores or treated as passing potential. Concurrent offline tuning ran on separate pinned CPUs. High wall/CPU ratios reflect host contention; measured timeouts do not prove a configuration intrinsically needs that much CPU. Only the explicitly recorded real wrapper executions establish measured portfolio resources.",
        "",
        "## Portable bundle and reproducibility",
        "",
        "Copy only `candidate/` for submission. `solve.py` uses `/task/workspace/model.py`, bundles the unchanged public baseline, reads generic configurations, launches sequential native searches, and selects minimum exact-checked cost. No IDs, family labels, hidden inputs, baseline-cost table, or saved schedules enter this bundle. Its global planner deadline is 109 seconds with baseline fallback. The source is included beside its rebuilt binary. `candidate/README.md` gives the rebuild and launch commands; `bundle_manifest.json` hashes every packaged file.",
        "",
        "Generation-only hidden access was used to tune generic configurations and measure scores. The surrounding directory contains privileged cases/results and must not be copied into a participant environment.",
        "",
        "Reproduce locally with `PYTHONDONTWRITEBYTECODE=1 python3 measure.py candidate_specs.json` from this directory. CPU 198 is the authoring host affinity used in that spec; select an available CPU if replaying elsewhere. `pair_specs.json` runs the original-pair bundle. `summarize.py` rechecks stored valid plans against the exact checker. `choose_portfolio.py` performs offline configuration selection; that selection is not itself runtime proof.",
        "",
        "## Resource and audit scope",
        "",
        "The direct wrapper tests pin the process tree to one CPU, apply an inherited 1 GiB RLIMIT_AS, and sample summed child/parent virtual and resident memory plus affinity at 25 ms intervals. The monitor kills on expanded affinity, aggregate-AS overflow, or 120-second wall timeout. Startup of the outer tool namespace is excluded; Python parsing, baseline planning, child launches, and candidate verification are included. CPU totals include waited-for descendants. Sampling is not an official isolation certificate; the hardened evaluator remains authoritative.",
        "",
        "This follow-up did not modify or rerun the root evaluator. The main-reported one-CPU/aggregate-AS hardening is respected; historical audit observations from the preceding sidecar are not reasserted as current vulnerabilities. No new evaluator flaw was established in this refinement. All scored generated answers pass exact action legality, stale-version, pinned-home, and memory checks implemented by the current public checker; that statement is not a new independent malformed-input audit or Fourier semantic proof.",
        "",
        "## Exact measured variants",
        "",
        "| Variant | Valid | Core % | Worst % | Cost | Wall s | CPU s | AS MiB |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in results:
        lines.append("| %s | %s | %s | %s | %s | %.3f | %.3f | %.2f |" % (record["spec"]["name"], "yes" if record["valid"] else "no", "%.6f" % (100 * record["core_score"]) if record["valid"] else "—", "%.6f" % (100 * record["worst_family_score"]) if record["valid"] else "—", str(record.get("cost", "—")), record["elapsed_seconds"], record["cpu_seconds"], record["peak_sampled_as_kib"] / 1024))
    lines.extend(["", "## Hidden-set family scores for actual selected bundle", ""])
    for family, score in actual["family_scores"].items():
        lines.append("- `%s`: %s" % (family, percent(score)))
    public_path = HERE / "public_validation.json"
    if public_path.exists():
        public = json.loads(public_path.read_text())
        lines.extend(["", "## Public examples", "", "The same portable candidate passed %d/%d public example checks in %.3f seconds wall. Evidence: `public_validation.json`; this is an exact-checker smoke test, not an additional official resource certification." % (public["valid_count"], public["count"], public["elapsed_seconds"])])
    lines.extend(["", "Protected hidden-case SHA-256: `" + manifest["hidden_sha256"] + "`.", ""])
    (HERE / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"report": str(HERE / "REPORT.md"), "variants": len(results), "valid_variants": sum(record["valid"] for record in results), "actual_core": actual["core_score"], "actual_worst": actual["worst_family_score"], "actual_wall": actual["elapsed_seconds"], "actual_cpu": actual["cpu_seconds"], "target_met": achieved}, indent=2))


if __name__ == "__main__":
    main()
