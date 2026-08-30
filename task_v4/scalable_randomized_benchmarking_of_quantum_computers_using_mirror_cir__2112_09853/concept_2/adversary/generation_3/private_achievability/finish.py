from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys


os.environ["OPENBLAS_NUM_THREADS"] = "1"
AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import model
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    confirmation = json.loads((AREA / "confirmation.json").read_text())
    selection = json.loads((AREA / "selection.json").read_text())
    variant = selection["variant"]
    artifact = AREA / "policies" / variant
    for name, expected in selection["policy_files_sha256"].items():
        assert digest(artifact / name) == expected
    manifest_path = ROOT / "evaluator/hidden/manifest.json"
    assert digest(manifest_path) == "35ede7981b1fbe3beb7aff3e09fa4c0cd5ea4de05a293814b7823d2d1175fd72"
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["files"].items():
        assert digest(ROOT / relative) == expected, relative
    seed_sets = {}
    reports = {}
    for label in ("exploration", "probability_exploration", "confirmation"):
        seed_path = AREA / (label + "_cases.json")
        cases = json.loads(seed_path.read_text())
        seed_sets[label] = {case["seed_hex"] for case in cases}
        report = json.loads((AREA / (label + ".json")).read_text())
        reports[label] = dict(summaries=report["summaries"], isolation=report["isolation"],
                              cases_sha256=digest(seed_path), report_sha256=digest(AREA / (label + ".json")),
                              valid_episodes=sum(record["valid"] for record in report["records"]),
                              episodes=len(report["records"]))
    assert not seed_sets["confirmation"].intersection(seed_sets["exploration"] | seed_sets["probability_exploration"])
    records = confirmation["records"]
    candidates = [record for record in records if record["variant"] == variant]
    controls = {record["seed_hex"]: record for record in records if record["variant"] == "original"}
    assert all(record["valid"] for record in records)
    assert all(record["isolation"] == "bwrap" for record in records)
    assert all(record["shots_used"] <= 2000 for record in records)
    groups = [[record for record in candidates if record["family"] == family and tuple(record["shape"]) == shape]
              for family in model.FAMILIES for shape in model.SHAPES]
    generator = np.random.default_rng(8052017)
    bootstrap = []
    for unused in range(4000):
        chosen = [group[int(index)] for group in groups for index in generator.integers(len(group), size=len(group))]
        family_scores = []
        control_scores = []
        for family in model.FAMILIES:
            members = [record for record in chosen if record["family"] == family]
            family_scores.append(1 / (1 + np.mean([record["normalized_mse"] for record in members])))
            control_scores.append(1 / (1 + np.mean([controls[record["seed_hex"]]["normalized_mse"] for record in members])))
        bootstrap.append([np.mean(family_scores), min(family_scores), np.mean(family_scores) - np.mean(control_scores)])
    diagnostics = []
    for record in candidates:
        episode = model.Episode(int(record["seed_hex"], 16), record["family"], record["shape"])
        fit = json.loads((AREA / "runs/confirmation" / record["id"] / "stderr.txt").read_text().splitlines()[-1])
        inclusion = {tuple(pair): value for pair, value in zip(fit["all_pairs"], fit["posterior_inclusion"])}
        supported = [pair for pair, coefficient in zip(episode.grid.pairs, episode.crosstalk) if coefficient > 0]
        diagnostics.append(dict(family=record["family"], shape=record["shape"],
                                true_support_count=len(supported),
                                posterior_expected_support_count=sum(inclusion.values()),
                                mean_true_pair_inclusion=float(np.mean([inclusion.get(tuple(pair), 0.) for pair in supported])),
                                support_recall=float(np.mean([inclusion.get(tuple(pair), 0.) > .5 for pair in supported])),
                                normalized_mse=record["normalized_mse"]))
    report = dict(completed_utc=datetime.now(timezone.utc).isoformat(), budget=2000,
                  fixed_targets=dict(average=.5, worst_family=1 / 2.5625),
                  search_closed=True, further_generations=False,
                  selected_policy=str(artifact.relative_to(ROOT) / "policy.py"),
                  selection=selection, reports=reports, independent_seed_sets_disjoint=True,
                  frozen_manifest_sha256=digest(manifest_path), all_frozen_manifest_files_unchanged=True,
                  candidate_unchanged_after_selection=True, official_certificate=None,
                  achievability="unknown; no official passing certificate established",
                  stratified_paired_bootstrap_95_percent=dict(
                      average=np.quantile(np.array(bootstrap)[:, 0], [.025, .975]).tolist(),
                      worst_family=np.quantile(np.array(bootstrap)[:, 1], [.025, .975]).tolist(),
                      average_improvement_over_control=np.quantile(np.array(bootstrap)[:, 2], [.025, .975]).tolist()),
                  bootstrap_caveat="Descriptive episode-cluster bootstrap, stratified by family and shape; two replicas per stratum do not establish a universal risk bound.",
                  support_diagnostics_post_selection_only=diagnostics,
                  resource_accounting_probe=json.loads((AREA / "resource_probe.json").read_text()),
                  resource_caveat="Frozen bwrap transport RUSAGE_CHILDREN undercounts policy CPU in this environment. The single-process candidates still inherit the actual 60-second RLIMIT_CPU, and use internal 42/53 CPU-second acquisition/fitting guards. No frozen transport changes were made.",
                  approximation_caveat="Count conditioning uses an independent-Bernoulli support approximation, not exact weighted-without-replacement support or latent-anchor inference. Drift uses the archived Fourier approximation. Uniform SPAM is used only for the disclosed distant_pairs family.")
    (AREA / "final_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(confirmation=confirmation["summaries"],
                         bootstrap=report["stratified_paired_bootstrap_95_percent"],
                         frozen_unchanged=True), indent=2))


if __name__ == "__main__":
    main()
