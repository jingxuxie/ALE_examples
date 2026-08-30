import argparse
import json
from pathlib import Path
import sys

from generate import load_baseline
from generate_barriers import make_barrier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from phase_model import check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=ROOT / "adversary" / "focused_barriers")
    parser.add_argument("--seed", type=int, default=0xF762B912ACE7B13)
    parser.add_argument("--per-family", type=int, default=16)
    parser.add_argument("--layers", type=int, nargs="+", default=[10, 12, 14, 16, 18])
    options = parser.parse_args()
    destination = options.destination
    destination.mkdir(exist_ok=True)
    baseline = load_baseline()
    cases = []
    witnesses = []
    trials = []
    for family_index, family in enumerate(("lattice", "shared_dense")):
        accepted = 0
        for trial in range(max(200, 12 * options.per_family)):
            layers = options.layers[trial % len(options.layers)]
            extra_terms = (8, 16, 24)[trial % 3]
            seed = options.seed + family_index * 1200041 + trial * 11197
            instance, witness = make_barrier(seed, family, 28, layers, extra_terms)
            baseline_metrics = check(instance, baseline.compile_circuit(instance))
            witness_metrics = check(instance, witness)
            reduction = 1 - witness_metrics["cost"] / baseline_metrics["cost"]
            trials.append({"family": family, "seed": seed, "layers": layers, "extra_terms": extra_terms, "planted_reduction": reduction})
            if reduction < 0.80:
                continue
            case_id = f"focused-{family}-{accepted}"
            cases.append({"id": case_id, "family": family, "input": instance, "baseline": baseline_metrics})
            witnesses.append({"id": case_id, "circuit": witness, "metrics": witness_metrics, "reduction": reduction, "seed": seed, "layers": layers, "extra_terms": extra_terms})
            print(case_id, baseline_metrics["cost"], witness_metrics["cost"], reduction, flush=True)
            accepted += 1
            if accepted == options.per_family:
                break
        if accepted != options.per_family:
            raise ValueError("insufficient physically certified cases; do not weaken the headroom filter")
    (destination / "cases.json").write_text(json.dumps(cases, separators=(",", ":")) + "\n")
    (destination / "witnesses.json").write_text(json.dumps(witnesses, separators=(",", ":")) + "\n")
    (destination / "trials.json").write_text(json.dumps(trials, indent=2) + "\n")


if __name__ == "__main__":
    main()
