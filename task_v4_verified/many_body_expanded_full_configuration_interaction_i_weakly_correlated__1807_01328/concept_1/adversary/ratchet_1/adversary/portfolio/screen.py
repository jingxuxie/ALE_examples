import json
import math
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "template"))
from acquisition import UNKNOWN, acquire, prior
from experiment import MASKS, ORDERS, SUBSETS, transform
from solution import FAMILIES, predict_prior


def quiet_core(terms):
    strengths = np.array([sum(abs(terms[mask]) for mask in MASKS[3] if not mask & (1 << orbital)) for orbital in range(8)])
    omitted = int(np.argmin(strengths))
    included = np.array([mask for mask in MASKS[3] if not mask & (1 << omitted)])
    ratio = float(strengths[omitted] / max(sum(abs(terms[MASKS[3]])), 1e-12))
    return omitted if ratio < .03 and np.max(abs(terms[included])) < 1.5e-6 else None


def adaptive_covariance(terms, omitted, exponent, old_scale, high_order):
    original = prior(terms, fifth_weight=2)
    pair_strength = SUBSETS[UNKNOWN][:, MASKS[2]] @ abs(terms[MASKS[2]])
    activity = SUBSETS[UNKNOWN][:, MASKS[1]] @ abs(terms[MASKS[1]])
    pair_metric = pair_strength ** 2 / np.maximum(activity, 1e-10)
    old = (UNKNOWN & (1 << omitted)) == 0
    reference = max(np.median(pair_metric[old & (ORDERS[UNKNOWN] == 4)]), 1e-9)
    scales = np.sqrt(np.diag(original)).copy()
    scales[old] = old_scale * (np.maximum(pair_metric[old], reference * .001) / reference) ** exponent
    scales[old] *= high_order ** (ORDERS[UNKNOWN[old]] - 4)
    return np.diag(scales ** 2 + 1e-20)


def main():
    source = ROOT.parents[2] / "cancellation_search/batch_02"
    models = json.loads((source / "models.json").read_text())
    tables = np.load(source / "cases.npz", allow_pickle=False)["energies"]
    prepared = []
    for model, table in zip(models, tables):
        observed = np.zeros(256)
        observed[ORDERS <= 3] = table[ORDERS <= 3]
        terms = transform(observed)
        terms[ORDERS >= 4] = 0
        omitted = quiet_core(terms)
        if model["family"] != "mixed" or omitted is None:
            continue
        mean = predict_prior(observed, np.array(model["orbital_energy"]), FAMILIES.index(model["family"]))
        prepared.append((terms, table, omitted, mean))
    print(json.dumps({"quiet_systems": len(prepared), "started": time.time()}), flush=True)
    results = []
    deadline = json.loads((ROOT / "budget.json").read_text())["deadline_unix"]
    for exponent in (0., .5, 1., 2.):
        for old_scale in (3e-6, 1e-5, 3e-5, 1e-4):
            for high_order in (.03, .15):
                for power in (.4, .8, 1.2):
                    for mode in ("quad", "any", "six"):
                        if time.time() > deadline - 300:
                            break
                        errors, queries_used = [], []
                        for terms, table, omitted, mean in prepared:
                            covariance = adaptive_covariance(terms, omitted, exponent, old_scale, high_order)
                            queries, _, cost = acquire(terms, covariance, mean=mean, budget=104, power=power,
                                                       return_queries=True, force_six=mode == "six", quints=0 if mode == "quad" else None)
                            design = SUBSETS[queries][:, UNKNOWN].astype(float)
                            kernel = design @ covariance @ design.T
                            weights = np.linalg.solve(kernel + np.eye(len(queries)) * 1e-20, design @ covariance @ np.ones(len(UNKNOWN)))
                            tail = mean[UNKNOWN].sum() + weights @ (table[queries] - SUBSETS[queries] @ terms - design @ mean[UNKNOWN])
                            errors.append(float(terms.sum() + tail - table[-1]))
                            queries_used.append(queries.tolist())
                        result = {"exponent": exponent, "old_scale": old_scale, "high_order": high_order,
                                  "power": power, "mode": mode, "mixed_rmse": math.sqrt(np.mean(np.square(errors))),
                                  "maximum_error": max(map(abs, errors)), "errors": errors, "queries": queries_used}
                        results.append(result)
    results.sort(key=lambda item: item["mixed_rmse"])
    (ROOT / "screen_results.json").write_text(json.dumps({"diagnostic_only": True, "offline_tuning_not_sandbox_score": True,
                                                          "quiet_systems": len(prepared), "results": results[:30]}, indent=2) + "\n")
    print(json.dumps([{key:value for key,value in result.items() if key not in ("errors","queries")} for result in results[:10]], indent=2), flush=True)


if __name__ == "__main__":
    main()
