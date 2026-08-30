import argparse
import json
import math
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from baseline import baseline_policy
from cascade_sim import load_policy, run_frame, validate_policy


TARGET = {"overall_reduction": 0.08, "family_reduction": 0.03,
          "max_overall_fer": 0.003, "max_family_fer": 0.005,
          "max_family_wilson_upper": 0.01, "max_stress_fer": 0.005}


def wilson_upper(failures, count):
    critical = 1.6448536269514722
    fraction = failures / count
    return (fraction + critical ** 2 / (2 * count) + critical * math.sqrt(
        fraction * (1 - fraction) / count + critical ** 2 / (4 * count ** 2))) / (1 + critical ** 2 / count)


def summarize(records):
    count = len(records)
    failures = sum(record["failure"] for record in records)
    return {"frames": count, "failures": failures, "fer": failures / count,
            "fer_upper_95": wilson_upper(failures, count),
            **{f"mean_{field}": sum(record[field] for record in records) / count
               for field in ["cost", "rounds", "disclosed", "passes", "effective_leakage"]},
            "max_peak_known": max(record["peak_known"] for record in records)}


def score_case(payload):
    case, policy, baseline_records, stress_case = payload
    candidates = []
    references = []
    reference_policy = baseline_policy()
    for frame_index, frame_seed in enumerate(case["frame_seeds"]):
        errors = case["errors"][frame_index] if stress_case else None
        candidate = run_frame(case, frame_seed, policy, errors=errors)
        if not stress_case:
            if policy == reference_policy:
                reference = candidate
            else:
                reference = run_frame(case, frame_seed, reference_policy) if baseline_records is None else baseline_records[str(frame_seed)]
            references.append(reference)
        candidates.append(candidate)
    return case["family"], candidates, references


def evaluate_suite(policy, suite, baseline_records=None, jobs=4):
    validate_policy(policy)
    candidate_groups = defaultdict(list)
    baseline_groups = defaultdict(list)
    case_results = []
    payloads = [(case, policy, baseline_records, False) for case in suite["cases"]]
    payloads.extend((case, policy, None, True) for case in suite.get("stress", []))
    if jobs == 1:
        scored = list(map(score_case, payloads))
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            scored = list(executor.map(score_case, payloads))
    for family, candidates, references in scored[:len(suite["cases"])]:
        candidate_groups[family].extend(candidates)
        baseline_groups[family].extend(references)
        case_results.append({"family": family, "candidate": summarize(candidates), "baseline": summarize(references)})
    families = {}
    for family in sorted(candidate_groups):
        candidate_summary = summarize(candidate_groups[family])
        reference_summary = summarize(baseline_groups[family])
        families[family] = {"candidate": candidate_summary, "baseline": reference_summary,
                            "ratio": candidate_summary["mean_cost"] / reference_summary["mean_cost"]}
    overall_ratio = sum(values["ratio"] for values in families.values()) / len(families)
    all_candidates = [record for records in candidate_groups.values() for record in records]
    total = summarize(all_candidates)
    stress = []
    for family, candidates, references in scored[len(suite["cases"]):]:
        stress.extend(candidates)
    stress_summary = summarize(stress) if stress else None
    reliability = total["fer"] <= TARGET["max_overall_fer"] and all(
        values["candidate"]["fer"] <= TARGET["max_family_fer"] and
        values["candidate"]["fer_upper_95"] <= TARGET["max_family_wilson_upper"] for values in families.values())
    reliability = reliability and stress_summary is not None and stress_summary["fer"] <= TARGET["max_stress_fer"]
    passed = reliability and overall_ratio <= 1 - TARGET["overall_reduction"] and all(
        values["ratio"] <= 1 - TARGET["family_reduction"] for values in families.values())
    reason = "passed" if passed else "improvement_target_not_met" if reliability else "reliability_constraints_not_met"
    return {"split": suite["split"], "overall_ratio": overall_ratio, "improvement": 1 - overall_ratio,
            "core_score": 1 - overall_ratio, "worst_family_score": min(1 - values["ratio"] for values in families.values()),
            "runtime_resource_score": min(values["baseline"]["mean_rounds"] / values["candidate"]["mean_rounds"] for values in families.values()),
            "valid": True, "passed": passed, "reason": reason,
            "families": families, "candidate_total": total, "stress": stress_summary,
            "reliability_pass": reliability, "target_pass": passed, "target": TARGET,
            "case_results": case_results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True)
    parser.add_argument("--split", choices=["train", "dev"], default="dev")
    parser.add_argument("--output")
    parser.add_argument("--jobs", type=int, choices=range(1, 17), default=4)
    arguments = parser.parse_args()
    suite = json.loads((Path(__file__).parent / "input" / f"{arguments.split}.json").read_text())
    result = evaluate_suite(load_policy(arguments.policy), suite, jobs=arguments.jobs)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
