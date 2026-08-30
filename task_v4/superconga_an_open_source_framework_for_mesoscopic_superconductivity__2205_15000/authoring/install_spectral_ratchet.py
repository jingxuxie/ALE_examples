import argparse
import datetime
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, choices=(2, 3), default=2)
    arguments = parser.parse_args()
    generation = arguments.generation
    ratchet = generation - 1
    proposal_path = CONCEPT / "adversary" / ("ratchet_" + str(ratchet)) / "proposal" / "freeze.json"
    proposal = json.loads(proposal_path.read_text())
    previous_freeze = json.loads((CONCEPT / "evaluator" / "hidden" / "freeze.json").read_text())
    if previous_freeze.get("generation", 1) != generation - 1:
        raise RuntimeError("unexpected installed generation")
    for relative, expected in previous_freeze["sha256"].items():
        if digest(CONCEPT / relative) != expected:
            raise RuntimeError("previous generation asset changed: " + relative)
    for name, relative in proposal["public"].items():
        source = CONCEPT / relative
        if digest(source) != proposal["public_sha256"][name]:
            raise RuntimeError("proposal input hash mismatch")
        shutil.copy2(source, CONCEPT / "participant" / "input" / name)
    witness = CONCEPT / proposal["private_witness"]
    if digest(witness) != proposal["private_witness_sha256"]:
        raise RuntimeError("proposal witness hash mismatch")
    shutil.copy2(witness, CONCEPT / "evaluator" / "hidden" / "feasible_design" / "design.json")
    diagnostics = proposal.get("diagnostics", str(Path(proposal["private_witness"]).parent / "diagnostics.json"))
    shutil.copy2(CONCEPT / diagnostics, CONCEPT / "evaluator" / "hidden" / "validation.json")
    current = {"generation": generation, "ratchet_generations": ratchet,
               "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "core_target": 0.96, "worst_family_target": 0.94,
               "parent_generation": "champions/generation_" + str(generation - 1),
               "adversarial_evidence": "adversary/ratchet_" + str(ratchet) + "/REPORT.md",
               "sha256": {relative: digest(CONCEPT / relative) for relative in previous_freeze["sha256"]}}
    (CONCEPT / "evaluator" / "hidden" / "freeze.json").write_text(json.dumps(current, indent=2) + "\n")
    state_path = CONCEPT / "status.json"
    state = json.loads(state_path.read_text())
    state.update({"phase": "generation_" + str(generation) + "_frozen", "generation": generation, "ratchet_generations": ratchet,
                  "first_generation": {"status": "solved", "fresh_score": 0.9999999999999648,
                                       "worst_family_score": 0.999999999999961, "wall_seconds": 333.07296601397684},
                  "ratchet_champion": proposal["measured_evidence"]["best_valid"],
                  "baseline": None, "fresh_attempts": [
                      {"model": "ultima-alpha", "generation": 1, "output": "attempts/v_1", "state": "solved"}
                  ]})
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(current, indent=2))


if __name__ == "__main__":
    main()
