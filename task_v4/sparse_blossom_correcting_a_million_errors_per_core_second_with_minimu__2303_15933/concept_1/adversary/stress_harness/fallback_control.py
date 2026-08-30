import json

from common import ROOT, SIDE, write_json
import numpy as np
from diagnostics import summarize_pair


def main():
    specs = json.loads((SIDE / "ratchet2_selected.json").read_text())["specs"]
    reports = []
    for name, corpus_name, prediction_name, variant in [
        ("pilot", "ratchet2_pilot_256", "ratchet2_knobs_64", "champion"),
        ("confirmation", "ratchet2_confirm_128", "ratchet2_confirm_native_128", "native_compiler"),
    ]:
        records = []
        original_wrong = []
        pooled = {}
        for spec in specs:
            case_id = spec["case_id"]
            with np.load(SIDE / "private_sweeps" / prediction_name / (case_id + "__" + variant + ".npz"), allow_pickle=False) as data:
                champion, metrics = data["predictions"], data["diagnostics"]
            with np.load(SIDE / "corpora" / corpus_name / "private" / (case_id + ".npz"), allow_pickle=False) as data:
                labels, matching = data["labels"][:len(champion)], data["baseline"][:len(champion)]
            base_wrong = np.any(champion != labels, axis=1)
            original_wrong.append(base_wrong)
            case_records = []
            for threshold in [0, 0.1, 0.25, 0.5, 1, 2, 4, 8, 100]:
                selected = (metrics[:, 0] == 0) & (metrics[:, 1] < threshold)
                predictions = champion.copy()
                predictions[selected] = matching[selected]
                wrong = np.any(predictions != labels, axis=1)
                pooled.setdefault(threshold, []).append(wrong)
                case_records.append(dict(threshold=threshold, failures=int(wrong.sum()), routed=int(selected.sum())))
            records.append(dict(case_id=case_id, baseline_failures=int(base_wrong.sum()), pure_matching_failures=int(np.any(matching != labels, axis=1).sum()), controls=case_records))
        baseline = np.concatenate(original_wrong)
        reports.append(dict(name=name, cases=records, controls=[dict(threshold=threshold, **summarize_pair(baseline, np.concatenate(wrong))) for threshold, wrong in pooled.items()],
            optimistic_casewise_label_oracle_failures=sum(min(control["failures"] for control in case["controls"]) for case in records),
            baseline_failures=int(baseline.sum())))
    report = dict(complete=True, reports=reports, official_score=False, exploratory=True,
        method="Replace the promoted prediction by two-pass correlated PyMatching only on low truncated-list-confidence shots; nine thresholds, two independent corpora",
        caveat="Exact prediction replay. Runtime is not an isolated measurement; no Bayes-optimality claim.")
    write_json(SIDE / "reports/ratchet2_fallback_controls.json", report)
    (ROOT / "generations/generation_2/evaluator/hidden/evidence/fallback_controls.json").write_text(json.dumps(report, indent=2) + "\n")
    for entry in reports:
        print(entry["name"], "baseline", entry["baseline_failures"], "best uniform", min(control["candidate_failures"] for control in entry["controls"]), "casewise oracle", entry["optimistic_casewise_label_oracle_failures"])


if __name__ == "__main__":
    main()
