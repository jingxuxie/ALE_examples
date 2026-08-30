import json
from pathlib import Path

from generate import ROOT, create_case


def main():
    hidden = ROOT / "evaluator/hidden"
    archive = hidden / "pilot_v1"
    if archive.exists():
        raise RuntimeError("pilot already archived")
    archive.mkdir()
    (archive / "cases").mkdir()
    metadata = json.loads((hidden / "generation.json").read_text())
    (hidden / "generation.json").rename(archive / "generation.json")
    for details in metadata:
        if details["development"]:
            continue
        name = details["case_id"]
        (hidden / "cases" / (name + ".json")).rename(archive / "cases" / (name + ".json"))
        case, replacement = create_case(name, details["family"], tuple(details["shape"]), details["seed"])
        replacement["development"] = False
        details.clear()
        details.update(replacement)
        (hidden / "cases" / (name + ".json")).write_text(json.dumps(case, separators=(",", ":")) + "\n")
    for kind in ("baseline", "multistart", "expensive"):
        destination = ROOT / "attempts" / ("pilot_v1_" + kind)
        destination.mkdir()
        for path in (ROOT / "attempts" / kind).glob("h*.*"):
            path.rename(destination / path.name)
    (hidden / "generation.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (archive / "REJECTED.txt").write_text("Pre-freeze builder pilot rejected: 54-second generic random-phase L-BFGS multistart passed the fixed quality thresholds. No fresh agent ran. Final cases retain the same physical vector-potential construction, positive stiffness, families, shapes and target thresholds; larger physical lattice spacing and narrower, fewer pins increase discrete vortex trapping. This is explicitly a finite-lattice model, not a continuum-accuracy claim.\n")


if __name__ == "__main__":
    main()
