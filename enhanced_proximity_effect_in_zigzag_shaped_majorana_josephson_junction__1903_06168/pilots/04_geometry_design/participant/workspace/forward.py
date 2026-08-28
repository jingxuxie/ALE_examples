"""Optional forward diagnostic, not a design optimizer."""

import argparse
import json

import numpy as np

from physics import ForwardModel, feasibility, geometry_arrays, load_result, nominal_scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--geometry")
    parser.add_argument("--output", required=True)
    parser.add_argument("--mu", type=float)
    parser.add_argument("--zeeman", type=float)
    parser.add_argument("--momenta", type=int, default=9)
    parser.add_argument("--topology", action="store_true")
    arguments = parser.parse_args()
    with open(arguments.input, encoding="utf-8") as handle:
        request = json.load(handle)
    masks = load_result(request, arguments.geometry) if arguments.geometry else geometry_arrays(request, request["baseline_geometry"])
    diagnostics = {"feasibility": feasibility(request, masks)}
    if diagnostics["feasibility"]["valid"]:
        scenario = nominal_scenario(request)
        if arguments.mu is not None:
            scenario["mu_normal_mev"] = arguments.mu
        if arguments.zeeman is not None:
            scenario["zeeman_mev"] = arguments.zeeman
        if not 2 <= arguments.momenta <= 501:
            parser.error("--momenta must lie between 2 and 501")
        model = ForwardModel(request, masks, scenario)
        diagnostics.update(model.spectral_gap(np.linspace(0, np.pi, arguments.momenta)))
        diagnostics["scenario"] = scenario
        if arguments.topology:
            diagnostics["class_d_invariant"] = model.topological_invariant()
    with open(arguments.output, "w", encoding="utf-8") as handle:
        json.dump(diagnostics, handle, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
