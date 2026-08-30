import json
from pathlib import Path
import subprocess


CONCEPT = Path(__file__).resolve().parent.parent
SOURCE = CONCEPT / "generations/generation_2"
TARGET = CONCEPT / "generations/generation_3"


def add(relative, contents):
    destination = TARGET / relative
    if destination.exists():
        raise FileExistsError(destination)
    patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n"
    patch += "".join("+" + line + "\n" for line in contents.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    copies = {
        "participant/input/graph.json": "participant/input/graph.json",
        "participant/input/witness.schema.json": "participant/input/witness.schema.json",
        "participant/workspace/core.py": "participant/workspace/core.py",
        "participant/workspace/check.py": "participant/workspace/inherited.py",
        "evaluator/hidden/oracle.py": "evaluator/hidden/inherited_oracle.py",
        "evaluator/hidden/full_state.cpp": "evaluator/hidden/full_state.cpp",
        "evaluator/evaluate.py": "evaluator/evaluate.py",
    }
    for source, destination in copies.items():
        contents = (SOURCE / source).read_text()
        if destination == "evaluator/evaluate.py":
            contents = contents.replace("generation_two_trusted_oracle", "generation_three_trusted_oracle")
        add(destination, contents)
    add("participant/baseline/champion.json", (CONCEPT / "champions/generation_2/witness.json").read_text())
    original = json.loads((CONCEPT / "champions/generation_2/metrics.json").read_text())
    add("participant/baseline/generation_2_metrics.json", json.dumps({key: value for key, value in original.items() if key != "groups"}, indent=2))
    add("participant/baseline/selection.json", (CONCEPT / "champions/generation_2/selection.json").read_text())
    specification = json.loads((SOURCE / "participant/input/spec.json").read_text())
    specification["generation"] = 3
    specification["orientation_calibration"] = {
        "edge_orientation": "horizontal including boundary +1; vertical -1",
        "detector_fields": ["constant +1", "all 7 canonical nonconstant row signs", "all 15 canonical nonconstant column signs", "all 20 products of a single-negative-row field and a single-negative-column field"],
        "raw_edge_field": "orientation times endpoint-average detector field",
        "directions": 43,
        "background_scales": [0.95, 1.05],
        "amplitude_interval": [-0.05, 0.05],
        "anchors": [round(-0.05 + 0.0025 * index, 6) for index in range(41)],
        "targets": dict(specification["local_calibration"]["targets"]),
        "certificate": "adjacent-endpoint Lipschitz cones with interval-specific derivative bound",
        "preserve_expected_error_count": True,
        "full_multidimensional_box_claimed": False,
    }
    specification["inference_points"] = 5791
    add("participant/input/spec.json", json.dumps(specification, indent=2))


if __name__ == "__main__":
    main()
