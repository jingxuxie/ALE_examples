import json
from pathlib import Path
import sys

import numpy as np

import solution as candidate


records = []
original_fit = candidate.Model.fit
original_design = candidate.design
original_posterior = candidate.posterior_mean


def fit(model, counts, initial=None, iterations=150):
    result = original_fit(model, counts, initial, iterations)
    records.append({"kind": "fit", "shots": int(counts.sum()), "iterations": iterations,
                    "bounds": model.bounds.tolist(), "log_rates": result.tolist()})
    return result


def design(model, log_rates, used, budget, criterion="rms"):
    allocation, information = original_design(model, log_rates, used, budget, criterion)
    projected = used + (budget - used.sum()) * allocation
    covariance = np.linalg.inv(np.einsum("a,akl->kl", projected, information))
    records.append({"kind": "design", "shots_before": int(used.sum()), "log_rates": log_rates.tolist(),
                    "used": used.tolist(), "allocation": allocation.tolist(), "criterion": criterion,
                    "predicted_family_sd_if_full_plan_used": np.sqrt(model.family_weights @ np.diag(covariance)).tolist()})
    return allocation, information


def posterior(model, counts, fitted, power=10):
    details = {}

    def trace(frame, event, argument):
        if frame.f_code is original_posterior.__code__:
            if event == "return":
                details["effective_samples"] = frame.f_locals.get("effective_samples")
                details["expanded_mode"] = frame.f_locals.get("mode", np.array([])).tolist()
            return trace
        return None

    sys.settrace(trace)
    try:
        result = original_posterior(model, counts, fitted, power)
    finally:
        sys.settrace(None)
    records.append({"kind": "posterior", "before_log_rates": fitted.tolist(),
                    "after_log_rates": result.tolist(), **details})
    return result


candidate.Model.fit = fit
candidate.design = design
candidate.posterior_mean = posterior
candidate.main()
Path("trace.json").write_text(json.dumps(records, indent=2) + "\n")
