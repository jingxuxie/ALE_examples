import argparse
import json

import numpy as np

from harness import ROOT, load_mps, measure, sha256, write_json
from refine import infer_charges
from trusted_contractor import canonicalize, local_operators, transfer


def profiles(tensors, request):
    charges = infer_charges(tensors, request)
    counts = [{"cut": index, "even": int(np.sum(charge == 0)), "odd": int(np.sum(charge == 1))}
              for index, charge in enumerate(charges)]
    tensors = canonicalize(tensors)
    length = len(tensors)
    rights = [None] * (length + 1)
    rights[-1] = np.ones((1, 1))
    for site in range(length - 1, -1, -1):
        rights[site] = np.einsum("apr,bps,rs->ab", tensors[site].conj(), tensors[site],
                                rights[site + 1], optimize=True)
    left = np.ones((1, 1))
    partial_parity = np.ones((1, 1))
    values = []
    for site, tensor in enumerate(tensors):
        operators = local_operators(request["local_dim"], request["omega"][site])
        local = {}
        for name in ("q", "q2", "parity"):
            image = transfer(left, tensor, operators[name])
            local[name] = float(np.sum(image * rights[site + 1]).real)
        partial_parity = transfer(partial_parity, tensor, operators["parity"])
        local["prefix_parity"] = float(np.sum(partial_parity * rights[site + 1]).real)
        values.append(local)
        left = transfer(left, tensor)
    assert abs(values[-1]["prefix_parity"] - (1 if request["sector"] == "even" else -1)) < 1e-6
    return {"bond_charge_counts": counts, "local_observables": values}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--labels", nargs="+", required=True)
    args = parser.parse_args()
    request = json.loads((ROOT / "requests" / (args.case + ".json")).read_text())
    records = {}
    for label in args.labels:
        path = ROOT / "runs" / args.case / label / "state.npz"
        tensors = load_mps(path, request)
        records[label] = {"state_sha256": sha256(path), "measurement": measure(tensors, request),
                          **profiles(tensors, request)}
    first = args.labels[0]
    comparisons = {}
    for label in args.labels[1:]:
        differences = [old["cut"] for old, new in zip(records[first]["bond_charge_counts"],
                                                       records[label]["bond_charge_counts"])
                       if old != new]
        comparisons[label] = {"energy_gain_against_first": records[first]["measurement"]["energy"]
                               - records[label]["measurement"]["energy"],
                              "different_charge_allocation_cuts": differences}
    result = {"case_id": args.case, "first_label": first, "records": records, "comparisons": comparisons,
              "interpretation": "Measured allocation differences, not a proof that charge counts alone cause the gap"}
    write_json(ROOT / "runs" / args.case / "allocation_diagnostics.json", result)
    print(json.dumps({"case_id": args.case, "comparisons": comparisons}), flush=True)


if __name__ == "__main__":
    main()
