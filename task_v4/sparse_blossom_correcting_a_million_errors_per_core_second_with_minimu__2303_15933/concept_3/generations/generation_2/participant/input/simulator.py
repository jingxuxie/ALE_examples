import numpy as np


def sample_events(spec, rates, action_id, shots, rng):
    action = spec["actions"][action_id]
    modes = rng.choice(len(action["mode_weights"]), shots, p=action["mode_weights"])
    exposures = np.asarray(action["exposures"])
    syndromes = np.zeros(shots, dtype=np.int64)
    for index, channel in enumerate(spec["channels"]):
        intensity = exposures[modes, index] * rates[index]
        fired = rng.random(shots) < -0.5 * np.expm1(-2.0 * intensity)
        alternate = rng.random(shots) < action["alternate_probability"][index]
        footprint = np.where(alternate, channel["masks"][1], channel["masks"][0])
        syndromes ^= np.where(fired, footprint, 0)
    return np.unique(syndromes, return_counts=True)
