"""Construct a review-only package. Previous fresh code is never public."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
PACKAGE = PENDING / "package" / "concept_1"


TASK = """# Branch-correct anisotropic Eliashberg solver

## Mission
Improve the supplied public nonlinear imaginary-axis baseline. Recover the
nonzero same-sign superconducting branch across multiband, retarded-scale,
nearly critical, weak-interband, and combined materials. Physics operators and
their derivative API are supplied. Fine anisotropic patch models and low
temperatures make numerical convergence and resource use important.

## Assets
`input/` contains the operator, public instances, baseline measurement, and
`FORMAT.md`. `workspace/solve.py` is the editable starting submission;
`baseline/solve.py` is the supplied public baseline. Paths here are relative to
this participant directory. Set `OUTPUT_DIR` to the writable output directory
specified by the launch prompt when running development examples.

## Interface
Submit a directory containing `solve.py`, invoked as
`python solve.py --input FILE --output FILE`. Write finite float arrays `delta`
and `z` in one NPZ. Package all required code/assets in your output directory.
Detailed equations, dimensions, and the helper API are in `input/FORMAT.md`.

## Objective
Solve at least 18 of 20 hidden instances and at least 3 of 4 in every family,
and improve worst-family acceptance by at least 0.25 over the measured supplied
public baseline. Normal-state solutions, wrong relative signs, and inaccurate
weak gaps do not receive credit.

## Resources
Pure single-process Python with NumPy/SciPy; one thread; no external processes,
network, or private-file access. Every fresh invocation gets 12 total CPU seconds
including startup, 2048 MiB address space, and an 1800-second wall safety ceiling.
Wall time is not a performance score. Submitted code/assets must fit in 32 MiB;
the output file and its expanded NPZ payload must each fit in 32 MiB.

## Scoring
Score is the minimum of the five family acceptance fractions. Each accepted
case must have independently checked normalized gap residual <= `2e-8`,
renormalization residual <= `2e-9`, and maximum per-patch normalized distance
to the certified branch <= `0.002`, with correct low-frequency relative signs.
A single global sign reversal is equivalent. Every quality and resource gate
is mandatory; exact norms and parameter ranges are in `input/FORMAT.md`.
"""


def main():
    selection = json.loads((PENDING / "selection.json").read_text())
    if PACKAGE.exists():
        raise FileExistsError("pending package already exists; do not overwrite a sealed package")
    for case_id, probe_id in selection["replacements"].items():
        directory = PENDING / "probes" / probe_id
        certificate_path = directory / "oracle_certificate.json" if (directory / "oracle_certificate.json").exists() else directory / "certificate.json"
        certificate = json.loads(certificate_path.read_text())
        measurement = json.loads((directory / "measurement.json").read_text())
        if not certificate["valid"] or not measurement["resource_failure_well_outside_12_cpu"]:
            raise ValueError("selected stress case is not certified and robustly failing: " + probe_id)
    policy = json.loads((ROOT / "evaluator" / "hidden" / "policy.json").read_text())
    policy.update(version="concept1-modeA-generation1-v1", frozen_at=datetime.now(timezone.utc).isoformat(),
                  output_bytes_max=32 * 1024 ** 2)
    texts = {}
    binaries = {}
    for source in sorted((ROOT / "participant").rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.name in ("baseline_result.json", "TASK.md"):
            continue
        relative = source.relative_to(ROOT)
        if source.suffix == ".npz":
            binaries[PACKAGE / relative] = source.read_bytes()
        else:
            texts[PACKAGE / relative] = source.read_text()
    public_baseline = (ROOT / "participant" / "baseline" / "solve.py").read_text()
    texts[PACKAGE / "participant" / "baseline" / "solve.py"] = public_baseline
    texts[PACKAGE / "participant" / "workspace" / "solve.py"] = public_baseline
    texts[PACKAGE / "TASK.md"] = TASK
    texts[PACKAGE / "participant" / "TASK.md"] = TASK
    format_path = PACKAGE / "participant" / "input" / "FORMAT.md"
    documentation = texts[format_path]
    documentation = documentation.replace("16 MiB", "32 MiB")
    documentation = documentation.replace("9–25 patches", "9–40 patches")
    documentation = documentation.replace("192–2048", "192–32768")
    documentation = documentation.replace("ratios reach 55.6", "ratios reach 4000")
    documentation = documentation.replace("private scoring uses its\nown blocked direct sums", "private scoring uses an\nindependent full-signed linear-convolution operator validated against direct sums")
    documentation = documentation.replace("References have direct-sum normalized\nresiduals below", "References have independently verified normalized\nresiduals below")
    documentation = documentation.replace("Run a public example from the concept root with:", "Run a public example from the participant directory with:")
    documentation = documentation.replace("The five public examples", "The public examples")
    documentation += """

## Expanded physical regime

The maximum positive-frequency count is 32768 and the maximum patch count is
40. These are independently anisotropic Fermi-surface patches, not duplicated
padding. Each new patch has its own interaction weights and mode fractions.
The numerical materials are synthetic finite-patch models; no convergence of
a particular ab initio Fermi-surface mesh is claimed.

The finest-grid cases have maximum phonon energy divided by temperature equal
to 12000. Their last Matsubara frequency is approximately 17.16 times the
largest phonon energy. Increasing frequency count accompanies decreasing
temperature while preserving the physical frequency window, rather than adding
irrelevant zeros. Positive four-mode spectra can span factors of 1000–4000.
Near-critical interaction strengths are calibrated by the normal-state pairing
eigenvalue, while weak interband links can induce very small nonzero gaps.
The equations, common finite cutoff, sign conventions, and quality tolerances
are unchanged. The output allowance is 32 MiB to accommodate the larger arrays.

Private validation evaluates every returned frequency using an independently
implemented full-signed, zero-padded linear convolution of the exact kernel.
It has been cross-checked against full direct sums on smaller grids and direct
signed sums on distributed rows of every large reference. This is an exact
finite-sum implementation up to floating-point roundoff, not a frequency-tail
or coarse-grid approximation. References additionally have independent
starting-amplitude checks. Offline reference cost does not relax the submission
CPU or memory limits, and does not imply a known within-budget solver.
"""
    texts[format_path] = documentation
    pool = ROOT / "adversary" / "ratchet_pool"
    for example, pool_id in (("low_temperature_4096", "pool_08"), ("low_temperature_8192", "pool_09")):
        binaries[PACKAGE / "participant" / "input" / "examples" / (example + ".npz")] = (pool / "cases" / pool_id / "instance.npz").read_bytes()
    for filename in ("evaluate.py", "launch.py"):
        texts[PACKAGE / "evaluator" / filename] = (ROOT / "evaluator" / filename).read_text()
    texts[PACKAGE / "evaluator" / "hidden" / "physics.py"] = (PENDING / "verification.py").read_text()
    texts[PACKAGE / "evaluator" / "hidden" / "policy.json"] = json.dumps(policy, indent=2) + "\n"
    texts[PACKAGE.parent / "authoring" / "sandbox_runner.py"] = (ROOT.parent / "authoring" / "sandbox_runner.py").read_text()
    manifest = json.loads((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
    manifest["generation"] = 1
    for index, record in enumerate(manifest["cases"]):
        case_id = record["case_id"]
        if case_id in selection["replacements"]:
            probe_id = selection["replacements"][case_id]
            source = PENDING / "probes" / probe_id
            metadata = json.loads((source / "parameters.json").read_text())
            manifest["cases"][index] = dict(metadata, case_id=case_id, source_probe=probe_id)
            binaries[PACKAGE / "evaluator" / "hidden" / "cases" / (case_id + ".npz")] = (source / "instance.npz").read_bytes()
            binaries[PACKAGE / "evaluator" / "hidden" / "references" / (case_id + ".npz")] = (source / "reference.npz").read_bytes()
            certificate_path = source / "oracle_certificate.json" if (source / "oracle_certificate.json").exists() else source / "certificate.json"
            certificate = json.loads(certificate_path.read_text())
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
        texts[PACKAGE / folder / "README.md"] = "# Private generation-1 " + folder + "\n\nNot exposed to a tested participant. No fresh trial has been launched.\n"
    texts[PACKAGE / "evaluator" / "README.md"] = """# Pending generation-1 evaluator

Run `python evaluator/evaluate.py --submission participant/baseline --report attempts/baseline_report.json`.
The sibling `../authoring/sandbox_runner.py` is bundled at the unchanged expected
location. Numerical quality gates and 12-CPU-second/2048-MiB/one-thread resources
are unchanged; output parsing permits 32 MiB for the declared larger arrays.
The independent full-frequency verifier never imports submitted code. All
candidate execution still uses the shared Landlock/seccomp runner and local
clone guard. Previous fresh submissions are private and are not shipped in the
participant directory. Baseline improvement is anchored to the supplied public
damped solver, not the privileged previous fresh solver.
"""
    status = {"generation": 1, "ratchet_index": 1, "ratchet_limit": 3, "active": False,
              "status": "pending_measurement_and_parent_review", "verification_mode": "A",
              "difficulty_status": "provisional_ratchet_candidate", "fresh_generation_1_launched": False,
              "prior_fresh_code_shipped_to_participant": False,
              "public_baseline_sha256": hashlib.sha256(public_baseline.encode()).hexdigest(),
              "target": {"core_score_min": 0.90, "worst_family_score_min": 0.75, "improvement_min": 0.25},
              "selection": selection, "joint_speed_quality_attainability": "not_established"}
    texts[PACKAGE / "status.json"] = json.dumps(status, indent=2) + "\n"
    patch = "*** Begin Patch\n"
    for path, contents in texts.items():
        patch += "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in contents.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    for path, contents in binaries.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    fresh = (ROOT / "champions" / "generation_1" / "solve.py").read_bytes()
    for path in (PACKAGE / "participant").rglob("*.py"):
        if path.read_bytes() == fresh or "self.spectral" in path.read_text():
            raise ValueError("private fresh implementation leaked into public package")
    print(json.dumps({"prepared": str(PACKAGE), "active": False,
                      "public_baseline_is_original": True, "prior_fresh_code_public": False}))


if __name__ == "__main__":
    main()
