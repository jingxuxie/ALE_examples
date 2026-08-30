import numpy as np


REGIMES = ("chain_hooks", "patch_crosstalk", "burst_aliases")
FAMILIES = ("boundary", "bulk", "hook", "rare")
BOUNDS = {"boundary": (0.003, 0.05), "bulk": (0.002, 0.06),
          "hook": (0.0015, 0.028), "rare": (0.00005, 0.015)}


def make_spec(regime, structure_seed):
    rng = np.random.default_rng(structure_seed)
    detector_count = 6 + REGIMES.index(regime)
    permutation = rng.permutation(detector_count)

    def mask(nodes):
        return sum(1 << int(permutation[node % detector_count]) for node in set(nodes))

    channels = []
    for index in range(detector_count):
        channels.append({"family": "boundary", "masks": [mask([index]), mask([index])]})
    for index in range(detector_count + 2):
        start = index % detector_count
        distance = 1 if regime == "chain_hooks" else (1 + index % 2)
        channels.append({"family": "bulk", "masks": [mask([start, (start + distance) % detector_count]),
                                                                     mask([start, (start + 3) % detector_count])]})
    for index in range(4):
        width = 3 if regime == "chain_hooks" else 4
        primary = [(index + offset) % detector_count for offset in range(width)]
        alternate = [(index + offset) % detector_count for offset in (0, 2, 4)]
        channels.append({"family": "hook", "masks": [mask(primary), mask(alternate)]})
    hook_start = len(channels) - 4
    for index in range(4):
        primary = channels[hook_start + index]["masks"][0]
        alternate = mask([(index + offset) % detector_count for offset in (1, 3, 4)])
        channels.append({"family": "rare", "masks": [primary, alternate]})
    channel_count = len(channels)
    sectors = rng.permutation(np.arange(channel_count) % 4)
    mode_scale = rng.uniform(2.0, 4.0, channel_count)
    for index in range(4):
        mode_scale[hook_start + 4 + index] = mode_scale[hook_start + index]
    for index, channel in enumerate(channels):
        channel.update({"id": "channel_%02d" % index, "sector": int(sectors[index]),
                        "rate_bounds": list(BOUNDS[channel["family"]])})
    actions = []
    for action_index in range(13):
        exposure = np.ones(channel_count)
        alternate_probability = np.zeros(channel_count)
        hot_probability = 0.0
        if action_index:
            hot_probability = [0.08, 0.22, 0.42][(action_index + REGIMES.index(regime)) % 3]
            alternate_probability = rng.uniform(0.10, 0.38, channel_count)
            exposure = rng.uniform(0.65, 1.25, channel_count)
            if action_index == 1:
                exposure *= 7.0
            elif action_index <= 9:
                sector = (action_index - 2) // 2
                gain = 5.0 if action_index % 2 == 0 else 18.0
                selected = sectors == sector
                exposure *= np.where(selected, gain, 0.35)
                for index, channel in enumerate(channels):
                    if channel["family"] == "rare" and selected[index]:
                        exposure[index] *= 2.5
            elif action_index == 10:
                exposure *= np.array([12.0 if channel["family"] in ("hook", "rare") else 0.25
                                      for channel in channels])
                alternate_probability *= 0.12
            elif action_index == 11:
                exposure *= np.array([20.0 if channel["family"] == "rare" else 0.45
                                      for channel in channels])
                alternate_probability = rng.uniform(0.55, 0.80, channel_count)
            else:
                exposure *= 0.3
                hot_probability = 0.65
        exposures = np.stack([exposure, exposure * mode_scale])
        if action_index == 0:
            exposures[1] = exposures[0]
        actions.append({"id": action_index, "name": "reference" if action_index == 0 else "configuration_%02d" % action_index,
                        "mode_weights": [1.0 - hot_probability, hot_probability],
                        "exposures": exposures.tolist(), "alternate_probability": alternate_probability.tolist()})
    return add_gain_ladder({"protocol": "detector-calibration-v1", "regime": regime,
            "detector_count": detector_count, "channels": channels, "actions": actions,
            "shot_budget": 40000, "max_queries": 64, "max_shots_per_query": 4000,
            "cpu_seconds": 60, "wall_seconds": 900})


def add_gain_ladder(spec):
    if len(spec["actions"]) != 13:
        raise ValueError("Gain ladder can only be added once")
    channel_count = len(spec["channels"])
    mode_scale = np.array(spec["actions"][1]["exposures"])[1] / np.array(spec["actions"][1]["exposures"])[0]
    for channel_index, channel in enumerate(spec["channels"]):
        if channel["family"] != "rare":
            continue
        channel["rate_bounds"] = list(BOUNDS["rare"])
        for gain_index, gain in enumerate((20.0, 120.0, 720.0, 4320.0)):
            exposure = np.full(channel_count, 0.2)
            exposure[channel_index] = gain
            alternate = np.full(channel_count, 0.15)
            alternate[channel_index] = 0.3 if gain_index % 2 == 0 else 0.7
            spec["actions"].append({"id": len(spec["actions"]),
                                    "name": "rare_%d_gain_%d" % (channel_index, int(gain)),
                                    "mode_weights": [0.8, 0.2],
                                    "exposures": np.stack([exposure, exposure * mode_scale]).tolist(),
                                    "alternate_probability": alternate.tolist()})
    return spec


def draw_rates(spec, rate_seed):
    rng = np.random.default_rng(rate_seed)
    bounds = np.array([channel["rate_bounds"] for channel in spec["channels"]])
    return np.exp(rng.uniform(np.log(bounds[:, 0]), np.log(bounds[:, 1])))


def sample_events(spec, rates, action_id, shots, rng):
    action = spec["actions"][action_id]
    exposure = np.asarray(action["exposures"])
    mode = rng.choice(2, shots, p=action["mode_weights"])
    syndrome = np.zeros(shots, dtype=np.int64)
    for index, channel in enumerate(spec["channels"]):
        probability = -0.5 * np.expm1(-2.0 * exposure[mode, index] * rates[index])
        fired = rng.random(shots) < probability
        alternate = rng.random(shots) < action["alternate_probability"][index]
        footprint = np.where(alternate, channel["masks"][1], channel["masks"][0])
        syndrome ^= np.where(fired, footprint, 0)
    return np.bincount(syndrome, minlength=1 << spec["detector_count"])


def independent_pmf(spec, rates, action_id):
    action = spec["actions"][action_id]
    states = np.arange(1 << spec["detector_count"])
    result = np.zeros(len(states))
    for mode, mode_weight in enumerate(action["mode_weights"]):
        distribution = np.zeros(len(states))
        distribution[0] = 1.0
        for index, channel in enumerate(spec["channels"]):
            probability = -0.5 * np.expm1(-2.0 * action["exposures"][mode][index] * rates[index])
            alternate = action["alternate_probability"][index]
            distribution = ((1.0 - probability) * distribution
                            + probability * (1.0 - alternate) * distribution[states ^ channel["masks"][0]]
                            + probability * alternate * distribution[states ^ channel["masks"][1]])
        result += mode_weight * distribution
    return result
