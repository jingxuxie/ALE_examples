import hashlib
import json
from pathlib import Path

from build_resilience_generation import replace_text


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"
PUBLIC = CONCEPT / "participant"
PRIVATE = CONCEPT / "evaluator/hidden"
EVIDENCE = CONCEPT / "adversary/generation_1"


def main():
    if not (CONCEPT / "generations/generation_0/freeze_manifest.json").exists():
        raise ValueError("archive the solved original generation first")
    original = json.loads((PUBLIC / "input/specification.json").read_text())
    if original.get("generation", 0) != 0:
        raise ValueError("this builder creates only phase generation 1")
    specification = json.loads((EVIDENCE / "selected_specification.json").read_text())
    evidence = json.loads((EVIDENCE / "champion_stress_audit.json").read_text())
    assert evidence["original_champion_passes"]
    assert evidence["selected_phase_radius"] == .008
    assert evidence["broad_random_scenarios"] >= 500
    assert specification["scenarios"][:5] == original["scenarios"]
    assert len(specification["scenarios"]) == 21
    for key, value in original.items():
        if key != "scenarios":
            assert specification[key] == value
    serialized = json.dumps(specification, indent=2) + "\n"
    replace_text(PUBLIC / "input/specification.json", serialized)
    replace_text(PRIVATE / "specification.json", serialized)
    manifest = {name: hashlib.sha256((PRIVATE / name).read_bytes()).hexdigest()
                for name in ("specification.json", "calibration.json")}
    replace_text(PRIVATE / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    task = '''# Falsify a calibration screen under independent phase drift

You are auditing a quantum-control team's claim that its compressed calibration screen certifies a qubit model for same-depth application circuits. Construct a physically valid coherent-leakage counterexample that remains a counterexample under the disclosed independent gate-phase tolerances: calibration accepts, but an application circuit has a large prediction error and little final leakage.

Assets: the exact processor family, reported CPTP model, calibration circuits, and tolerance scenarios in `input/`; a NumPy simulator in `workspace/screen.py`; and the previous-generation champion in `baseline/witness.json`. That champion is a runnable starting point, not a passing solution for this generation. This challenges the supplied screen's sufficiency, not a GST theorem.

Submit **one static `witness.json`** in the designated output directory. The complete interface is in `input/INTERFACE.md`. Run `python workspace/screen.py --witness PATH` for local measurements or `python baseline/search.py --output PATH` to emit the baseline. Submitted code is never executed by the evaluator.

A passing witness satisfies every calibration and held-out bound in **all 21 enumerated tolerance scenarios**, including the original common-mode scenarios and independent phase corners. The circuit has exactly 64 gates. Scores report nominal and worst-scenario prediction error plus constraint violations. All scientific acceptance criteria are public; probabilities are independently reproduced by the private evaluator.

Budget: one hour, four CPU cores, 4 GiB address space per process, no network. The JSON file is limited to 32 KiB. No report is required.
'''
    replace_text(PUBLIC / "TASK.md", task)
    interface = (PUBLIC / "input/INTERFACE.md").read_text()
    interface = interface.replace(
        'multiply all four coupling coordinates by `coupling_scale` and add `phase_shift` to all three phases, then construct both models anew. These five enumerated scenarios, not an entire continuous uncertainty interval, define robustness.',
        'multiply all four coupling coordinates by `coupling_scale`, then add `phase_shift` to the phases and construct both models anew. A scalar phase shift applies to all three gates; a three-element list applies separately in `I, X, Y` order. The 21 enumerated scenarios retain the original five common-mode checks and add the 16 corners formed by independent phase shifts of ±0.008 radians and coupling scales 0.98 or 1.02. These enumerated scenarios, not an entire continuous uncertainty interval, define robustness.')
    interface = interface.replace('over the five tolerance scenarios', 'over the 21 tolerance scenarios')
    assert 'These five enumerated' not in interface
    replace_text(PUBLIC / "input/INTERFACE.md", interface)
    baseline = '''import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "witness.json"
    Path(args.output).write_bytes(source.read_bytes())


if __name__ == "__main__":
    main()
'''
    replace_text(PUBLIC / "baseline/search.py", baseline)
    replace_text(PUBLIC / "baseline/witness.json",
                 (CONCEPT / "champions/generation_1/witness.json").read_text())
    status = dict(concept="phase_robust_leakage_counterexample", verification_mode="B_COUNTEREXAMPLE",
                  status="built", generation=1, ratchet_generations=1, solvability="unknown",
                  targets=dict(minimum_scenario_gap=.065, maximum_final_leakage=.01,
                               calibration_maximum=.005, calibration_family_rms=.002, scenarios=21),
                  previous_fresh_attempt="v_1", previous_fresh_status="solved",
                  champion="champions/generation_1/witness.json",
                  counterexample_search="adversary/generation_1/champion_stress_audit.json")
    replace_text(CONCEPT / "status.json", json.dumps(status, indent=2) + "\n")
    (CONCEPT / "freeze_manifest.json").unlink()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
