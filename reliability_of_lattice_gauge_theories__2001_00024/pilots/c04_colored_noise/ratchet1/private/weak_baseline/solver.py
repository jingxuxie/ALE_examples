import numpy as np

import engine
from accelerated import predict


def solve(case: dict) -> dict:
    operators = engine.build_model(case)
    amplitude = float(np.clip(np.median([row["value"] for row in case["calibration"]
                                         if row["mode"] == 0]), 1e-5, 0.12))
    bath = dict(beta=0, amplitude=amplitude, cutoff=1.0, floor=0.0, eta=0.0)
    local_channels = engine.channels(case, operators, 0.0)
    audit_bath = dict(beta=0, amplitude=float(engine.spectrum(case["audit"]["bath"], 1.0)),
                      cutoff=1.0, floor=0.0, eta=0.0)
    audit_compiled = engine.secular_generator(
        engine.hamiltonian(case, operators, case["audit"]["action"]), local_channels, audit_bath)
    predictions = {}
    actions = engine.feasible_actions(case)
    for action in actions:
        compiled = engine.secular_generator(engine.hamiltonian(case, operators, action), local_channels, bath)
        predictions[action["id"]] = predict(case, operators, compiled, "centered_expm")[0]
    return dict(bath=bath, audit=engine.audit_response(audit_compiled, case["audit"]["states"]),
                predictions=predictions, selected_action=max(actions, key=engine.action_cost)["id"])
