import random


SCREENING_SEED = 200100024
CHALLENGE_SEED = 200700668
CONFIRMATION_SEED = 210802203
FAMILIES = ("u1_local", "u1_correlated", "z2_pseudogenerator")


def term(ops, amplitude=1):
    coefficient = complex(amplitude)
    return {"amplitude": [coefficient.real, coefficient.imag], "ops": [list(op) for op in ops]}


def hermitian(ops, amplitude=1):
    conjugates = {"raise": "lower", "lower": "raise"}
    adjoint = [(kind, offset, conjugates.get(name, name)) for kind, offset, name in ops]
    return [term(ops, amplitude), term(adjoint, complex(amplitude).conjugate())]


def channels_for(family, length, variant):
    instances = []

    def add(name, terms, stride=1):
        instances.append({"id": name, "anchors": list(range(variant % stride, length, stride)), "terms": terms})

    if family.startswith("u1"):
        add("link_leak", [term([("l", 0, "x")])])
        add("pair_leak", hermitian([("m", 0, "raise"), ("m", 1, "raise")]))
        add("bare_hop", hermitian([("m", 0, "raise"), ("m", 1, "lower")]))
        add("matter_drive", [term([("m", 0, "x")])], stride=2)
        add("density_link", [term([("m", 0, "n"), ("l", 1, "x")])], stride=3)
        add("dressed_clean", hermitian([("m", 0, "lower"), ("l", 0, "raise"), ("m", 1, "lower")]), stride=8)
        if family == "u1_correlated":
            add("four_site_crosstalk", hermitian([("m", -1, "lower"), ("l", 0, "raise"), ("m", 2, "lower")]))
            add("two_link_crosstalk", [term([("l", 0, "x"), ("l", 2, "x")])], stride=2)
            add("skip_pair", hermitian([("m", 0, "raise"), ("m", 2, "raise")]), stride=3)
    else:
        assisted = hermitian([("m", 0, "raise"), ("l", 0, "raise"), ("m", 1, "lower")])
        assisted += hermitian([("m", 0, "raise"), ("l", 0, "lower"), ("m", 1, "lower")], 0.5)
        add("assisted_hop", assisted)
        add("bare_hop", hermitian([("m", 0, "raise"), ("m", 1, "lower")]), stride=2)
        add("density_links", [term([("m", 0, "n"), ("l", 0, "z")]),
                              term([("m", 0, "n"), ("l", -1, "z")], -0.5)])
        add("electric_leak", [term([("l", 0, "z")])])
        add("pair_crosstalk", [term([("m", 0, "x"), ("m", 1, "x")])], stride=3)
        add("two_link_crosstalk", [term([("l", 0, "z"), ("l", 1, "z")])], stride=2)
        add("dressed_clean", hermitian([("m", 0, "raise"), ("l", 0, "z"), ("m", 1, "lower")]), stride=8)
        cancellation = hermitian([("m", 0, "raise"), ("l", 0, "raise"), ("m", 1, "lower")])
        cancellation += hermitian([("m", 0, "raise"), ("l", 0, "lower"), ("m", 1, "lower")], -1)
        add("interference_clean", cancellation, stride=8)
    operator = "x" if family.startswith("u1") else "z"
    add("balanced_null", [term([("l", 0, operator)]), term([("l", 0, operator)], -1)], stride=16)
    return instances


def make_case(family, length, seed, variant, split):
    randomizer = random.Random(seed)
    model = "z2" if family == "z2_pseudogenerator" else "u1"
    denominator = (9, 12, 15)[variant % 3]
    caps = [denominator - randomizer.randrange(0, 3) for site in range(length)]
    uncertainty = [round(0.0005 * randomizer.randint(1, 4), 7) for site in range(length)]
    if model == "u1":
        target = [0] * length
    elif variant % 3 == 0:
        target = [1] * length
    elif variant % 3 == 1:
        target = [(-1) ** site for site in range(length)]
    else:
        blocks = [randomizer.choice((-1, 1)) for index in range((length + 7) // 8)]
        target = [blocks[site // 8] for site in range(length)]
    phase_start = (9, 15, 23)[variant % 3]
    phase_ticks = list(range(phase_start, phase_start + 15, 2))
    return {"id": f"{split}_{family}_{variant:02d}", "family": family, "model": model,
            "length": length, "target": target, "channels": channels_for(family, length, variant),
            "hardware": {"denominator": denominator, "caps": caps,
                         "uncertainty": uncertainty, "bandwidth": 2 if model == "z2" else 1,
                         "phase_denominator": 12, "phase_ticks": phase_ticks}}


def split_cases(split):
    seeds = {"screening": SCREENING_SEED, "challenge": CHALLENGE_SEED, "confirmation": CONFIRMATION_SEED}
    lengths = {"screening": [32, 64, 128], "challenge": [48, 80, 112, 160], "confirmation": [96, 144]}
    offset = {"screening": 0, "challenge": 3, "confirmation": 7}[split]
    for family_index, family in enumerate(FAMILIES):
        for index, length in enumerate(lengths[split]):
            yield make_case(family, length, seeds[split] + family_index * 1009 + index * 97,
                            offset + index, split)
