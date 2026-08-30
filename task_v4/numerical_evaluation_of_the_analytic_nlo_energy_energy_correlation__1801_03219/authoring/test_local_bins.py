import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"concept_1/adversary"))
sys.path.insert(0,str(ROOT/"concept_1/participant/workspace"))
from robust_bins import bin_average_local
from model import bin_average,endpoint_base


def main():
    upper = np.nextafter(1.,np.inf)
    amplitude = 1/(upper-1)
    model = {"knots":np.array([-24.,1.,upper,24.]),
             "coefficients":[[[0.],[0.],[0.]],[[3*amplitude/8,0.,-amplitude/2,0.,amplitude/8],[0.],[0.]],[[0.],[0.],[0.]]]}
    checks = []
    for lower,upper,expected in [(0.,2.,4/15),(-24.,24.,1/90),(1.,upper,8*amplitude/15)]:
        actual = float(bin_average_local(model,lower,upper)[0])
        old = float(bin_average(model,lower,upper)[0])
        assert abs(actual-expected)/(1+abs(expected)) < 1e-13
        checks.append({"lower":lower,"upper":upper,"expected":expected,"local_result":actual,"old_global_result":old})
    reference = dict(np.load(ROOT/"concept_1/evaluator/hidden/oracle.npz"))
    cases = np.load(ROOT/"concept_1/evaluator/hidden/cases.npz")
    differences = []
    for lower,upper in cases["bins"]:
        old = bin_average(reference,lower,upper)
        new = bin_average_local(reference,lower,upper,endpoint_base)
        differences.append(np.max(np.abs(old-new)/(1+np.abs(old))))
    assert max(differences) < 1e-12
    report = {"one_ulp_regression":checks,"reference_max_mixed_change":float(max(differences)),
              "target_changed":False,"reason":"Evaluate Chebyshev polynomials in interval-local quadrature coordinates; preserve physical mass on unresolved global intervals."}
    (ROOT/"concept_1/adversary/local_bin_regression.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
