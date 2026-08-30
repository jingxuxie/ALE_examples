import json
from pathlib import Path

from common import ROOT, SIDE, digest_file
import numpy as np
from diagnostics import summarize_pair


def main():
    selected = json.loads((SIDE / "ratchet2_selected.json").read_text())["specs"]
    groups = {spec["case_id"]: spec["stress_group"] for spec in selected}
    references = {}
    predictions = {}
    residuals = []
    corpus = SIDE / "corpora/ratchet2_confirm_128"
    for case_id, group in groups.items():
        with np.load(corpus / "private" / (case_id + ".npz"), allow_pickle=False) as data:
            labels = data["labels"]
        with np.load(SIDE / "private_sweeps/ratchet2_confirm_champion_128" / (case_id + "__champion.npz"), allow_pickle=False) as data:
            wrong = np.any(data["predictions"] != labels, axis=1)
            references[case_id] = wrong
        predictions[case_id] = {}
        for variant in ["native_compiler", "double_ensemble", "quad_ensemble", "wide_osd"]:
            with np.load(SIDE / "private_sweeps/ratchet2_confirm_native_128" / (case_id + "__" + variant + ".npz"), allow_pickle=False) as data:
                predictions[case_id][variant] = np.any(data["predictions"] != labels, axis=1)
                if variant == "native_compiler":
                    metrics = data["diagnostics"]
        with np.load(corpus / "private" / (case_id + "_features.npz"), allow_pickle=False) as data:
            features = {name: data[name] for name in data.files}
        report = json.loads((SIDE / "private_sweeps/ratchet2_confirm_champion_128" / (case_id + "__champion_residuals.json")).read_text())
        residuals.append(dict(case_id=case_id, family=group, failures=int(wrong.sum()), shots=len(wrong),
            fast_failures=int(((metrics[:, 0] > 0) & wrong).sum()),
            mean_truncated_gap_on_failures=float(metrics[wrong, 1].mean()),
            failure_feature_means={name: float(value[wrong].mean()) for name, value in features.items()},
            all_shot_feature_means={name: float(value.mean()) for name, value in features.items()},
            logical_confusion_masks=report["logical_confusion_masks"], joint_css_failures=report["joint_css_failures"],
            detector_hotspots=report["detector_hotspots"][:3]))
    controls = []
    for variant in ["native_compiler", "double_ensemble", "quad_ensemble", "wide_osd"]:
        controls.append(dict(variant=variant,
            pooled=summarize_pair(np.concatenate(list(references.values())), np.concatenate([predictions[case][variant] for case in groups])),
            families={group: summarize_pair(np.concatenate([references[case] for case in groups if groups[case] == group]),
                np.concatenate([predictions[case][variant] for case in groups if groups[case] == group])) for group in sorted(set(groups.values()))}))
    output = dict(exploratory=True, official_score=False, target_selected_without_using_new_candidate_hidden_scores=True,
        proposed_targets=dict(pooled_error_reduction=0.20, holdout_error_reduction=0.15, max_family_failure_ratio=1.0, relative_cpu_multiplier=1.25),
        broad_screen=dict(regimes=33, shots_per_regime=32, champion_failures=37, shots=1056,
            excluded_result="champion_broad_32 was invalidated for a Fortran/C output-buffer mismatch; only champion_broad_verified_32 was used"),
        selected_confirmation=dict(shots=768, champion_failures=101, cases=residuals), controls=controls,
        headroom_evidence="Pilot: 58 to 45 failures with 4x ensembles, 4.93x measured native CPU. Independent confirmation: 101 to 95 at 4.65x CPU, with uncertainty including zero. This is not a demonstrated passing reference.",
        cheap_controls="Case-wise label-oracle choices at 1.25x CPU remove 5.17% on pilot and 3.96% on independent confirmation. Compiler-only removes zero. Eight likelihood-temperature controls remove at most 1.98% uniformly; even their case-wise label oracle removes only 6.93%.",
        scientific_interpretation="Residuals concentrate in the list-search path and spatial-pair-coupled inference; the noisy temporal case has confidently wrong truncated-list scores. These are associations and evidence of a difficult approximation problem, not an exact Bayes-gap proof.",
        root_cause_limits=["True sampled fault components are not necessarily decoder correction components.",
            "Hotspot ranking is exploratory, with uncorrected multiple comparisons.",
            "No exact logical posterior or certified lower bound was computed.",
            "A disjoint X/Z/Y gauge marginalization experiment did not improve pilot errors.",
            "Adaptive gap-routing CPU in knob_frontier is estimated, not an isolated resource score.",
            "A full-budget passing method is unknown; main may review this as a hard open improvement task."],
        corpus_manifest_sha256=digest_file(corpus / "manifest.json"))
    destination = ROOT / "generations/generation_2/evaluator/hidden/scientific_selection.json"
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(dict(controls=[dict(variant=entry["variant"], pooled=entry["pooled"]) for entry in controls]), indent=2))


if __name__ == "__main__":
    main()
