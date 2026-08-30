import importlib.util
import json
from pathlib import Path

from generate import make_case


ROOT = Path(__file__).resolve().parent
specification = importlib.util.spec_from_file_location("portfolio", ROOT / "portfolio/solver.py")
portfolio = importlib.util.module_from_spec(specification)
specification.loader.exec_module(portfolio)


def main():
    request = json.loads((ROOT / "broad_search/cases.json").read_text())
    previous = json.loads((ROOT / "broad_search/portfolio_solution.json").read_text())
    previous = {item["id"]: item for item in previous["solutions"]}
    solutions, records = [], []
    reference = portfolio.baseline_module()
    for index, case in enumerate(request["cases"]):
        dimension = len(case["one_body"])
        _, planted, _ = make_case(803921 + index * 1009, case["family"], dimension, dimension - 2, case["id"])
        refined, record = portfolio.optimize(case, planted, 12)
        old = previous[case["id"]]
        import numpy as np
        old_cost = reference.cost(np.asarray(case["one_body"]), np.asarray(case["factors"]), np.asarray(old["orbital"]), np.asarray(old["auxiliary"]))
        if old_cost <= record["cost"]:
            refined = old
        record["previous_cost"] = old_cost
        record["best_cost"] = min(old_cost, record["cost"])
        record["extra_reduction"] = 1 - record["best_cost"] / old_cost
        records.append(record)
        solutions.append(refined)
        print(json.dumps(record), flush=True)
    (ROOT / "broad_search/privileged_multistart_solution.json").write_text(json.dumps({"solutions": solutions}, allow_nan=False))
    (ROOT / "broad_search/privileged_multistart_report.json").write_text(json.dumps({"records": records, "uses_private_planted_initializations": True, "interpretation": "Establishes additional quality feasibility and finds optimization failures; does not by itself certify an unprivileged generic inference solver."}, indent=2))


if __name__ == "__main__":
    main()
