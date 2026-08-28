import hashlib
import math

import numpy as np

from engine import calibration_rates


FAMILIES = ("white_coherent", "pink_correlated", "brown_degenerate")


def pure_specification(indices, phases=None, magnitudes=None):
    phases = np.zeros(len(indices)) if phases is None else np.asarray(phases)
    magnitudes = np.ones(len(indices)) if magnitudes is None else np.asarray(magnitudes)
    amplitudes = magnitudes * np.exp(1j * phases)
    amplitudes /= np.linalg.norm(amplitudes)
    return dict(indices=list(map(int, indices)), real=amplitudes.real.tolist(),
                imag=amplitudes.imag.tolist())


def make_case(family, variant, seed, region):
    random = np.random.default_rng(seed)
    family_index = FAMILIES.index(family)
    local_variant = variant % 3
    beta = family_index
    eta = ((0.05, 0.3, 0.7), (0.0, 0.5, 0.92), (0.0, 0.6, 1.0))[family_index][local_variant]
    bath = dict(beta=beta, amplitude=((0.026, 0.018, 0.009)[family_index]
                                     * random.uniform(0.8, 1.2)),
                cutoff=(1.0 if beta == 0 else (0.3, 0.42, 0.58)[local_variant]),
                floor=(0.0 if beta == 0 else (0.0003, 0.0001, 0.0006)[local_variant]), eta=eta)
    coherent = ((0.025, 0.15, 0.3), (0, 0.065, 0.12), (0, 0, 0))[family_index][local_variant]
    kappa = ((0.045, 0.009, 0.003), (0.003, 0.008, 0.02),
             (0.002, 0.006, 0.012))[family_index][local_variant]
    budget = 21.0
    if region == "challenge":
        if family_index == 0:
            bath["eta"] = 0.95 if local_variant == 0 else 0.45
            coherent = 0.08 if local_variant == 0 else 0.32
            budget = 11.0 if local_variant == 1 else 21.0
            kappa = 0.015
        elif family_index == 1:
            bath["floor"] = 0.003 if local_variant == 0 else 0.0001
            bath["eta"] = 0.7 if local_variant == 0 else 0.98
        else:
            coherent = 0.014 if local_variant == 0 else 0
            bath["cutoff"] = 0.17 if local_variant == 1 else 0.45
            bath["amplitude"] *= 0.45
            bath["eta"] = 0.85
    elif region == "confirmation":
        bath["eta"] = (0.63, 0.82, 0.94)[family_index]
        bath["amplitude"] *= 0.87
        if beta:
            bath["cutoff"] = 0.37 + 0.06 * family_index
        coherent = (0.19, 0.043, 0.0)[family_index]
        kappa = (0.014, 0.009, 0.007)[family_index]
        budget = 15.5 if family_index == 0 else 21.0
    symmetric = family_index == 2
    model = dict(
        hopping=([1.0] * 3 if symmetric else random.uniform(0.8, 1.2, 3).tolist()),
        phase=([0.0] * 3 if symmetric else random.uniform(-0.16, 0.16, 3).tolist()),
        electric=([0.0 if local_variant != 1 else 0.25] * 3 if symmetric
                  else random.uniform(0.3, 0.65, 3).tolist()),
        mass=([0.0] * 3 if symmetric else random.uniform(-0.22, 0.22, 3).tolist()),
        error_hop=random.uniform(0.7, 1.2, 3).tolist(),
        error_link=random.uniform(0.4, 1.1, 3).tolist(),
        crosstalk=[0.8, -0.55, 0.35],
        matter_weight=random.uniform(0.5, 1.25, 3).tolist(),
        link_weight=random.uniform(0.5, 1.25, 3).tolist(),
        matter_sign=[1, 1, 1], link_sign=[1, -1, 1] if local_variant == 2 else [1, 1, 1],
        kappa=kappa,
    )
    model["lambda"] = coherent
    if family_index == 1 and region == "challenge" and local_variant == 1:
        model["matter_sign"] = [1, -1, 1]
    initial = pure_specification([34])
    if local_variant == 2 or region == "confirmation":
        initial = pure_specification([34, 26], [0, 0.35], [1, 0.4])
    actions = [
        dict(id="off", strength=0.0, coefficients=[1, 1, 1]),
        dict(id="flat_low", strength=0.9, coefficients=[1, 1, 1]),
        dict(id="flat_high", strength=2.6, coefficients=[1, 1, 1]),
        dict(id="signed", strength=2.6, coefficients=[1, -1, 1]),
        dict(id="graded_high", strength=2.6, coefficients=[0.25, 0.55, 1]),
        dict(id="graded_mid", strength=1.6, coefficients=[0.25, 0.55, 1]),
        dict(id="unaffordable", strength=8.0, coefficients=[1, 1, 1]),
    ]
    rows = []
    centers = np.geomspace(0.04, 15, 13) * random.uniform(0.9, 1.1)
    for center in centers:
        for mode in (0, 1, -1):
            row = dict(omega=(center * np.array([0.78, 1.0, 1.23])).tolist(),
                       weight=[0.25, 0.5, 0.25], mode=mode)
            mean = calibration_rates(bath, [row])[0]
            sigma = max(1e-6, 0.018 * abs(mean))
            row.update(value=float(mean + random.normal() * sigma), sigma=float(sigma))
            rows.append(row)
    audit_beta = (2 * family_index + local_variant + 1) % 3
    audit_bath = dict(beta=audit_beta, amplitude=float(random.uniform(0.007, 0.023)),
                      cutoff=float(random.uniform(0.25, 0.7)) if audit_beta else 1.0,
                      floor=float(random.uniform(0.0001, 0.001)) if audit_beta else 0.0,
                      eta=(1.0, 0.0, 0.65)[local_variant])
    audit_state = pure_specification([0, 3, 5, 18, 29, 42, 56, 63],
                                    random.uniform(-math.pi, math.pi, 8),
                                    random.uniform(0.6, 1.4, 8))
    case_id = hashlib.sha256(f"c04-v1-{seed}".encode()).hexdigest()[:12]
    case = dict(version=1, case_id=case_id, calibration=rows, model=model, initial=initial,
                actions=actions, budget=budget,
                times=np.linspace(0, 3.8 + 0.5 * local_variant + random.uniform(0, 0.4), 7).tolist(),
                audit=dict(action=(actions[0] if symmetric else actions[1]),
                           bath=audit_bath, states=[initial, audit_state]))
    return dict(case=case, family=family, region=region, seed=seed, generating_bath=bath)


def reserved_cases():
    result = {}
    for split, count, first_seed in (("screening", 3, 1101), ("challenge", 2, 2201),
                                     ("confirmation", 1, 3301)):
        result[split] = [make_case(family, variant, first_seed + family_index * count + variant, split)
                         for family_index, family in enumerate(FAMILIES) for variant in range(count)]
    return result
