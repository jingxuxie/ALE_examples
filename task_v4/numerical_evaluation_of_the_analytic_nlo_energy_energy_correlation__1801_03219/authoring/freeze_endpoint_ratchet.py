import importlib.util
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

from endpoint_basis import leading_terms,native_chart
import native_kernel


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT/"concept_1"
sys.path.insert(0,str(CONCEPT/"participant/workspace"))
from model import evaluate,load_model,bin_average


def main():
    audit = json.loads((CONCEPT/"evaluator/hidden/oracle_audit.json").read_text())
    assert max(audit[key] for key in ["degree_24_40_values","degree_24_40_derivatives","native_values","native_derivatives","reconstructed_density_discrepancy"]) < 2e-9
    endpoint_limits = {}
    with mp.workdps(180):
        for chart,sign in [("collinear",-1),("backward",1)]:
            endpoint_limits[chart] = {str(sign*distance): [float(mp.re(value)) for value in native_chart(mp.mpf(sign*distance),chart,native_kernel)] for distance in [20,30,40]}
    model = {"knots":np.array([-24.,-4.,4.,24.]),
             "coefficients":[[[1.,2.],[3.,-1.],[2.,4.]]]*3,
             "charts":["collinear","density","backward"]}
    coordinates = np.array([-23.,-8.,-4.2,-3.,0.,3.,4.2,8.,23.])
    native_derivatives = []
    with mp.workdps(70):
        terms = leading_terms()
        for coordinate in coordinates:
            interval = 0 if coordinate < -4 else 1 if coordinate < 4 else 2
            left,right = model["knots"][interval:interval+2]
            chart = model["charts"][interval]
            channel_derivatives = []
            for coefficients in model["coefficients"][interval]:
                channel = len(channel_derivatives)
                def density(argument):
                    latent = coefficients[0]+coefficients[1]*(2*argument-left-right)/(right-left)
                    if chart == "density":
                        return latent
                    angular = 1/(1+mp.exp(-argument))
                    complement = 1/(1+mp.exp(argument))
                    logarithm = mp.log(angular if chart == "collinear" else complement)
                    base = mp.polyval(list(reversed(terms[chart][channel])),logarithm)
                    base *= complement if chart == "collinear" else angular
                    return base+angular*complement*latent
                channel_derivatives.append(float(mp.diff(density,mp.mpf(float(coordinate)))))
            native_derivatives.append(channel_derivatives)
    native_derivatives = np.asarray(native_derivatives)
    derivative_error = float(np.max(np.abs(evaluate(model,coordinates,True,observable="density")-native_derivatives)/(1+np.abs(native_derivatives))))
    assert derivative_error < 1e-12
    module_spec = importlib.util.spec_from_file_location("endpoint_grader",CONCEPT/"evaluator/evaluate.py")
    grader = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(grader)
    baseline = grader.grade(CONCEPT/"participant/baseline")
    assert baseline["valid"] and not baseline["passed"] and baseline["max_tolerance_ratio"] > 100
    (CONCEPT/"evaluator/hidden/target.json").write_text(json.dumps({
        "generation":2,"frozen_before_attempt":True,"scalar_budget":268,
        "max_tolerance_ratio":1.,"minimum_baseline_improvement":100,
        "baseline_max_tolerance_ratio":baseline["max_tolerance_ratio"],
        "point_and_bin_mixed_tolerance":2e-8,"derivative_mixed_tolerance":2e-7,
        "ratchet_basis":"endpoint power corrections, at generation-one champion storage footprint",
    },indent=2)+"\n")
    baseline = grader.grade(CONCEPT/"participant/baseline")
    (CONCEPT/"adversary/generation_2_baseline.json").write_text(json.dumps(baseline,indent=2)+"\n")
    (CONCEPT/"adversary/generation_2_validation.json").write_text(json.dumps({
        "oracle_audit":audit,"independent_density_derivative_error":derivative_error,
        "endpoint_remainders":endpoint_limits,"baseline_error_ratio":baseline["max_tolerance_ratio"],
        "validity":"Numerical convergence and derivative crosschecks pass; exact native source transcription independently audited.",
    },indent=2)+"\n")
    status = json.loads((CONCEPT/"status.json").read_text())
    status.update({"status":"ready","generation":2,"ratchet_generations":1,
                   "baseline":baseline,"solvability":"unknown","target_frozen":True})
    (CONCEPT/"status.json").write_text(json.dumps(status,indent=2)+"\n")
    print(json.dumps({"baseline_max_tolerance_ratio":baseline["max_tolerance_ratio"],"core_score":baseline["core_score"],"worst_family_score":baseline["worst_family_score"],"derivative_crosscheck":derivative_error},indent=2))


if __name__ == "__main__":
    main()
