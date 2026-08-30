import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parents[1]


def add(relative, content):
    path = ROOT / relative
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n" + "\n".join("+" + line for line in content.splitlines()) + "\n*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)


def main():
    add("participant/workspace/core.py", (ORIGINAL / "participant/workspace/check.py").read_text().split("def check(data):")[0])
    add("evaluator/hidden/oracle.py", (ORIGINAL / "evaluator/hidden/oracle.py").read_text().split("def evaluate(artifact):")[0])
    for relative in ("participant/input/graph.json", "participant/input/witness.schema.json"):
        add(relative, (ORIGINAL / relative).read_text())
    add("participant/baseline/champion.json", (ORIGINAL / "champions/generation_1/witness.json").read_text())
    add("participant/baseline/generation_1_metrics.json", (ORIGINAL / "champions/generation_1/metrics.json").read_text())
    add("participant/baseline/selection.json", (ORIGINAL / "champions/generation_1/selection.json").read_text())
    add("adversary/known_witness.json", (ORIGINAL / "adversary/known_witness.json").read_text())
    spec = json.loads((ORIGINAL / "participant/input/spec.json").read_text())
    spec["generation"] = 2
    spec["local_calibration"] = {"families": ["rows", "columns"], "canonical_signs": "first +1, exclude all +1",
        "background_scales": [0.95, 1.05], "amplitude_interval": [-0.05, 0.05],
        "anchors": [round(-0.05 + 0.002 * index, 6) for index in range(51)],
        "targets": {"gap": 0.85, "opposite_posterior": 0.845, "syndrome_probability": 0.0000175},
        "preserve_expected_error_count": True, "full_local_box_claimed": False}
    spec["evaluation_seconds"] = 900
    spec["host_contention_is_failure"] = False
    add("participant/input/spec.json", json.dumps(spec, indent=2) + "\n")


if __name__ == "__main__":
    main()
