import json
from pathlib import Path
import sys

from generate import generate_case, load_baseline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from phase_model import check


def main():
    baseline = load_baseline()
    families = ("lattice", "bottleneck", "heterogeneous", "shared_dense")
    cases = []
    witnesses = []
    grouped = {family: [] for family in families}
    for family_index, family in enumerate(families):
        for case_index in range(24):
            size = (12, 16, 20, 24, 28)[case_index % 5]
            terms_count = (24, 48, 72, 96)[case_index % 4]
            seed = 0xABD986FA2714099 + 41047 * family_index + 14591 * case_index
            workload, witness = generate_case(seed, family, size, terms_count)
            baseline_metrics = check(workload, baseline.compile_circuit(workload))
            witness_metrics = check(workload, witness)
            case_id = f"stress-{family}-{case_index}"
            improvement = 1 - witness_metrics["cost"] / baseline_metrics["cost"]
            grouped[family].append(improvement)
            cases.append({"id": case_id, "family": family, "input": workload, "baseline": baseline_metrics})
            witnesses.append({"id": case_id, "circuit": witness, "metrics": witness_metrics, "reduction": improvement})
    destination = ROOT / "adversary" / "private_stress"
    destination.mkdir(exist_ok=True)
    (destination / "cases.json").write_text(json.dumps(cases, separators=(",", ":")) + "\n")
    (destination / "witnesses.json").write_text(json.dumps(witnesses, separators=(",", ":")) + "\n")
    summary = {family: {"mean_planted_reduction": sum(values) / len(values), "min_planted_reduction": min(values), "cases_with_40pct_headroom": sum(value >= 0.40 for value in values)} for family, values in grouped.items()}
    report = {"cases": len(cases), "families": summary, "purpose": "Broad private challenge space prepared without fresh-agent feedback. Construction witnesses establish nontrivial baseline gaps, not a generic passing compiler."}
    (destination / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
