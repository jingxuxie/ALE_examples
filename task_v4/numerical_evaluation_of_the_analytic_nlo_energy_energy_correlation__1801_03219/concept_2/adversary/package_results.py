"""Promote only independently confirmed witnesses and record final evidence."""

import hashlib
import json
from pathlib import Path

import numpy as np

from search import ROOT, Kernel, save
from problem import FAMILIES, load_witness, validate, weight
from local_api import measure
from target import integrate


def main():
    witness = load_witness(ROOT / "adversary/best_screen")
    report = json.loads((ROOT / "adversary/best_screen/report.json").read_text())
    confirmation = json.loads((ROOT / "adversary/native_confirmation.json").read_text())
    if confirmation["witness"] != witness or not confirmation["resolved"]:
        raise RuntimeError("native verification is incomplete or is for another witness")
    for reference, native in zip(report["reference"]["fine"]["value"], confirmation["native_fine"]["value"]):
        if abs(float(reference) - float(native)) > 1e-18:
            raise RuntimeError("grade and native confirmation do not describe the same moment")
    frozen = json.loads((ROOT / "adversary/presearch_hashes.json").read_text())
    for name, expected in frozen.items():
        if hashlib.sha256((ROOT / "participant/input" / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("target, domain or kernel changed after search")
    kernel = Kernel()
    positions = (np.arange(16384) + .5) / 16384
    values = weight(positions, witness)
    energy = values**2
    quarter_fractions = [float(chunk.sum() / energy.sum()) for chunk in np.array_split(energy, 4)]
    perturbations = []
    for index in range(12):
        perturbed = json.loads(json.dumps(witness))
        name = "cosine" if index % 2 else "sine"
        perturbed[name][index] += 1 if index % 3 else -1
        validate(perturbed)
        result = measure(perturbed, kernel=kernel)
        perturbations.append({"array": name, "index": index, "worst_screen_margin": result["worst_screen_margin"]})
    controls = []
    for index in range(3):
        control = {"version": 1, "bin": witness["bin"], "band_start": witness["band_start"],
                   "tilt": witness["tilt"], "curvature": witness["curvature"],
                   "cosine": [0] * 12, "sine": [0] * 12}
        control["cosine"][index * 5] = 10**10
        result = measure(control, kernel=kernel)
        controls.append({"mode_offset": index * 5, "worst_screen_margin": result["worst_screen_margin"],
                         "panels": {family: result["families"][family]["target"]["panels"] for family in FAMILIES}})
    diagnostics = {"response_weight_quarter_energy_fractions": quarter_fractions,
                   "dense_response_weight_rms": float(np.sqrt(energy.mean())),
                   "dense_max_abs_weight": float(np.max(np.abs(values))),
                   "one_quantum_perturbations": perturbations,
                   "same_band_single_mode_controls": controls,
                   "qualification": "Perturbations and controls are public screening diagnostics, not separately native-certified champions."}
    save("adversary/robustness_diagnostics.json", diagnostics)
    baseline = json.loads((ROOT / "attempts/baseline/report.json").read_text())
    known = report["passed"] and confirmation["resolved"]
    champion_path = None
    if known:
        champion_path = "champions/privileged/witness.json"
        save(champion_path, witness)
        save("champions/privileged/report.json", report)
        save("champions/privileged/native_confirmation.json", confirmation)
    else:
        save("attempts/privileged_best/witness.json", witness)
        save("attempts/privileged_best/report.json", report)
        save("attempts/privileged_best/native_confirmation.json", confirmation)
    summary_keys = ("core_score", "worst_family_score", "runtime_score", "resource_score", "passed", "valid")
    status = {"concept": "concept_2", "mode": "B", "state": "builder_complete",
              "target_frozen": True, "participant_ready": True,
              "fresh_agents_launched_here": 0, "fresh_attempts": "Two independent attempts are owned by the main orchestrator; not claimed by this builder.",
              "achievability": "known_private_witness" if known else "unknown",
              "champion": champion_path,
              "baseline": dict({key: baseline[key] for key in summary_keys}, report="attempts/baseline/report.json"),
              "privileged_best": {key: report[key] for key in summary_keys},
              "frozen_manifest": "evaluator/hidden/frozen_manifest.json",
              "native_confirmation": "adversary/native_confirmation.json",
              "numerical_tests": {"passed": 4, "failed": 0, "log": "adversary/numerical_tests.log"},
              "concerns": ["Reference convergence is extensively checked, not a rigorous interval enclosure.",
                           "Fresh-agent difficulty remains uncalibrated by this builder.",
                           "The mechanism is correlated adaptive-quadrature error, not a raw floating endpoint bug or a uniquely EEC phenomenon.",
                           "The main orchestrator's separate official ancillary-source audit is not represented as completed here."],
              "scope": "All builder-written files are inside concept_2; no concept_1, concept_3, shared authoring or prior-task files were modified."}
    save("status.json", status)
    print(json.dumps({"achievability": status["achievability"], "champion": champion_path,
                      "scores": status["privileged_best"], "native_gaps": confirmation["native_refinement_gaps"],
                      "source_surrogate_gaps": confirmation["native_vs_surrogate_gaps"],
                      "quarter_energy_fractions": quarter_fractions,
                      "perturbed_minimum_screen_margin": min(item["worst_screen_margin"] for item in perturbations)}, indent=2))


if __name__ == "__main__":
    main()
