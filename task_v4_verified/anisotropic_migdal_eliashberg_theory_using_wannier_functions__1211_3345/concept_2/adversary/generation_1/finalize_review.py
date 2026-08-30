import hashlib
import json
import shutil
from pathlib import Path

from prepare_pending import PENDING, json_write, protected_state, text_patch


def main():
    manifest = json.loads((PENDING / "package_manifest.json").read_text())
    assert protected_state() == manifest["protected_active_before"]
    completed = []
    for filename in sorted((PENDING / "champion_replays").glob("*/result.json")):
        result = json.loads(filename.read_text())
        if result.get("admissible"):
            completed.append({"name": filename.parent.name, "score": result["score"], "valid": result["valid"]})
    large = PENDING / "large_patch_probe"
    candidate = large / "candidate_n24"
    private = json.loads((candidate / "evaluation.json").read_text())
    baseline = json.loads((candidate / "baseline_evaluation.json").read_text())
    output = PENDING / "champion_replays/large_n24__compressed_spectrum/output"
    artifacts = list(output.glob("*.npz"))
    assert not artifacts, "A new artifact exists: audit it before summarizing this stopped run."
    trace = PENDING / "large_patch_replay.log"
    assert "JSONDecodeError" in trace.read_text()
    control_result = PENDING / "champion_replays/dimension_adapter_original_control/result.json"
    stopped = large / "stopped_run"
    stopped.mkdir(exist_ok=True)
    for source, destination in ((trace, "controller_traceback.log"),
                                (output / "coarse.log", "coarse.log"),
                                (output / "coarse.resource.json", "empty_resource_record.json")):
        shutil.copy2(source, stopped / destination)
    large_summary = {
        "status": "inconclusive_bounded_replay",
        "private_score": private["score"], "target_ratio": private["target_ratio"],
        "baseline_score": baseline["score"],
        "known_private_valid_witness": True,
        "dimension_adapter_original_control_score": json.loads(control_result.read_text())["score"],
        "coarse_positive_count": 48, "requested_random_restarts": 24,
        "logged_minimum_calls_at_least": 225,
        "last_logged_minimum_tc_kelvin": 80.91891420424972,
        "candidate_artifact_emitted": False,
        "champion_passed": False,
        "champion_failure_established": False,
        "stage_wall_limit_seconds": 600,
        "file_timestamp_elapsed_control_to_traceback_seconds": trace.stat().st_mtime - control_result.stat().st_mtime,
        "cpu_seconds": None, "peak_rss_kib": None,
        "resource_measurement_reason": "The terminated stage left an empty GNU-time record. Its old reader then raised JSONDecodeError; exact search CPU/RSS were not recovered. Unknown is not zero.",
        "reason": "The bounded coarse SLSQP run reached its 600-second stage limit without emitting a pair, then resource-log parsing failed. Neither is a scientific, optimization, admissibility, or one-hour resource failure. No retry or additional search is scheduled.",
        "resource_reader_hardened_without_rerun": True,
        "new_fresh_model_launched": False,
    }
    json_write(large / "replay_summary.json", large_summary)
    mixing = json.loads((PENDING / "mixing_sanity_probe/summary.json").read_text())
    review = {
        "status": "bounded_review_complete_no_promotion_recommended",
        "active_package_unchanged": protected_state() == manifest["protected_active_before"],
        "new_fresh_launches": 0,
        "completed_configuration_replays": len(completed),
        "completed_passing_replays": sum(record["valid"] for record in completed),
        "completed_admissible_failing_replays": sum(not record["valid"] for record in completed),
        "completed_replays": completed,
        "selected_n8_private_score": 1.094955838159416,
        "selected_n8_stronger_champion_oracle_score": 1.0877026333364312,
        "selected_n8_target_fixed_before_replay": 1.09,
        "selected_n8_actual_method_gap_is_genuine": True,
        "selected_n8_shortcut": mixing,
        "selected_n8_recommended_as_hard_ratchet": False,
        "large_patch_probe": large_summary,
        "moment_or_isospectral_constraints_added": False,
        "moment_or_isospectral_witness_verified": False,
        "remaining_scheduled_search_seconds": 0,
        "reason": "The actual n8 method gap is defeated by a simple new interpolation extension. The larger instance has a verified witness but an inconclusive bounded champion run. Neither currently justifies claiming a difficult surviving ratchet; do not raise a threshold to evade the shortcut.",
    }
    json_write(PENDING / "REVIEW_SUMMARY.json", review)
    text_patch(PENDING / "REVIEW_SUMMARY.md", """# Bounded ratchet review: no promotion recommended

Both original fresh attempts are solved. The higher unrounded v2 result, 1.1245411788778297, is archived with its frozen submission, evaluations, and manifests. Active participant/evaluator/status files remain unchanged; no new fresh model or promotion occurred.

## Actual search evidence

- 23 completed configuration replays, including two n=8 controls: all produced admissible artifacts; 15 pass and eight fail. The two ordinary retained pool alternatives pass at 1.1221797657498267 and 1.1273501422691823. Each control reproduces 1.1245411788778297.
- For `middle_cross_45`, the private witness is 1.094955838159416 at a pre-fixed target 1.09. Every single-family configuration of the actual champion fails; even recombining all 16 output endpoints reaches only 1.0877026333364312. This is a genuine method-level minimax gap, not a path, label, shape, or stale-threshold failure.
- However, a new two-parameter interpolation of champion endpoints passes at 1.094290457685765 in 8.621409096999999 CPU seconds, including its full independent audit. The validated n=8 draft is therefore not recommended as evidence of difficult search. Its target is not raised after this result. The `middle_cross_35` oracle miss is much narrower and is not substituted to manufacture a threshold gap.

## Larger private design

`large_patch_probe/candidate_n24/` contains a reproducible, nonidentical three-band instance, feasible reference, private pair, baseline, independent audits, and a complete frozen artifact checker. All three bands are different, all interband couplings are positive and reciprocal, and the modes do not commute. Integrated total couplings range from 0.22144179345340279 to 2.774296312611569; the equality-constrained space has 504 free coordinates per kernel.

The exact checker confirms private score **1.1219300515770714** at target **1.11**, fixed before replay. Baseline is admissible, score **1.0**, not valid. The signed-frequency matrices are separately assembled for each family, and the regular-row no-go control passes. The private witness checker takes 7.895 CPU seconds with 726096 KiB process-lifetime peak RSS on this run.

The dimension/path-only champion adapter reproduces the n=8 control exactly. On n=24, the coarse SLSQP run logs at least 225 objective calls and reaches a low-endpoint temperature of 80.91891420424972 K, but emits no pair before the **600-second stage cap**. Its empty GNU-time file then triggers a bookkeeping JSON error. The resource reader is hardened without repeating the search; raw logs are preserved in `large_patch_probe/stopped_run/`. Exact search CPU/RSS are unknown, not zero. This is **inconclusive**, not an optimization gap, invalid-input failure, or proof of failure under a one-hour budget. The visible weak-band structure may also allow a faster decomposed search.

## Optional stronger invariants

No Frobenius-moment or isospectral constraint is added, and no witness for that variant is claimed. Such restrictions change the feasible search problem; an old LP step that ignores them cannot count as a challenger failure. A future proposal must first produce a distinct-Tc pair satisfying all strengthened invariants and then test an invariant-aware adaptation of the search. This review does not spend another budget on an unverified construction.

## Available draft and reporting

`participant/`, `input/FORMAT.md`, and `evaluator/evaluate.py` remain a fully validated but **not recommended** n=8 draft for parent inspection. `validation/summary.json` records the exact private/baseline/oracle checks and 17 hostile-artifact/constraint rejection probes. `reporting_only/REPORTING_REGRESSION.json` confirms the reason/core/worst/resource reporting addition preserves the original numerical scores and verdicts. Archived original contracts and outputs are not rewritten.

No search remains scheduled. Only the parent may decide to resume investigation, promote a proposal, or launch a fresh model. The current evidence does not justify claiming that a difficult ratchet survived.
""")
    status = json.loads((PENDING / "status.json").read_text())
    status.update({
        "review_status": review["status"], "recommended_for_promotion": False,
        "ready_for_new_fresh_attempts": False, "remaining_scheduled_search_seconds": 0,
        "large_patch_probe": large_summary, "review_summary": "REVIEW_SUMMARY.md",
        "reason": review["reason"],
    })
    json_write(PENDING / "status.json", status)
    assert protected_state() == manifest["protected_active_before"]
    print(json.dumps({"completed_replays": len(completed), "passes": review["completed_passing_replays"],
                      "admissible_failures": review["completed_admissible_failing_replays"],
                      "large_replay": large_summary["status"], "recommended_for_promotion": False,
                      "active_unchanged": True, "remaining_search_seconds": 0}), flush=True)


if __name__ == "__main__":
    main()
