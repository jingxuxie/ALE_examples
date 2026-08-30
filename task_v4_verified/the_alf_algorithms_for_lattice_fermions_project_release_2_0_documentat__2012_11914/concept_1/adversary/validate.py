import copy
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from evaluate import evaluate, precision_weight, read_witness
from physics import load_model, weight_batch


def main():
    destination = ROOT / "adversary" / "controls"
    destination.mkdir(exist_ok=True)
    model = load_model()
    malformed = {"fields": [[True] * 16] * 16}
    malformed_path = destination / "boolean.json"
    malformed_path.write_text(json.dumps(malformed))
    rejection = evaluate(malformed_path)
    assert not rejection["valid"] and not rejection["passed"]
    malformed_path.write_text(json.dumps({"fields": [[1] * 16] * 15}))
    short_rejection = evaluate(malformed_path)
    assert not short_rejection["valid"]
    random = np.random.default_rng(779)
    agreements = []
    for beta in [0.4, 1.6, 3.0]:
        test_model = copy.deepcopy(model)
        test_model["beta"] = beta
        fields = random.choice([-1, 1], size=(16, 16)).tolist()
        direct_sign, direct_log = weight_batch(fields, test_model)
        precise_signs, precise_log = precision_weight(fields, test_model, model["certification_points"][0], 65)
        difference = abs(float(precise_log) - direct_log[0])
        assert np.prod(precise_signs) == direct_sign[0] and difference < 1e-5
        agreements.append({"beta": beta, "direct_sign": int(direct_sign[0]), "log_error": float(difference)})
    negative_source = ROOT / "adversary" / "negative_2.0_4.0_1.0_16.json"
    positive_control = None
    if negative_source.exists():
        witness = {"fields": json.loads(negative_source.read_text())["fields"]}
        witness_path = destination / "negative_beta2.json"
        witness_path.write_text(json.dumps(witness))
        control_model = copy.deepcopy(model)
        control_model["beta"] = 2.0
        positive_control = evaluate(witness_path, control_model)
        assert positive_control["passed"]
        half_filling = copy.deepcopy(control_model)
        half_filling["chemical_potential"] = 0.0
        half_filling["certification_points"] = [{"beta_multiplier": 1.0, "chemical_shift": 0.0}]
        half_filling_result = evaluate(witness_path, half_filling)
        assert not half_filling_result["passed"]
        positive_control["half_filling_control"] = half_filling_result
    report = {"passed": True, "malformed_rejected": True, "independent_double_high_precision_agreements": agreements,
              "negative_weight_positive_control_at_beta2": positive_control,
              "note": "The beta2 negative control validates the checker but does not demonstrate feasibility at the participant beta."}
    (ROOT / "adversary" / "evaluator_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "negative_control_passed": positive_control["passed"] if positive_control else None}))


if __name__ == "__main__":
    main()
