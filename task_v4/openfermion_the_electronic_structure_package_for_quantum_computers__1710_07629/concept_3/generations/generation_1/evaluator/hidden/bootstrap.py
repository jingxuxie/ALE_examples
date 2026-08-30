"""Builder-only copies; writes exclusively inside this new generation."""

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parents[1]


def main():
    paths = [
        "participant/score.py", "participant/make_request.py",
        "participant/input/metrics.py", "participant/input/scoring.json",
        "participant/input/distribution.py", "participant/input/SCHEMA.md",
        "participant/input/ENVIRONMENT.md", "participant/input/DEVELOPMENT.md",
        "participant/input/example_request.json", "participant/input/example_predictions.json",
        "participant/baseline/features.py", "participant/baseline/train.py", "participant/baseline/solver.py",
        "evaluator/evaluate.py", "evaluator/isolation.py", "evaluator/scoring.py", "evaluator/settings.json",
        "evaluator/test_evaluator.py", "evaluator/test_isolation.py", "evaluator/run_checks.py",
        "evaluator/hidden/exact.py", "evaluator/hidden/validate_source.py",
        "evaluator/hidden/build_data.py", "adversary/fixture.py",
    ]
    sources = {relative: ORIGINAL / relative for relative in paths}
    pilot = ORIGINAL / "adversary/scale_pilot"
    sources["evaluator/hidden/native_reference.py"] = pilot / "reference/native_reference.py"
    sources["evaluator/hidden/reference_matvec.cpp"] = pilot / "reference_matvec.cpp"
    champion = ORIGINAL / "champions/generation_1"
    for name in ("solver.py", "physics.py", "hubbard.cpp"):
        sources["participant/baseline_exact/" + name] = champion / name
    patch = "*** Begin Patch\n"
    lineage = {}
    for relative, source in sources.items():
        destination = ROOT / relative
        if destination.exists():
            raise RuntimeError(f"Refusing to overwrite {destination}")
        content = source.read_bytes()
        lineage[relative] = {"source": str(source), "sha256": hashlib.sha256(content).hexdigest()}
        patch += f"*** Add File: {destination}\n"
        patch += "".join("+" + line + "\n" for line in content.decode().splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    for source, relative in ((champion / "hubbard.so", "participant/baseline_exact/hubbard.so"),
                             (pilot / "reference_matvec.so", "evaluator/hidden/reference_matvec.so")):
        content = source.read_bytes()
        (ROOT / relative).write_bytes(content)
        lineage[relative] = {"source": str(source), "sha256": hashlib.sha256(content).hexdigest()}
    snapshot = json.loads((pilot / "lineage.json").read_text())["snapshot"]
    comparisons = {}
    for name in ("hubbard.cpp", "hubbard.so", "physics.py", "solver.py"):
        final_hash = hashlib.sha256((champion / name).read_bytes()).hexdigest()
        comparisons[name] = {"pilot_sha256": snapshot[name]["sha256"],
                             "final_sha256": final_hash, "identical": snapshot[name]["sha256"] == final_hash}
    report = {"copies": lineage, "pilot_vs_final_champion": comparisons,
              "original_files_modified": False, "champion_dimension_adaptation": "none"}
    (ROOT / "evaluator/hidden/lineage.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(comparisons, indent=2))


if __name__ == "__main__":
    main()
