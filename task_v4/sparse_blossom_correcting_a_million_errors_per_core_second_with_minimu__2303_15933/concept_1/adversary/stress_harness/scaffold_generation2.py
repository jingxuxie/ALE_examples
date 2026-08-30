import json
from pathlib import Path
import shutil
import subprocess

from common import ROOT, SIDE, digest_file


DESTINATION = ROOT / "generations/generation_2"


def write_json(path, value):
    path.relative_to(DESTINATION)
    path.write_text(json.dumps(value, indent=2) + "\n")


def add_file(relative, text):
    path = DESTINATION / relative
    if path.exists():
        raise ValueError("Refusing to overwrite: " + str(path))
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    if DESTINATION.exists():
        raise ValueError("Generation already exists")
    for relative in ["participant/input", "participant/baseline", "participant/workspace", "evaluator/hidden", "attempts", "champions", "adversary"]:
        (DESTINATION / relative).mkdir(parents=True)
    specs = json.loads((SIDE / "ratchet2_selected.json").read_text())["specs"]
    for spec in specs:
        spec["family"] = spec.pop("stress_group")
    original = (ROOT / "participant/input/models.py").read_text()
    prefix = original[:original.index("SPECS =")]
    functions = original[original.index("def make_model"):].replace("def make_model(spec):", "def make_uniform_model(spec):", 1)
    profile = (SIDE / "regimes.py").read_text().split("def make_stress_model(spec):", 1)[1]
    profile = "def make_model(spec):" + profile.replace("model = make_model(spec)", "model = make_uniform_model(spec)", 1)
    add_file("participant/input/models.py", prefix + "SPECS = " + repr(specs) + "\n\n\n" + functions + "\n\n" + profile)
    for relative in ["participant/input/worker.py", "participant/input/run_public.py", "participant/workspace/submission.py", "evaluator/evaluate.py"]:
        add_file(relative, (ROOT / relative).read_text())
    champion = ROOT / "champions/generation_1"
    for source, destination in [("submission.py", "submission.py"), ("decoder.cpp", "decoder.cpp"), ("Makefile", "Makefile")]:
        add_file("participant/baseline/" + destination, (champion / source).read_text())
    shutil.copy2(champion / "decoder.so", DESTINATION / "participant/baseline/decoder.so")
    shutil.copytree(ROOT / "participant/input/runtime", DESTINATION / "participant/input/runtime")
    for name in ["runtime_versions.json", "requirements.lock"]:
        shutil.copy2(ROOT / "participant/input" / name, DESTINATION / "participant/input" / name)
    record_provenance()


def record_provenance():
    champion = ROOT / "champions/generation_1"
    write_json(DESTINATION / "evaluator/hidden/baseline_provenance.json", dict(
        source="concept_1/champions/generation_1", promoted_by_main=True,
        files={name: digest_file(champion / name) for name in ["submission.py", "decoder.cpp", "decoder.so", "Makefile"]},
        official_report_sha256=digest_file(ROOT / "attempts/v_1_result.json"),
        official_report=json.loads((ROOT / "attempts/v_1_result.json").read_text()),
        code_only_exposed=True, original_frozen_sha256=digest_file(ROOT / "evaluator/hidden/frozen.json")))
    write_json(DESTINATION / "status.json", dict(status="BUILDING", mode="A_BASELINE_IMPROVEMENT", generation=2,
        ratchet_index=1, max_ratchets=3, parent_champion="concept_1/champions/generation_1", fresh_runner_launched=False))


if __name__ == "__main__":
    main()
