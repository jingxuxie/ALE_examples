from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

import sys
import time

from scipy.optimize import minimize

from analyze import compare_topology
from focused import load

sys.path.insert(0, str(CONCEPT / "participant/input"))
from gl_model import GLModel


def main():
    manifest, target = load()
    records = []
    for reference in manifest["cases"]:
        case = read_case(ROOT / reference["case_path"])
        model = GLModel(case)
        baseline = checked_field(ROOT / reference["baseline_path"], case)
        started = time.monotonic()
        result = minimize(model.objective, model.pack(baseline), jac=True, method="L-BFGS-B", options={"maxiter": 2000, "maxls": 40, "ftol": 1e-15, "gtol": 1e-9, "maxcor": 20})
        field = model.unpack(result.x)
        energy, unused, rms = energy_gradient(case, field)
        topology = compare_topology(case, baseline, field)
        records.append({"case_id": reference["case_id"], "energy": energy, "gradient_rms": rms, "improvement": reference["baseline_energy"] - energy, "iterations": result.nit, "wall_seconds": time.monotonic() - started, "changed_hole_windings": len(topology["changed_hole_windings"]), "meaningful_topology_change": topology["meaningful_topology_change"], "scipy_message": str(result.message)})
    write_json(ROOT / "local_polish.json", {"purpose": "tight-tolerance local relaxation diagnostic, not witness construction or a ground-state certificate", "records": records})
    print(records)


if __name__ == "__main__":
    main()
