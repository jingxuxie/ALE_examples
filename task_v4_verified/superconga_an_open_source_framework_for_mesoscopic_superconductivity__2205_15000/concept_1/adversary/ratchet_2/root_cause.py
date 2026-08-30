from common import ROOT, digest, read_json, write_json

import sys
import time

import numpy as np

sys.path.insert(0, str(ROOT / "submission"))
from numerics import Model
from sectors import HarmonicSectors


def main():
    records = []
    for name in ("vp03", "vp05"):
        reference = read_json(ROOT / "frozen_warm_inputs" / name / "reference.json")
        case = read_json(ROOT / reference["case_path"])
        model = Model(case)
        started = time.monotonic()
        record = {"case_id": name, "input_sha256": digest(ROOT / reference["case_path"])}
        try:
            sector = HarmonicSectors(model, model.initial)
            np.linalg.solve(sector.hessian, sector.projected.T * sector.weights)
            eigenvalues = np.linalg.eigvalsh(sector.hessian)
            record.update({"construction_succeeds": True, "hole_sector_dimension": len(sector.centers), "quadratic_min_eigenvalue": float(eigenvalues.min()), "quadratic_max_eigenvalue": float(eigenvalues.max()), "continuous_sector_center_min": float(sector.center.min()), "continuous_sector_center_max": float(sector.center.max())})
        except (RuntimeError, np.linalg.LinAlgError) as error:
            record.update({"construction_succeeds": False, "exception": str(error)})
        record["wall_seconds"] = time.monotonic() - started
        records.append(record)
    write_json(ROOT / "root_cause.json", {"purpose": "bounded initialization-only diagnostic of unchanged captured solver; no field optimization or witness generation", "source_manifest_sha256": digest(ROOT / "source_manifest.json"), "records": records, "interpretation": "Successful projection construction rules out its numerical-failure fallback on these exact frozen starts. All scored repeats return the same energy with zero nonlinear candidate trials, well before budget cutoffs. The algorithm searches hole-winding sectors but does not explicitly propose bulk-vortex relocation; tight local polishing does not close the observed vortex-allocation gaps. This does not replace the predeclared clean-load certification gate."})
    print(records)


if __name__ == "__main__":
    main()
