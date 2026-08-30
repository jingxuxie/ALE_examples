"""Build inactive generation two, retaining only original public solver code."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from materials import make


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
PACKAGE = PENDING / "package" / "concept_1"


def main():
    if PACKAGE.exists():
        raise FileExistsError("pending package already exists")
    selection = json.loads((PENDING / "selection.json").read_text())
    for probe_id in selection["replacements"].values():
        directory = PENDING / "cases" / probe_id
        certificate = json.loads((directory / "certificate.json").read_text())
        measurement = json.loads((directory / "measurement.json").read_text())
        assert certificate["valid"] and not measurement["actual_v3_accepted"]
        assert measurement["quality"]["branch_error"] > 20 * 0.002
    texts = {}
    binaries = {}
    for source in sorted((ROOT / "participant").rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.name == "baseline_result.json":
            continue
        assert not source.is_symlink()
        target = PACKAGE / source.relative_to(ROOT)
        if source.suffix == ".npz":
            binaries[target] = source.read_bytes()
        else:
            texts[target] = source.read_text()
    task = texts[PACKAGE / "participant" / "TASK.md"]
    task = task.replace("Fine anisotropic patch models and low\ntemperatures make numerical convergence and resource use important.",
                        "Fine anisotropic patch models, very close or sheet-selective pairing\ninstabilities, weak induced gaps, and low temperatures make branch correctness\nand resource use important. A small residual alone is not success.")
    texts[PACKAGE / "participant" / "TASK.md"] = task
    texts[PACKAGE / "TASK.md"] = task
    format_path = PACKAGE / "participant" / "input" / "FORMAT.md"
    documentation = texts[format_path]
    documentation = documentation.replace("weak-interband factors are between about 3e-8 and 3e-5;\nnear-critical leading eigenvalues are 1 + 2e-5 through 1 + 3e-3.",
                        "weak-interband factors can extend down to 1e-12;\nnear-critical global or isolated-sheet eigenvalue excesses can be as small as\n3e-9. Some weakly linked sheets lie slightly below their isolated instability\nwhile another sheet is superconducting.")
    documentation += """

## Sheet-selective and near-critical regimes

The declared grid and patch limits remain unchanged. New conditioning cases
use 1536–4096 positive frequencies and 9–15 patches, while the earlier larger
grids remain part of the suite. Positive four-mode spectra retain multiple
retardation scales. Repulsive intraband Coulomb terms can produce high-frequency
sign reversals even though all target low-frequency gaps share one sign.

Some materials are globally very close to their pairing instability. Others
have several weakly linked sheets near distinct isolated-sheet instabilities:
one gap can be well developed while another is extremely sensitive to the
coupling and temperature. The overall leading eigenvalue does not by itself
describe every sheet's nonlinear conditioning. Band labels and eigenvalues are
not inputs. Exact matrices and quadrature weights, including their independent
anisotropy, define the problem; patches and modes are not duplicated padding.

These synthetic finite-patch stress regimes are not predictions of experimentally
resolvable transition-temperature differences. Weak-interband hidden criticality
is motivated by Komendova et al., arXiv:1203.6837 (2012); this benchmark does not
claim to reproduce that paper's microscopic model. The original Margine–Giustino
finite imaginary-axis equations, nonzero same-sign branch, residual norms,
branch-distance threshold, and computational resources are unchanged.

`examples/critical_coulomb_3072.npz` and
`examples/competing_sheets_2304.npz` are independent public development draws
from these regimes, not hidden fixtures or reference solutions. The two new
examples contain only the seven public input arrays, just like all other inputs.
"""
    texts[format_path] = documentation
    public_specs = [
        {"case_id": "critical_coulomb_3072", "family": "critical", "seed": 280390031,
         "n_freq": 3072, "patches_per_band": 9, "max_phonon_over_temperature": 2400,
         "mode_ratios": [0.0012, 0.028, 0.27, 1], "global_target": 1.00000002, "coulomb_strength": 0.12},
        {"case_id": "competing_sheets_2304", "family": "combined", "seed": 283130057,
         "n_freq": 2304, "patches_per_band": 4, "max_phonon_over_temperature": 1800,
         "mode_ratios": [0.002, 0.027, 0.3, 1], "sheet_targets": [1.004, 1.00000001, 0.999998],
         "interband_factor": 2e-11, "coulomb_strength": [0.04, 0.11, 0.07]},
    ]
    public_inputs = []
    public_metadata = []
    for specification in public_specs:
        instance, metadata, unused = make(specification)
        public_inputs.append((specification["case_id"], instance))
        public_metadata.append(metadata)
    texts[PENDING / "public_example_generation.json"] = json.dumps(public_metadata, indent=2) + "\n"
    policy = json.loads((ROOT / "evaluator" / "hidden" / "policy.json").read_text())
    policy.update(version="concept1-modeA-generation2-v1", frozen_at=datetime.now(timezone.utc).isoformat())
    texts[PACKAGE / "evaluator" / "hidden" / "policy.json"] = json.dumps(policy, indent=2) + "\n"
    for filename in ("evaluate.py", "launch.py", "README.md"):
        texts[PACKAGE / "evaluator" / filename] = (ROOT / "evaluator" / filename).read_text().replace("generation-1", "generation-2") if filename == "README.md" else (ROOT / "evaluator" / filename).read_text()
    texts[PACKAGE / "evaluator" / "hidden" / "physics.py"] = (ROOT / "evaluator" / "hidden" / "physics.py").read_text()
    texts[PACKAGE.parent / "authoring" / "sandbox_runner.py"] = (ROOT.parent / "authoring" / "sandbox_runner.py").read_text()
    manifest = json.loads((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
    manifest["generation"] = 2
    for index, record in enumerate(manifest["cases"]):
        case_id = record["case_id"]
        if case_id in selection["replacements"]:
            probe_id = selection["replacements"][case_id]
            source = PENDING / "cases" / probe_id
            metadata = json.loads((source / "parameters.json").read_text())
            manifest["cases"][index] = dict(metadata, case_id=case_id, source_probe=probe_id)
            binaries[PACKAGE / "evaluator" / "hidden" / "cases" / (case_id + ".npz")] = (source / "instance.npz").read_bytes()
            binaries[PACKAGE / "evaluator" / "hidden" / "references" / (case_id + ".npz")] = (source / "reference.npz").read_bytes()
            certificate = json.loads((source / "certificate.json").read_text())
            certificate.update(case_id=case_id, source_probe=probe_id)
            texts[PACKAGE / "evaluator" / "hidden" / "references" / (case_id + ".json")] = json.dumps(certificate, indent=2) + "\n"
        else:
            for folder in ("cases", "references"):
                source = ROOT / "evaluator" / "hidden" / folder / (case_id + ".npz")
                binaries[PACKAGE / "evaluator" / "hidden" / folder / source.name] = source.read_bytes()
            source = ROOT / "evaluator" / "hidden" / "references" / (case_id + ".json")
            texts[PACKAGE / "evaluator" / "hidden" / "references" / source.name] = source.read_text()
    texts[PACKAGE / "evaluator" / "hidden" / "manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    for folder in ("attempts", "champions", "adversary"):
        texts[PACKAGE / folder / "README.md"] = "# Private generation-2 " + folder + "\n\nNot exposed to participants. No new fresh trial has been launched.\n"
    for filename in ("test_generation.py", "test_security.py"):
        texts[PACKAGE / "adversary" / filename] = (ROOT / "adversary" / filename).read_text()
    texts[PACKAGE / "status.json"] = json.dumps({
        "concept": "concept_1", "generation": 2, "ratchet_index": 2, "ratchet_limit": 3,
        "active": False, "status": "pending_measurement_and_parent_review", "verification_mode": "A",
        "difficulty_status": "provisional_ratchet_candidate", "fresh_agent_launched_by_builder": False,
        "prior_fresh_code_shipped_to_participant": False, "public_baseline_sha256": hashlib.sha256((ROOT / "participant" / "baseline" / "solve.py").read_bytes()).hexdigest(),
        "selection": selection, "joint_speed_quality_attainability": "not_established_for_generation_2",
        "previous_generation_attainability": "verified_by_actual_fresh_v3"}, indent=2) + "\n"
    patch = "*** Begin Patch\n"
    for path, contents in texts.items():
        patch += "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in contents.splitlines())
    subprocess.run(["apply_patch"], input=patch + "*** End Patch\n", text=True, check=True)
    for path, contents in binaries.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    for name, instance in public_inputs:
        np.savez_compressed(PACKAGE / "participant" / "input" / "examples" / (name + ".npz"), **instance)
    for directory in ("baseline", "workspace"):
        assert (PACKAGE / "participant" / directory / "solve.py").read_bytes() == (ROOT / "participant" / directory / "solve.py").read_bytes()
    print(json.dumps({"prepared": str(PACKAGE), "active": False, "numerical_thresholds_unchanged": True,
                      "baseline_and_workspace_unchanged": True, "large_grid_cases_retained": True}))


if __name__ == "__main__":
    main()
