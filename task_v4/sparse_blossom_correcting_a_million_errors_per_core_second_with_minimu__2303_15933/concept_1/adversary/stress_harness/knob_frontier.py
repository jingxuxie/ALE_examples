import itertools
import json

from common import SIDE, write_json
import numpy as np


def analyze(name, records, reference_name, predictions_dir, base_predictions_dir):
    selected = json.loads((SIDE / "ratchet2_selected.json").read_text())["specs"]
    case_ids = [spec["case_id"] for spec in selected]
    groups = {spec["case_id"]: spec["stress_group"] for spec in selected}
    records = [record for record in records if record["case_id"] in case_ids]
    baseline = {record["case_id"]: record for record in records if record["variant"] == reference_name}
    baseline_cpu = sum(record["cpu_seconds"] for record in baseline.values())
    baseline_errors = sum(record["failures"] for record in baseline.values())
    family_baselines = {group: sum(record["failures"] for case, record in baseline.items() if groups[case] == group) for group in set(groups.values())}
    options = [[record for record in records if record["case_id"] == case] for case in case_ids]
    frontier = []
    for ratio in [1.1, 1.25, 1.5, 2, 4, 8]:
        choices = []
        for combination in itertools.product(*options):
            cpu = sum(record["cpu_seconds"] for record in combination)
            if cpu > ratio * baseline_cpu:
                continue
            if any(sum(record["failures"] for record in combination if groups[record["case_id"]] == family) > count for family, count in family_baselines.items()):
                continue
            errors = sum(record["failures"] for record in combination)
            choices.append((errors, cpu, combination))
        if choices:
            errors, cpu, combination = min(choices, key=lambda entry: entry[:2])
            frontier.append(dict(cpu_budget_ratio=ratio, failures=errors, reduction=1 - errors / baseline_errors,
                actual_cpu_ratio=cpu / baseline_cpu, case_variants={entry["case_id"]: entry["variant"] for entry in combination}))
    uniform = []
    for variant in sorted({record["variant"] for record in records}):
        current = [record for record in records if record["variant"] == variant]
        if len(current) == len(case_ids):
            uniform.append(dict(variant=variant, failures=sum(record["failures"] for record in current),
                reduction=1 - sum(record["failures"] for record in current) / baseline_errors,
                cpu_ratio=sum(record["cpu_seconds"] for record in current) / baseline_cpu))
    adaptive = []
    corpus = SIDE / "corpora" / ("ratchet2_confirm_128" if "confirm" in name else "ratchet2_pilot_256")
    for threshold in [0.1, 0.25, 0.5, 1, 2, 4]:
        errors, routed, count, estimated_cpu = 0, 0, 0, baseline_cpu
        for case in case_ids:
            source = predictions_dir / (case + "__" + ("native_compiler" if "confirm" in name else "champion") + ".npz")
            with np.load(source, allow_pickle=False) as data:
                metrics = data["diagnostics"]
                candidate = data["predictions"].copy()
            with np.load(predictions_dir / (case + "__quad_ensemble.npz"), allow_pickle=False) as data:
                quad = data["predictions"]
            with np.load(corpus / "private" / (case + ".npz"), allow_pickle=False) as data:
                labels = data["labels"][:len(candidate)]
            selected_rows = (metrics[:, 0] == 0) & (metrics[:, 1] <= threshold)
            candidate[selected_rows] = quad[selected_rows]
            errors += int(np.any(candidate != labels, axis=1).sum())
            routed += int(selected_rows.sum())
            count += len(candidate)
            quad_record = next(record for record in records if record["case_id"] == case and record["variant"] == "quad_ensemble")
            estimated_cpu += quad_record["cpu_seconds"] * selected_rows.mean()
        adaptive.append(dict(gap_threshold=threshold, failures=errors, reduction=1 - errors / baseline_errors,
            routed=routed, shots=count, estimated_cpu_ratio=estimated_cpu / baseline_cpu))
    return dict(name=name, baseline_failures=baseline_errors, baseline_cpu=baseline_cpu, shots=sum(record["shots"] for record in baseline.values()),
        family_baselines=family_baselines, uniform=uniform, per_case_label_oracle_frontier=frontier, adaptive_gap_controls=adaptive,
        caveats=["Private exploratory results, not an official future score.",
                 "Case-wise configuration selection uses labels and is optimistic, not a usable unbiased decoder.",
                 "Adaptive error counts are exact replay; routing CPU is an estimate using per-case average decode costs.",
                 "Truncated candidate-list gaps are not certified posterior probabilities."])


def main():
    pilot = SIDE / "private_sweeps/ratchet2_knobs_64"
    confirmation = SIDE / "private_sweeps/ratchet2_confirm_native_128"
    promoted = SIDE / "private_sweeps/ratchet2_confirm_champion_128"
    sources = [pilot, confirmation, promoted]
    summaries = [json.loads((source / "summary.json").read_text()) for source in sources]
    if not all(summary["complete"] for summary in summaries):
        raise ValueError("Wait for all controls")
    reports = [analyze("pilot", summaries[0]["records"], "champion", pilot, pilot),
               analyze("confirmation", summaries[1]["records"] + summaries[2]["records"], "champion", confirmation, promoted)]
    write_json(SIDE / "reports/ratchet2_knob_frontier.json", dict(reports=reports, frozen_generation_modified=False))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
