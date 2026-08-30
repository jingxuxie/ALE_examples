import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from channel import fit_table, marginals


def solve(instance):
    selected = []
    table, risks = fit_table(marginals(instance, selected))
    for stage in range(instance["budget"]):
        best = None
        for tap in range(len(instance["taps"])):
            if tap in selected:
                continue
            proposal = sorted(selected + [tap])
            candidate_table, candidate_risks = fit_table(marginals(instance, proposal))
            key = (max(candidate_risks), sum(candidate_risks), proposal)
            if best is None or key < best[0]:
                best = key, proposal, candidate_table
        selected, table = best[1:]
    return {"selected": selected, "correction": table}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    answer = solve(json.loads(Path(arguments.input).read_text()))
    Path(arguments.output).write_text(json.dumps(answer) + "\n")


if __name__ == "__main__":
    main()
