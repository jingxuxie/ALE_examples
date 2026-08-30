from common import PARTICIPANT

import numpy as np
import stim
from models import SPECS, make_model


def catalog():
    cases = []

    def add(case_id, group, distance, rounds=1, px=0.006, pz=0.006, py=0.075,
            pair=0.0, measurement=0.0, burst=0.0, profile="uniform", family=None):
        if family is None:
            family = "temporal_memory" if rounds > 1 else "spatial_crosstalk" if pair else "biased_pauli"
        cases.append(dict(case_id=case_id, stress_group=group, family=family, distance=distance, rounds=rounds,
                          px=px, pz=pz, py=py, pair=pair, measurement=measurement, burst=burst, profile=profile))

    for original in SPECS:
        cases.append(dict(original, stress_group="initial_distribution_anchors", profile="uniform"))
    for distance, probability in [(11, 0.075), (13, 0.080), (15, 0.085)]:
        add(f"size_d{distance}", "distance_scaling", distance, py=probability)
    for distance in [8, 10, 12]:
        add(f"even_d{distance}", "even_distance", distance, py=0.085)
    for name, px, pz, py in [("balanced", 0.028, 0.028, 0.028), ("x_dominant", 0.050, 0.004, 0.020), ("z_dominant", 0.004, 0.050, 0.020)]:
        add(name + "_d11", "bias_rotation", 11, px=px, pz=pz, py=py)
    for distance, probability in [(9, 0.024), (11, 0.032), (13, 0.040)]:
        add(f"pairs_d{distance}", "strong_spatial_crosstalk", distance, px=0.004, pz=0.010, py=0.045, pair=probability)
    for distance, rounds in [(9, 5), (11, 5), (11, 7)]:
        add(f"depth_d{distance}_r{rounds}", "memory_depth", distance, rounds, px=0.003, pz=0.003,
            py=0.026, measurement=0.018, burst=0.010)
    for distance, rounds, pair in [(9, 3, 0.010), (11, 5, 0.014), (13, 5, 0.018)]:
        add(f"joint_d{distance}_r{rounds}", "joint_space_time_faults", distance, rounds,
            px=0.003, pz=0.005, py=0.025, pair=pair, measurement=0.018, burst=0.010)
    for distance in [9, 11, 13]:
        add(f"strip_d{distance}", "known_spatial_nonuniformity", distance, px=0.005, pz=0.005,
            py=0.055, pair=0.008, profile="detector_support_strip")
    for distance, rounds in [(9, 3), (9, 5), (11, 5)]:
        add(f"bad_round_d{distance}_r{rounds}", "known_temporal_nonuniformity", distance, rounds,
            px=0.003, pz=0.003, py=0.025, measurement=0.008, burst=0.008, profile="noisy_middle_round")
    for distance, measurement in [(9, 0.045), (11, 0.055), (13, 0.065)]:
        add(f"readout_d{distance}", "measurement_dominated", distance, 5, px=0.002, pz=0.002,
            py=0.015, measurement=measurement, burst=0.006)
    return cases


def make_stress_model(spec):
    model = make_model(spec)
    probabilities = model["probabilities"].copy()
    profile = spec["profile"]
    coordinates = model["detector_coordinates"]
    if profile == "detector_support_strip":
        selected = coordinates[:, 0] <= 1
        touched = np.any(model["detector_matrix"][selected] != 0, axis=0)
        probabilities[touched] *= 2.0
    elif profile == "noisy_middle_round":
        selected = coordinates[:, 2] == spec["rounds"] // 2
        touched = np.any(model["detector_matrix"][selected] != 0, axis=0)
        kinds = model["mechanism_kind"]
        probabilities[touched & (kinds == "readout")] *= 4.0
        probabilities[touched & (kinds == "YY_time")] *= 2.0
        probabilities[touched & np.isin(kinds, ["X", "Z", "Y"])] *= 1.5
    elif profile != "uniform":
        raise ValueError("Unknown profile")
    probabilities = np.clip(probabilities, 1e-8, 0.25)
    lines = model["dem_text"].splitlines()
    for mechanism, probability in enumerate(probabilities):
        suffix = lines[mechanism].split(")", 1)[1]
        lines[mechanism] = f"error({probability:.17g})" + suffix
    model["probabilities"] = probabilities
    model["dem_text"] = "\n".join(lines) + "\n"
    assert stim.DetectorErrorModel(model["dem_text"]).num_errors == len(probabilities)
    return model
