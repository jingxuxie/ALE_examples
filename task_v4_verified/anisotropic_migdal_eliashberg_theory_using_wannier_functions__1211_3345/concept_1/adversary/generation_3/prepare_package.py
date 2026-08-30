"""Prepare an inactive final ratchet only after independently audited champion gaps."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
SIDECAR = ROOT / "adversary" / "prospective_generation3"
PACKAGE = PENDING / "package" / "concept_1"
sys.path.insert(0, str(SIDECAR))
from continuum_materials import make


def main():
    assert not PACKAGE.exists()
    selection = json.loads((PENDING / "selection.json").read_text())
    evidence = json.loads((SIDECAR / "continuum_audit.json").read_text())
    assert evidence["passed"] and len(evidence["cases"]) == 4
    assert set(selection["replacements"].values()) == {record["case_id"] for record in evidence["cases"]}
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    for relative, expected in protocol["active_sealed_files"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    texts, binaries = {}, {}
    for source in sorted((ROOT / "participant").rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.name == "baseline_result.json":
            continue
        assert not source.is_symlink()
        target = PACKAGE / source.relative_to(ROOT)
        if source.suffix == ".npz":
            binaries[target] = source.read_bytes()
        else:
            texts[target] = source.read_text()
    task_path = PACKAGE / "participant" / "TASK.md"
    task = texts[task_path].replace("and resource use important. A small residual alone is not success.",
                                   "and resource use important. Some materials resolve smooth anisotropic phonon\nspectra using dozens of distinct quadrature bins. A small residual alone is not success.")
    texts[task_path] = task
    texts[PACKAGE / "TASK.md"] = task
    format_path = PACKAGE / "participant" / "input" / "FORMAT.md"
    documentation = texts[format_path]
    documentation = documentation.replace("Strictly positive Einstein-mode energies", "Strictly positive phonon energies: discrete modes or spectral quadrature nodes")
    documentation = documentation.replace("are 9–40 patches, 3–4 modes, and 192–32768 positive frequencies.",
                                           "are 9–40 patches, 3–96 phonon nodes, and 192–32768 positive frequencies.")
    documentation = documentation.replace("weak interband coupling with induced small gaps; and a combination of the last\nthree.",
                                           "weak interband coupling with induced small gaps; and combinations including\nlow-temperature, spectrally resolved interactions.")
    documentation = documentation.replace("The finest-grid cases have maximum phonon energy divided by temperature equal", "The four-mode finest-grid cases have maximum phonon energy divided by temperature equal")
    documentation += """

## Resolved phonon spectra

In addition to few-mode models, inputs can contain up to 96 distinct positive
phonon quadrature nodes. They can represent smooth multimodal spectral support
with energy-dependent anisotropy: different nodes need not have proportional
or commuting patch interaction matrices. Integrated patch couplings remain
moderate, rather than growing with the number of quadrature nodes. These are
independent spectral samples, not duplicated modes or padded arrays.

For a positive log-energy quadrature with weights q[s], the convention is
`A[s,a,b] = 2 * alpha2F[a,b,Omega[s]] * q[s]`. Thus `sum_s A[s,a,b]`
is the integrated dimensionless patch coupling. The kernel and nonlinear map
are exactly the same finite sums specified above; no new input field or API
is required. A numerical spectral quadrature is equivalently the discrete
spectral measure already defined in this document.

Resolved-spectrum examples use positive smooth multimodal profiles over
bounded phonon windows, with varying symmetric patch-pair spectra and optional
weak links between sheets. The Matsubara cutoff remains about 17.16 times the
physical upper end of that window. Quadrature nodes lie inside the support,
so the largest node is slightly below the physical upper end. Some such
materials have well-developed gaps and induced weak-sheet gaps; they do not
require pushing a pairing instability toward machine precision.

`examples/phonon_continuum_96.npz` is an independent public development draw
with 96 nodes, 4096 positive frequencies and 12 patches. It contains only the
seven public arrays, not band labels, eigenvalues or reference solutions.
The exact supplied finite problem is scored, not convergence to an infinite
Matsubara cutoff or to a continuous phonon integral. The original public
operator, derivative API, baseline, resource limits and quality gates remain
unchanged.
"""
    texts[format_path] = documentation
    example_specification = {"case_id": "phonon_continuum_96", "family": "combined", "seed": 33990167,
                             "n_freq": 4096, "patches": 12, "n_modes": 96, "max_phonon_over_temperature": 1500,
                             "mode_span": 1400, "sheet_lambda": [0.64, 0.46, 0.28],
                             "sheet_coulomb": [0.08, 0.10, 0.12], "interband_factor": 0.0003}
    example, metadata, unused_spectrum = make(example_specification)
    texts[PENDING / "public_example_generation.json"] = json.dumps(metadata, indent=2) + "\n"
    policy = json.loads((ROOT / "evaluator" / "hidden" / "policy.json").read_text())
    policy.update(version="concept1-modeA-generation3-v1", frozen_at=datetime.now(timezone.utc).isoformat())
    texts[PACKAGE / "evaluator" / "hidden" / "policy.json"] = json.dumps(policy, indent=2) + "\n"
    for name in ("evaluate.py", "launch.py", "README.md", "hidden/physics.py"):
        texts[PACKAGE / "evaluator" / name] = (ROOT / "evaluator" / name).read_text()
    texts[PACKAGE.parent / "authoring" / "sandbox_runner.py"] = (ROOT.parent / "authoring" / "sandbox_runner.py").read_text()
    manifest = json.loads((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
    manifest["generation"] = 3
    retained = {}
    for index, record in enumerate(manifest["cases"]):
        case_id = record["case_id"]
        if case_id in selection["replacements"]:
            probe_id = selection["replacements"][case_id]
            source = SIDECAR / "continuum_cases" / probe_id
            parameters = json.loads((source / "parameters.json").read_text())
            certificate = json.loads((source / "certificate.json").read_text())
            assert certificate["valid"] and parameters["n_modes"] == 96
            manifest["cases"][index] = dict(parameters, case_id=case_id, source_probe=probe_id)
            for folder, filename in (("cases", "instance.npz"), ("references", "reference.npz")):
                binaries[PACKAGE / "evaluator" / "hidden" / folder / (case_id + ".npz")] = (source / filename).read_bytes()
            texts[PACKAGE / "evaluator" / "hidden" / "references" / (case_id + ".json")] = json.dumps(dict(certificate, case_id=case_id, source_probe=probe_id), indent=2) + "\n"
        else:
            for folder in ("cases", "references"):
                relative = Path(folder) / (case_id + ".npz")
                contents = (ROOT / "evaluator" / "hidden" / relative).read_bytes()
                binaries[PACKAGE / "evaluator" / "hidden" / relative] = contents
                retained[str(relative)] = hashlib.sha256(contents).hexdigest()
            relative = Path("references") / (case_id + ".json")
            texts[PACKAGE / "evaluator" / "hidden" / relative] = (ROOT / "evaluator" / "hidden" / relative).read_text()
    texts[PACKAGE / "evaluator" / "hidden" / "manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    texts[PACKAGE / "adversary" / "retained_case_hashes.json"] = json.dumps(retained, indent=2) + "\n"
    texts[PACKAGE / "adversary" / "continuum_evidence.json"] = json.dumps(evidence, indent=2) + "\n"
    for folder in ("attempts", "champions", "adversary"):
        texts[PACKAGE / folder / "README.md"] = "# Private generation-3 " + folder + "\n\nNot exposed to participants. No new fresh trial has been launched.\n"
    for name in ("test_generation.py", "test_security.py"):
        texts[PACKAGE / "adversary" / name] = (ROOT / "adversary" / name).read_text()
    texts[PACKAGE / "adversary" / "test_ratchet.py"] = (PENDING / "test_generation3.py").read_text()
    texts[PACKAGE / "status.json"] = json.dumps({
        "concept": "concept_1", "generation": 3, "ratchet_index": 3, "ratchet_limit": 3, "active": False,
        "status": "pending_baseline_measurement_and_parent_review", "verification_mode": "A",
        "difficulty_status": "provisional_final_ratchet_candidate", "fresh_agent_launched_by_builder": False,
        "prior_fresh_code_shipped_to_participant": False, "selection": selection,
        "public_baseline_sha256": hashlib.sha256((ROOT / "participant" / "baseline" / "solve.py").read_bytes()).hexdigest(),
        "joint_speed_quality_attainability": "unknown_for_generation_3; offline certificates are not a joint witness",
        "previous_generation_attainability": "verified_by_actual_fresh_v4"}, indent=2) + "\n"
    for name in ("generation_2_snapshot_manifest.json", "generation_2_archive_smoke.json"):
        texts[PENDING / name] = (SIDECAR / name).read_text()
    patch = "*** Begin Patch\n"
    for path, content in texts.items():
        patch += "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in content.splitlines())
    subprocess.run(["apply_patch"], input=patch + "*** End Patch\n", text=True, check=True)
    for path, content in binaries.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    np.savez_compressed(PACKAGE / "participant" / "input" / "examples" / "phonon_continuum_96.npz", **example)
    shutil.copyfile(SIDECAR / "generation_2_runnable_snapshot.tar.gz", PENDING / "generation_2_runnable_snapshot.tar.gz")
    for folder in ("baseline", "workspace"):
        assert (PACKAGE / "participant" / folder / "solve.py").read_bytes() == (ROOT / "participant" / folder / "solve.py").read_bytes()
    print(json.dumps({"package": str(PACKAGE), "active": False, "numerical_target_unchanged": True,
                      "original_public_baseline_unchanged": True, "retained_cases": 16, "new_public_example": "phonon_continuum_96.npz"}))


if __name__ == "__main__":
    main()
