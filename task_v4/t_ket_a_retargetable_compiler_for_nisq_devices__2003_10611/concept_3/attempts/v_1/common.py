import json
import os
from pathlib import Path


INPUT = Path(os.environ.get("INPUT", "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/concept_3/participant/input/instances.json"))
CASES = json.loads(INPUT.read_text())["instances"]


def verify(case, gates):
    size = case["n"]
    rows = [1 << wire for wire in range(size)]
    clocks = [0] * size
    visited = set(rows)
    native = {tuple(sorted(edge)) for edge in case["edges"]}
    for control, target in gates:
        assert type(control) is int and type(target) is int
        assert 0 <= control < size and 0 <= target < size
        assert tuple(sorted((control, target))) in native
        rows[target] ^= rows[control]
        visited.add(rows[target])
        clocks[control] = clocks[target] = 1 + max(clocks[control], clocks[target])
    missing = set(case["required_parities"]) - visited
    depth = max(clocks)
    exact = rows == case["target_rows"]
    return dict(id=case["id"], count=len(gates), depth=depth,
                max_count=case["max_cnots"], max_depth=case["max_depth"],
                exact=exact, missing=sorted(missing),
                passed=exact and not missing and len(gates) <= case["max_cnots"] and depth <= case["max_depth"])


def write_witness(circuits, path="submission/witness.json"):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(schema_version=1, circuits=circuits), separators=(",", ":")) + "\n")


def export_instances(path="instances.txt"):
    with open(path, "w") as stream:
        print(len(CASES), file=stream)
        for case in CASES:
            print(case["id"], case["n"], len(case["edges"]), len(case["required_parities"]), case["max_cnots"], case["max_depth"], file=stream)
            for edge in case["edges"]:
                print(*edge, file=stream)
            print(*case["target_rows"], file=stream)
            print(*case["required_parities"], file=stream)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--witness", default="submission/witness.json")
    args = parser.parse_args()
    if args.export:
        export_instances()
    else:
        witness = json.loads(Path(args.witness).read_text())
        assert set(witness) == {"schema_version", "circuits"}
        assert witness["schema_version"] == 1
        assert set(witness["circuits"]) == {case["id"] for case in CASES}
        reports = [verify(case, witness["circuits"][case["id"]]) for case in CASES]
        print(json.dumps(reports, indent=2))
