import json
from pathlib import Path


def rank(vectors):
    pivots = {}
    for value in vectors:
        while value:
            leading = value.bit_length() - 1
            if leading not in pivots:
                pivots[leading] = value
                break
            value ^= pivots[leading]
    return len(pivots)


def main():
    root = Path(__file__).resolve().parents[1]
    results = []
    for directory in (root / "participant/input", root / "evaluator/hidden/instances"):
        for path in sorted(directory.glob("*.json")):
            model = json.loads(path.read_text())
            if not isinstance(model, dict) or model.get("schema") != "detector-compression/v1":
                continue
            signatures = [signature for channel in model["channels"] for signature in channel["signatures"]]
            detector_mask = (1 << model["detectors"]) - 1
            detector_rank = rank([signature & detector_mask for signature in signatures])
            augmented_rank = rank(signatures)
            if augmented_rank <= detector_rank:
                raise RuntimeError("logical observable is a fixed linear detector parity: unintended shortcut")
            results.append({"instance": str(path.relative_to(root)), "detector_rank": detector_rank,
                            "augmented_rank": augmented_rank, "deterministic_linear_logical_shortcut": False})
    report = {"passed": True, "instances": results}
    (root / "adversary/structure_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
