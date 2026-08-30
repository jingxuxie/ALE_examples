import calendar
import hashlib
import time

from sweep import ROOT, ARCHIVE, read_json, write_json, summarize, select_candidate


candidate = "n8192_b128_w18_pairs"
confirmation = read_json(ROOT / "confirmation_results.json")
sensitivity = read_json(ROOT / "sensitivity_results.json")
assert len(confirmation["results"]) == 11
assert len(sensitivity["results"]) == 4
assert all(not result["solved"] and result["error"] is None for result in confirmation["results"] + sensitivity["results"])
summarize()
select_candidate(candidate)
results = read_json(ROOT / "search_results.json")
construction = read_json(ROOT / "candidate_construction.json")
candidate_results = [result for result in results["runs"] if result["case"] == candidate]
assert len(candidate_results) == 20
assert all(not result["solved"] and result["error"] is None for result in candidate_results)
assert all(case["run_errors"] == 0 for case in results["cases"])
source_integrity = {}
for name, metadata in read_json(ROOT / "adaptations.json").items():
    suffix = ".py" if name == "sat_search" else ".cpp"
    digest = hashlib.sha256((ARCHIVE / "submission" / (name + suffix)).read_bytes()).hexdigest()
    assert digest == metadata["archived_sha256"]
    source_integrity[name] = digest
for name in ("evaluate.py", "reproduce.py"):
    assert (ROOT / "candidate_validation/evaluator" / name).read_bytes() == (ARCHIVE / "evaluator" / name).read_bytes()
    source_integrity[name] = hashlib.sha256((ARCHIVE / "evaluator" / name).read_bytes()).hexdigest()
write_json(ROOT / "archive_integrity.json", source_integrity)
clusters = [
    {"name": "calibrated_original", "cases": ["archive_control"], "observation": "Archived grouped v3/v4 and adapted counterparts all recover the identical 14-bit support. Full BEST traces match. BP's 20-update BEST trace matches over the 12-second calibration.", "interpretation": "Dimension adaptation preserves the original search, rather than invalidating its static witness or disabling its working code."},
    {"name": "weight_pressure", "cases": ["n2048_b32_w14_pairs", "n2048_b32_w16_pairs", "n2048_b32_w18_pairs"], "observation": "Three of five probes solve the new weight-14 case; none solve weight-16 or weight-18 cases within 30 seconds.", "interpretation": "Consistent with a larger sparse support search burden; instances have different random seeds, so this is not an isolated causal estimate of weight."},
    {"name": "wide_pair_spread", "cases": [f"n{size}_b{block}_w{weight}_pairs" for size, block in ((4096, 64), (8192, 128)) for weight in (14, 16, 18)], "observation": "All six wider, 64-root pair-spread cases survive the five-method 30-second portfolio. The selected weight-18 case additionally survives eleven 240-second and four 120-second configurations.", "interpretation": "All have 384 parity rows and exact rank 379: difficulty is not caused by an unadapted dimension or an increased row count. Wider roots enlarge the search universe and reduce the number of complete roots that fit in an information set."},
    {"name": "concentrated_spread_positive_controls", "cases": ["n4096_b64_w18_quartets", "n8192_b128_w18_quartets"], "observation": "Standard BP solves both weight-18 quartet-spread controls in about 2.28 and 1.05 seconds respectively, with independent activated-witness certificates.", "interpretation": "The same wide dimensions are not inherently unsupported. Concentrating the core in five roots rather than nine creates stronger local parity overlap; actual parity-constraint structure matters."},
    {"name": "narrow_block_positive_control", "cases": ["n2048_b16_w18_pairs"], "observation": "Four grouped variants solve weight 18 within 30 seconds; fastest is about 0.43 seconds.", "interpretation": "Higher redundancy and narrower blocks can make information-set localization easier. Increasing the number of checks is not automatically a hardness ratchet."},
    {"name": "other_valid_geometry_survivors", "cases": ["n2048_b64_w18_pairs", "n4096_b32_w18_pairs", "n8192_b64_w18_pairs", "n4096_mixed_w18_pairs"], "observation": "Each survives its five 30-second probes without process or validation errors, including a mixed geometry with partial terminal blocks.", "interpretation": "These are retained alternatives, not proven harder than the selected candidate; only the selected case receives long confirmation."},
]
write_json(ROOT / "root_cause_clusters.json", {"clusters": clusters, "claim_scope": "Empirical failures within the recorded seeds and time caps only; neither impossibility nor one-hour agent hardness is established."})
adaptation_details = {
    "shared": [
        "Six passes are retained. Public block incidence is regenerated from every deployment, not copied from the original labels.",
        "Per-geometry geometry.hpp supplies n, check count, ceiling check-bitset length, block-size maximum, per-pass root counts and offsets, and exact GF(2) matrix rank calculated from public deployment rows.",
        "The constants 2048/384/379 and packed six-word syndrome dimensions are replaced mechanically; algorithmic acceptance remains a zero-syndrome core of weight 8 through 18.",
        "Compilation uses g++ -O3 -march=native -std=c++17; all commands, binaries, geometry headers and unified source diffs are retained.",
        "Progress logging changes from every 100 to every 10 trials and adds CONFIG/END records, without changing candidate generation.",
    ],
    "grouped_isd": [
        "Matrix row words use ceil(n/64). Groups and their membership lengths are geometry-sized vectors; mixed-block prefix lengths are the sum of actual group lengths.",
        "Full Gaussian elimination, singleton candidates, within-root pairs, four-position pair collisions, twenty hash bits, duplicate rejection, and full original-row syndrome verification remain unchanged.",
        "The final submitted source uses initial incumbent 20. A second build uses 1000, reproducing the v3 BEST trace exactly on the archived control.",
        "The default tested retained-root count is floor(0.84*rank/block_size), independently for each grouping pass: 9 for 2048/32, 4 for 4096/64, and 2 for 8192/128, all at rank 379.",
        "Selected-case confirmation additionally tests zero/global shuffling, two and three retained roots, all six grouping passes across runs, and multiple recorded seeds. No stale ten-root assumption is imposed on 128-bit blocks.",
    ],
    "bp_osd": [
        "Check adjacency, message offsets and padded message capacity scale to the maximum public block size; iteration loops use actual per-check sizes, supporting partial final blocks.",
        "Impulses, sorting by shared parity checks, 100 min-sum iterations, normalization schedule, priors, OSD checkpoints 19/49/99, OSD depth 50 and weight bounds remain unchanged.",
        "A public CLI seed is added; default seed 345778 preserves the original trajectory. Confirmation also uses 271828.",
        "A separate, explicitly labeled sensitivity build shuffles the initial impulse order with a public seed. It does not replace the standard champion method or receive privileged core information.",
    ],
    "sat": [
        "The archived libz3 SAT/XOR/cardinality encoding is retained, with deployment and output paths redirected to isolated private run directories.",
        "The previously parsed-but-unused seed is actually set through sat.random_seed. Model support export is added for independent witness checking; bounds remain 8 through 18.",
    ],
    "witness_validation": [
        "Every planted case is checked by both unchanged archived replay implementations for earliest and shortest priorities.",
        "Every successful solver core is activated with six bits from empty first-pass roots, exactly as in the champion finish.py logic, and independently replayed.",
        "The final selected witness is also checked by byte-identical archived evaluate.py and reproduce.py copied into candidate_validation; only their private deployment and manifest differ.",
    ],
}
write_json(ROOT / "adaptation_details.json", adaptation_details)
total_cpu = sum(result["user_cpu_seconds"] + result["system_cpu_seconds"] for result in candidate_results)
confirmation_cpu = sum(result["user_cpu_seconds"] + result["system_cpu_seconds"] for result in confirmation["results"])
method_stats = {}
for result in candidate_results:
    stats = method_stats.setdefault(result["method"], {"runs": 0, "successes": 0, "wall_seconds": 0.0, "cpu_seconds": 0.0, "best_weight": None})
    stats["runs"] += 1
    stats["successes"] += int(result["solved"])
    stats["wall_seconds"] += result["wall_seconds"]
    stats["cpu_seconds"] += result["user_cpu_seconds"] + result["system_cpu_seconds"]
    if result["best_weight"] is not None:
        stats["best_weight"] = min(stats["best_weight"], result["best_weight"]) if stats["best_weight"] is not None else result["best_weight"]
first_launch = min(read_json(path)["utc_start"] for path in (ROOT / "runs").glob("*/*/*/launch.json"))
search_started = calendar.timegm(time.strptime(first_launch, "%Y-%m-%dT%H:%M:%SZ"))
ready = {
    "status": "ready",
    "ready_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "candidate_case": candidate,
    "selection_reason": "Calibrated wide-block, pair-spread survivor with positive private certificate and no success across all selected within-cap portfolio, long-confirmation and order-sensitivity runs; not asserted globally hardest.",
    "deployment": str(ROOT / "deployment.json"),
    "privileged_witness": str(ROOT / "privileged_witness.json"),
    "manifest": str(ROOT / "manifest.json"),
    "deployment_sha256": construction["deployment_sha256"],
    "n": 8192,
    "passes": 6,
    "block_sizes": [128] * 6,
    "roots_per_pass": 64,
    "parity_rows": 384,
    "gf2_rank": 379,
    "core_weight": 18,
    "core_occupied_roots_per_pass": 9,
    "activation_weight": 6,
    "witness_weight": 24,
    "private_certificate": {"passed": True, "earliest": {"initial_odd": 6, "corrected": 6, "residual": 18}, "shortest": {"initial_odd": 6, "corrected": 6, "residual": 18}, "independent_core_score": 1.0},
    "sweep_cases": len(results["cases"]),
    "total_completed_runs": len(results["runs"]),
    "selected_case_runs": len(candidate_results),
    "selected_case_successes": 0,
    "selected_case_search_cpu_seconds": total_cpu,
    "long_confirmation_runs": 11,
    "long_confirmation_cap_seconds": 240,
    "long_confirmation_cpu_seconds": confirmation_cpu,
    "sensitivity_runs": 4,
    "sensitivity_cap_seconds": 120,
    "method_statistics": method_stats,
    "search_span_seconds_to_ready": time.time() - search_started,
    "scope": "Within-cap failures only. Two independent cold ultima-alpha trials are for main to launch; this worker launches none and makes no one-hour-hardness claim.",
    "ownership": "Only concept_2/adversary/ratchet_1 is created or modified; frozen participant/evaluator and attempt directories are untouched.",
    "search_results": str(ROOT / "search_results.json"),
    "root_cause_clusters": str(ROOT / "root_cause_clusters.json"),
    "exact_adaptations": str(ROOT / "adaptation_details.json"),
}
report = ["# Champion-ratchet private handoff", "", f"Candidate: `{candidate}`. Status: ready for main's generation switch and two independent cold trials.", "", "## Validity", "", "Six fixed valid permutations, n=8192, block size 128, 64 roots/pass, 384 rows, GF(2) rank 379. The planted 18-bit even-parity core occupies nine roots per pass; six disjoint first-pass activation bits give weight 24. Both independent priority replays report initial_odd=6, corrected=6, residual=18. The byte-identical archived evaluator gives score 1.0.", "", "## Measured search results", "", f"All {len(candidate_results)} selected-case runs fail within their recorded caps: five 30-second probes, eleven 240-second confirmations, and four 120-second sensitivity runs. They consume {total_cpu:.1f} aggregate CPU seconds. There are no solver process/validation errors. This is not a proof of absence or one-hour agent hardness.", "", "| Case | Successes/runs | Best observed valid parity-core weight | Fastest success (s) |", "|---|---:|---:|---:|"]
for case in results["cases"]:
    fastest = f"{case['fastest_success_seconds']:.3f}" if case["fastest_success_seconds"] is not None else "—"
    best = str(case["best_weight"]) if case["best_weight"] is not None else "—"
    report.append(f"| {case['case']} | {case['successes']}/{case['runs']} | {best} | {fastest} |")
report.extend(["", "Rows include calibration runs on the archive control; other cases receive five probes unless selected for confirmation. A recorded parity core heavier than 18 is not a valid activated witness. Different instances use distinct construction seeds; cross-case comparisons are suggestive rather than isolated causal estimates.", "", "## Why this is a genuine search challenge", "", "Archived and adapted grouped solvers recover the same original core in 2–3 seconds with identical complete BEST traces. Standard BP also has an identical 20-update calibration trace. On the same 8192/128 geometry, the quartet-spread 18-bit control solves with BP in 1.05 seconds. Thus dimension support is demonstrably working, and changing labels of an old witness is not the tested failure mode.", "", "For the selected pair-spread core, nine roots carry two bits each. A rank-379 information set covers fewer than three complete 128-bit roots; grouping is scaled to two, with additional global/zero and three-root controls across passes. The grouped decoder's low-order nonpivot enumeration and BP/OSD's sparse-impulse guidance do not find a <=18 parity core under these tested budgets. The randomized-order BP sensitivity avoids relying solely on the champion's deterministic high-overlap impulse ordering. These are mechanism-based interpretations, not complexity lower bounds.", "", "## Artifacts and exact adaptations", "", "- `deployment.json`, `privileged_witness.json`, `manifest.json`: main's candidate deployment, private certificate input and integrity manifest.", "- `ready.json`, `selection.json`, `independent_score.json`, `validation.json`: ready metadata and positive checks.", "- `search_results.json`, phase plans/results, and `runs/`: all seeds, wall/CPU caps and use, commands, stdout/stderr, generated cores, successful witnesses and failures.", "- `cases/`: all seventeen deployments and private constructions, including successful easy controls.", "- `root_cause_clusters.json`, `adaptation_details.json`, `sources/*.patch`, `bin/*/geometry.hpp`, `bin/*/compile.json`: empirical clusters, exact adaptation descriptions, actual unified diffs and build commands.", "- `trajectory_calibration.json`, `archive_integrity.json`: original/adapted trace agreement and unchanged archive source hashes.", "", "## Reproduction", "", "Run from this directory, using Python 3 and g++ with libz3 available:", "", "```sh", "python3 -B sweep.py prepare", "python3 -B sweep.py sweep --seconds 30 --workers 16", "python3 -B sweep.py confirmation --case n8192_b128_w18_pairs --seconds 240 --workers 11", "python3 -B sensitivity.py --seconds 120", "python3 -B finalize.py", "```", "", "Existing run result files are reused, not silently overwritten. To collect a new replicate, use a new phase/label and recorded seed via run_job. Preparation regenerates deterministic case data and binaries only inside this worker directory. Main owns the real generation switch and cold agents; this worker does neither."])
(ROOT / "findings.md").write_text("\n".join(report) + "\n")
write_json(ROOT / "ready.json", ready)
print({"status": "ready", "candidate": candidate, "selected_runs": len(candidate_results), "cpu_seconds": total_cpu})
