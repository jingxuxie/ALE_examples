import json
from pathlib import Path


def main():
    concept = Path(__file__).resolve().parents[1]
    model = json.loads((concept / "participant/input/model.json").read_text())
    columns = [int(value, 16) for value in model["columns"]]
    results = []
    for attempt in ("v_5", "v_6"):
        candidates = []
        for artifact in sorted((concept / "attempts" / attempt).rglob("*.json")):
            if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 16384:
                continue
            try:
                data = json.loads(artifact.read_text())
            except (UnicodeError, ValueError):
                continue
            if not isinstance(data, dict) or not isinstance(data.get("faults"), list):
                continue
            faults = data["faults"]
            if any(type(fault) is not int or not 0 <= fault < len(columns) for fault in faults):
                continue
            if len(set(faults)) != len(faults):
                continue
            syndrome = 0
            logical_parity = 0
            for fault in faults:
                syndrome ^= columns[fault]
                logical_parity ^= model["observable"][fault]
            valid = bool(faults) and len(faults) <= model["weight_bound"] and syndrome == 0 and logical_parity == 1
            candidates.append({
                "artifact": str(artifact.relative_to(concept)),
                "weight": len(faults),
                "detector_weight": syndrome.bit_count(),
                "logical_parity": logical_parity,
                "valid_witness": valid,
            })
        exact_weights = [candidate["weight"] for candidate in candidates if candidate["detector_weight"] == 0 and candidate["logical_parity"] == 1]
        results.append({
            "attempt": attempt,
            "candidate_count": len(candidates),
            "passing_candidates": sum(candidate["valid_witness"] for candidate in candidates),
            "best_exact_logical_weight": min(exact_weights, default=None),
            "candidates": candidates,
        })
    report = {"passed": not any(result["passing_candidates"] for result in results), "attempts": results}
    destination = concept / "adversary/fresh_candidate_audit.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"no_passing_candidate": report["passed"], "attempts": [{key: value for key, value in result.items() if key != "candidates"} for result in results]}))


if __name__ == "__main__":
    main()
