import json
import os

import numpy as np

from build_pilots import ROOT, reference, write_events


def add_case(kind, case_id, family, source_case, requested, query_list, rationale):
    pool = ROOT / "pilots" / kind / "private" / "challenge_pool"
    manifest_path = pool / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    parent_case = next(case for case in manifest["cases"] if case["id"] == source_case)
    data = np.loadtxt(pool / source_case / "events.txt", ndmin=2)
    events = [data[data[:, 0] == index, 1:] for index in range(requested)]
    directory = pool / case_id
    directory.mkdir(exist_ok=True)
    write_events(directory / "events.txt", events)
    (directory / "job.json").write_text(json.dumps({"kind": kind, "events_file": "events.txt", "nevents": requested, "queries": query_list}, indent=2))
    manifest["cases"] = [case for case in manifest["cases"] if case["id"] != case_id]
    manifest["cases"].append({"id": case_id, "family": family, "split": "pool", "nevents": requested, "max_constituents": max(map(len, events)), "source_ids": parent_case["source_ids"][:requested], "rationale": rationale})
    manifest_path.write_text(json.dumps(manifest, indent=2))
    reference(kind, case_id)


available = os.sched_getaffinity(0)
os.sched_setaffinity(0, {sorted(available)[-4]})
resolved_queries = [
    dict(order=3, log_min=-5.0, bins=60, ratio_bins=8, phi_bins=5, nu1=0.35, nu2=0.75),
    dict(order=4, log_min=-5.0, bins=60, ratio_bins=8, phi_bins=5, nu1=0.45, nu2=1.3, nu3=0.8),
    dict(order=4, log_min=-4.0, bins=48, ratio_bins=5, phi_bins=13, nu1=0.9, nu2=0.7, nu3=2.2),
]
add_case("resolved", "pool_sector_repartition", "nonlinear_sector_repartition", "pool_ordinary", 128, resolved_queries,
         "The source's non-unit finite differences are phi-local. Changing angular sectors changes the statistic itself; results cannot be obtained by rebinning the public-sector histogram. Includes distinct positive exponents and mixed partition requests on the same real jets.")
ewoc_queries = []
for geometry in ["pp", "ee"]:
    for algorithm in ["ca", "kt", "antikt"]:
        ewoc_queries += [dict(geometry=geometry, algorithm=algorithm, radius=0.45, observable="mass", kappa=1.0, log_min=-2.0, bins=65),
                         dict(geometry=geometry, algorithm=algorithm, radius=0.025, observable="angular", kappa=1.7, log_min=-4.0, bins=65)]
add_case("ewoc", "pool_radius_transition", "subjet_contact_transition", "pool_high_multiplicity", 128, ewoc_queries,
         "All six source-supported geometry/algorithm combinations, contrasting nearly constituent-resolved angular measurements with large-radius massive diagonal contacts; this tests physical integration, not malformed inputs or roundoff masses.")
