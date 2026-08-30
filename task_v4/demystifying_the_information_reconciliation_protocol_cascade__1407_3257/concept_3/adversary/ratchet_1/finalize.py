"""Validate and summarize private generation evidence into a ready handoff."""

import collections
import datetime
import difflib
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

from public_development import generate
from ratchet import ARCHIVE, HERE, TASK, asset, encoded, initialize


def read(relative):
    return json.loads((HERE / relative).read_text())


def wilson(correct, total):
    quantile = 1.959963984540054
    proportion = correct / total
    denominator = 1 + quantile * quantile / total
    center = (proportion + quantile * quantile / (2 * total)) / denominator
    radius = quantile * math.sqrt(proportion * (1 - proportion) / total + quantile * quantile / (4 * total * total)) / denominator
    return [center - radius, center + radius]


def main():
    candidate = HERE / "candidate"
    control = read("reports/control_original-control_champion_original/score.json")
    first = read("reports/moderate480_confirmation-a_champion_parameterized/score.json")
    second = read("reports/moderate480_confirmation-b_champion_parameterized/score.json")
    baseline = read("reports/moderate480_confirmation-a_baseline/score.json")
    official = read("official_champion_score.json")
    equivalence = read("validation_equivalence.json")
    assert control["correct"] == 180 and control["mean_queries"] == 339.0777777777778
    assert first["correct"] < 171 and second["correct"] < 171
    assert not first["passed"] and not second["passed"] and not baseline["passed"]
    assert equivalence["passed"]
    for key in ("correct", "episodes", "cells", "mean_queries", "runtime_resource_score", "policy_sha256", "contract_sha256", "protocol_failures", "target_passed", "complete_hidden_suite"):
        assert official[key] == first[key], (key, official[key], first[key])
    contract = read("candidate/participant/input/contract.json")
    public_cases = read("candidate/participant/input/dev_cases.json")
    assert encoded(generate(contract)) == (candidate / "participant/input/dev_cases.json").read_text()
    scores = {}
    private_seeds = set()
    for path in sorted((HERE / "reports").glob("*/score.json")):
        report = json.loads(path.read_text())
        scores[path.parent.name] = report
        assert report["runtime_resource_score"] == 1 and report["replay_errors"] == 0, path
        private_seeds.update(case["seed"] for case in json.loads((path.parent / "private_cases.json").read_text()))
    assert not private_seeds & {case["seed"] for case in public_cases}
    first_cases = read("reports/moderate480_confirmation-a_champion_parameterized/private_cases.json")
    second_cases = read("reports/moderate480_confirmation-b_champion_parameterized/private_cases.json")
    first_seeds = {case["seed"] for case in first_cases}
    second_seeds = {case["seed"] for case in second_cases}
    assert not first_seeds & second_seeds
    screen_seeds = {case["seed"] for path in (HERE / "reports").glob("screen*/private_cases.json") for case in json.loads(path.read_text())}
    assert not screen_seeds & (first_seeds | second_seeds)
    for profile in (HERE / "profiles").iterdir():
        assert (profile / "participant/input/dev_cases.json").read_bytes() == (ARCHIVE / "participant/input/dev_cases.json").read_bytes()
        assert (profile / "participant/input/simulator.py").read_bytes() == (ARCHIVE / "participant/input/simulator.py").read_bytes()
        assert (profile / "evaluator/evaluate.py").read_bytes() == (TASK / "evaluator/evaluate.py").read_bytes()
        assert sorted(path.name for path in (profile / "participant/input").iterdir()) == ["contract.json", "dev_cases.json", "simulator.py"]
    test_log = (HERE / "validation_contract.log").read_text()
    assert "Ran 12 tests" in test_log and test_log.rstrip().endswith("OK")
    assert not any(path.is_symlink() for path in candidate.rglob("*"))
    champion_hashes = {hashlib.sha256((HERE / "policies" / name).read_bytes()).hexdigest() for name in ("champion_original.py", "champion_parameterized.py")}
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() not in champion_hashes for path in (candidate / "participant").rglob("*") if path.is_file())
    initialize(HERE / "profiles/moderate480", HERE / "policies/champion_parameterized.py")
    import ratchet
    command = ratchet.EVALUATOR.sandbox_command(HERE / "policies/champion_parameterized.py")
    assert "--clearenv" in command and "--unshare-net" in command and "--unshare-pid" in command
    assert "--proc" not in command
    validation = {"passed": True, "contract_isolation_tests": 12, "original_control_correct": control["correct"], "original_control_mean_queries": control["mean_queries"], "mechanical_patch_equivalence": equivalence, "official_cli_score_matches_private_diagnostic_harness": True, "all_scored_episodes_resource_valid": True, "all_scored_diagnostics_replay_exactly": True, "screen_confirmation_seed_overlap": 0, "confirmation_a_b_seed_overlap": 0, "private_public_seed_overlap": 0, "all_profiles_mount_only_original_public_dev": True, "public_simulator_byte_identical": True, "evaluator_byte_identical": True, "champion_not_in_public_assets": True, "public_dev_regenerates_byte_identically": True, "candidate_input_files": sorted(path.name for path in (candidate / "participant/input").iterdir()), "candidate_mounts": command, "wall_seconds": 12, "cpu_seconds": 8, "memory_mib": 512, "startup_handshake": "120-second namespace initialization bound; 12-second interaction timer starts after sandbox_ready; OS CPU/memory caps unchanged", "live_files_changed_by_worker": [], "fresh_agents_launched": 0}
    (HERE / "validation.json").write_text(encoded(validation))
    episodes = read("reports/moderate480_confirmation-a_champion_parameterized/episodes.json") + read("reports/moderate480_confirmation-b_champion_parameterized/episodes.json")
    errors = [record for record in episodes if not record["result"]["correct"]]
    primary = collections.defaultdict(list)
    confusion = collections.Counter()
    for record in errors:
        clusters = record["diagnostic"]["clusters"]
        if "second_component_not_acquired" in clusters:
            cluster = "allocation_second_component_not_acquired"
        elif "contaminated_or_incomplete_neighborhood_model" in clusters:
            cluster = "neighborhood_selection_contains_non_neighbor"
        elif "both_models_from_same_component" in clusters:
            cluster = "component_selection_not_distinct"
        elif "inference_failure_on_valid_neighborhoods" in clusters:
            cluster = "finite_sample_inference_on_valid_distinct_neighborhoods"
        else:
            cluster = "unclassified"
        primary[cluster].append(record)
        confusion[f"{record['case']['family']}->{record['result']['prediction']}"] += 1
    primary_summary = {}
    for cluster, records in primary.items():
        primary_summary[cluster] = {"count": len(records), "median_queries": statistics.median(record["result"]["queries"] for record in records), "median_frames": statistics.median(record["result"]["frames"] for record in records), "unused_queries_at_least_four": sum(record["result"]["queries"] <= 476 for record in records), "unused_frames_at_least_one": sum(record["result"]["frames"] < 160 for record in records), "examples": [{"private_seed": record["case"]["seed"], "family": record["case"]["family"], "denominator": record["case"]["contamination_denominator"], "prediction": record["result"]["prediction"], "frames": record["result"]["frames"], "queries": record["result"]["queries"], "models": record["diagnostic"]["models"]} for record in records[:2]]}
    root_causes = {"episodes": 360, "incorrect": len(errors), "primary_disjoint_clusters": primary_summary, "confusion_on_errors": dict(confusion), "nonexclusive_original_clusters": dict(sum((collections.Counter(score["root_cause_clusters_nonexclusive"]) for score in (first, second)), collections.Counter())), "interpretation": ["Allocation: fixed discovery/rejection stages can fail to acquire a second component, then force a homogeneous RR/SS fallback while resources remain.", "Neighborhood selection: repeated contaminated echoes can enter the frequency-ranked five/six-site core; the later likelihood conditions on that core as a true neighborhood, so correct epsilon alone does not repair structural misspecification.", "Inference: a separate cluster has valid cores from both components but insufficient discriminating observations under background contamination. This is not a stale epsilon-grid or over-budget failure.", "Budget saturation is a nonexclusive indicator, not causal proof. Paired resource screens below isolate query-budget changes on the same cases; no oracle-assisted result is counted as a score.", "The legacy diagnostic key contaminated_or_incomplete_neighborhood_model specifically means at least one selected core site is not a true neighbor; a valid five-site subset alone is not counted."]}
    (HERE / "root_causes.json").write_text(encoded(root_causes))
    paired = {}
    reference = {record["case"]["seed"]: record for record in read("reports/screen480_screen-v1_champion_parameterized/episodes.json")}
    for budget in (360, 300):
        records = read(f"reports/screen{budget}_paired-v1_champion_parameterized/episodes.json")
        assert {record["case"]["seed"] for record in records} == set(reference)
        paired[str(budget)] = {"episodes": len(records), "correct": sum(record["result"]["correct"] for record in records), "480_correct_lower_wrong": sum(reference[record["case"]["seed"]]["result"]["correct"] and not record["result"]["correct"] for record in records), "480_wrong_lower_correct": sum(not reference[record["case"]["seed"]]["result"]["correct"] and record["result"]["correct"] for record in records), "failure_clusters": dict(sum((collections.Counter(record["diagnostic"]["clusters"]) for record in records), collections.Counter()))}
    pooled_correct = first["correct"] + second["correct"]
    summary = {"selected": {"noise_probabilities": ["1/8", "1/6", "1/4"], "parity_queries": 480, "frames": 160, "status": "hard_open_candidate", "solvability": "unknown", "known_passing_implementation": None}, "selection_rationale": "Keep original 480 queries and 160 frames: moderate contamination already defeats correctly parameterized champion on two independent full suites. Do not choose an artificially tight budget, a seed-selected label split, or 1/2 contamination.", "screening": {name: {key: score[key] for key in ("episodes", "correct", "mean_queries", "runtime_resource_score", "cells")} for name, score in scores.items() if name.startswith("screen")}, "screening_caveat": "Exploration used seven equally weighted public epsilon hypotheses and three replicates per cell. The selected contract has three hypotheses; both full confirmations use exactly that grid. Initial unpaired budget screens are descriptive; paired screens reuse all 63 reference cases.", "paired_resource_screens": paired, "confirmation_a": first, "confirmation_b": second, "baseline_confirmation_a": baseline, "original_control": control, "pooled_confirmation": {"correct": pooled_correct, "episodes": 360, "accuracy": pooled_correct / 360, "wilson_95_interval": wilson(pooled_correct, 360), "caveat": "Descriptive uncertainty, not a proof of impossibility or a guaranteed future failure rate."}, "total_sandbox_episodes_in_reports": sum(score["episodes"] for score in scores.values()), "additional_official_cli_episodes": official["episodes"]}
    (HERE / "sweep_summary.json").write_text(encoded(summary))
    for relative in ("participant/input/contract.json", "participant/TASK.md", "participant/workspace/INTERFACE.md", "evaluator/tests/test_contract.py"):
        original = (ARCHIVE / relative).read_text() if (ARCHIVE / relative).exists() else (TASK / relative).read_text()
        changed = (candidate / relative).read_text()
        asset(HERE / "patches" / (relative.replace("/", "__") + ".patch"), "".join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True), fromfile="generation_1/" + relative, tofile="generation_2/" + relative)))
    frozen_path = candidate / "evaluator/frozen.json"
    frozen = json.loads(frozen_path.read_text())
    frozen["sha256"] = {str(path.relative_to(candidate)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(candidate.rglob("*")) if path.is_file() and path != frozen_path}
    old_text = frozen_path.read_text()
    new_text = encoded(frozen)
    if old_text != new_text:
        patch = "*** Begin Patch\n*** Update File: " + str(frozen_path) + "\n@@\n" + "".join("-" + line + "\n" for line in old_text.splitlines()) + "".join("+" + line + "\n" for line in new_text.splitlines()) + "*** End Patch\n"
        subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)
    manifest_hash = hashlib.sha256((candidate / "evaluator/hidden/manifest.json").read_bytes()).hexdigest()
    metadata = {"ready": True, "status": "hard_open_candidate", "generation": 2, "mode": "E", "solvability": "unknown", "known_passing_implementation": None, "public_root": "candidate/participant", "private_evaluator_root": "candidate/evaluator", "private_test_probes": "candidate/adversary", "contract": "candidate/participant/input/contract.json", "hidden_manifest": "candidate/evaluator/hidden/manifest.json", "hidden_manifest_sha256": manifest_hash, "contract_sha256": first["contract_sha256"], "official_score": "official_champion_score.json", "score_reports": "reports", "validation": "validation.json", "root_causes": "root_causes.json", "sweep_summary": "sweep_summary.json", "mechanical_champion_patch": "champion_parameterization.patch", "public_development_instructions": "public_development_generation.json", "target": {"total": "171/180", "each_cell": "18/20"}, "independent_confirmations": [first["correct"], second["correct"]], "baseline_correct": baseline["correct"], "resource_validity": 1.0, "promotion": "Main agent only: copy candidate/participant and candidate/evaluator into generation-two live roots; preserve archived generation one; keep all other ratchet_1 artifacts private. candidate/adversary contains only test probes. Do not mount ratchet_1, profiles, reports, policies, or manifests inside a policy child. No live switch performed by this worker.", "prepared_date": "2026-08-28"}
    (HERE / "candidate_ready.json").write_text(encoded(metadata))
    text = f"""# Generation-two handoff: moderate background contamination

Status: **hard_open_candidate; solvability unknown; no passing tested implementation**.

## Selected public contract

Keep mode E, 256 bits, two hidden relabeled 16-site Rook/Shrikhande components,
RR/RS/SS labels, doublet errors, exact public simulator, 160 frames, 480 total
parities, eight parities/frame, mask weight 64, and 12s interaction / 8 CPU s /
512 MiB. Change only the three contamination probabilities to **1/8, 1/6, 1/4**.
The threshold remains 171/180 and at least 18/20 in each of nine cells.

## Evidence

- Original archived champion: **180/180**, mean **339.0778** queries, matching
  the archived result exactly. Mechanical adaptation reproduces every request
  and response on all 180 control cases; `validation_equivalence.json`.
- Parameterized champion, independent confirmation A: **{first['correct']}/180**;
  confirmation B: **{second['correct']}/180**. Both miss the overall and worst-cell
  thresholds. A uses the candidate manifest, B is a disjoint confirmation only.
- Unmodified evaluator CLI independently reproduces A; `official_champion_score.json`.
- Weak baseline on A: **{baseline['correct']}/180**. All runs are resource-valid.
- All **12** inherited model/protocol/isolation tests pass; `validation_contract.log`.
- Exploratory grids cover 0, 1/32, 1/16, 1/8, 1/6, 1/4, 1/3 at 480/360/300
  queries. Each grid has three samples per cell. The 360/300 paired repeats use
  exactly the 63 cases from 480; `sweep_summary.json` records discordant outcomes.
  No 1/2 contamination was needed. Exploratory seven-point priors are explicitly
  distinguished from the correctly narrowed three-point confirmation prior.

## Failure mechanisms

Across 360 confirmation episodes, {len(errors)} errors separate into the disjoint
clusters in `root_causes.json`: second-component acquisition/allocation failure,
frequency-ranked cores containing non-neighbors, and finite-sample inference
errors even with valid cores from distinct components. Budget saturation is
reported separately and is not asserted to be causal. These are neither stale
epsilon-grid failures nor mechanical budget overruns. A stronger policy needs
uncertainty-aware neighborhood/component discovery and allocation under noise;
no budget-respecting reference solution is claimed.

## Exact champion adaptation

`champion_parameterization.patch` and `parameterization.json` enumerate every
change. Read public contract at `/task/contract.json`; replace 160 with frame
limit, 153/110/120 with frame limit minus 7/50/40, and 470/472/477/370 with query
limit minus 10/8/3/110. Use contract per-frame limit for decoding and the exact
public epsilon hypotheses, preserving the original 1e-5 approximation only for
zero noise. Generalize three-way noise indexing and prior normalization for
exploratory grids. Source selection, discovery thresholds, likelihood formula,
posterior stopping, fallback, decoding and allocation algorithm are unchanged.
Absolute resource reserves are retained; no tuning on private confirmation
cases occurs. All champion code stays in private `policies/`, never public assets.

## Private isolation and promotion

Only the original public development JSON is mounted during every hidden sweep.
Private cases are loaded by the parent; bwrap mounts only system runtime paths,
the profile's three public input files, and the single policy file. There is no
`/proc`, evaluator, manifest, other submission, network or inherited environment.
The parent uses the original Device and evaluator; transcript recording and
exact policy replay happen only after scoring and are not revealed to the child.
Startup namespace initialization is outside the 12-second interaction timer.

Promote **only** `candidate/participant/` and `candidate/evaluator/` (and optionally
`candidate/adversary/` for inherited tests). `candidate_ready.json` is the index.
The private manifest is `candidate/evaluator/hidden/manifest.json`; preserve its
fresh pre-confirmation root seed rather than cherry-picking new hidden cases.
`candidate/evaluator/frozen.json` hashes the release assets. This worker has not
changed the live task, evaluator, attempts or champions, and launched no agents.

## Public development regeneration

The candidate contains 36 new independently generated public cases (four/cell),
not the original low-noise dev cases. From `candidate/participant`, run:

```sh
python3 -B workspace/generate_dev_cases.py --contract input/contract.json --output input/dev_cases.json --episodes-per-cell 4
```

This deterministically reproduces the JSON byte-for-byte without consulting a
private manifest. The public seed recipe and domain are in
`public_development_generation.json`; private/public overlap is zero. Public
development is descriptive and cannot certify the hidden threshold.

## Reproduction

From this private directory, the official confirmation command is:

```sh
python3 -B profiles/moderate480/evaluator/evaluate.py --policy policies/champion_parameterized.py --jobs 16 --output official_champion_score.json
```

The private diagnostic runner is `ratchet.py`; profiles, manifests, episode-level
traces, scores, hashes, paired resource comparisons and patches are retained.
No candidate proof of solvability exists; readiness is for an explicitly allowed
hard-open generation, not a solved-reference benchmark.
"""
    asset(HERE / "HANDOFF.md", text)
    print(encoded({"ready": True, "confirmations": [first["correct"], second["correct"]], "baseline": baseline["correct"], "primary_clusters": {key: value["count"] for key, value in primary_summary.items()}, "paired": paired, "sandbox_episodes": summary["total_sandbox_episodes_in_reports"] + official["episodes"]}))


if __name__ == "__main__":
    main()
