import hashlib

import numpy as np

import engine


FAMILIES = ("white_coherent", "pink_correlated", "brown_degenerate")
SCREENING = [
    ("white_coherent", 0, 761031, 9000), ("white_coherent", 1, 761032, 16000),
    ("pink_correlated", 0, 762041, 11000), ("pink_correlated", 1, 762042, 18500),
    ("brown_degenerate", 0, 763051, 12500), ("brown_degenerate", 1, 763052, 20000),
]
CONFIRMATION = [("white_coherent", 2, 861131, 14500),
                ("pink_correlated", 2, 862141, 17000),
                ("brown_degenerate", 2, 863151, 15500)]


def state(indices, phases=None, magnitudes=None):
    phases = np.zeros(len(indices)) if phases is None else np.asarray(phases)
    magnitudes = np.ones(len(indices)) if magnitudes is None else np.asarray(magnitudes)
    amplitudes = magnitudes * np.exp(1j * phases)
    amplitudes /= np.linalg.norm(amplitudes)
    return dict(indices=list(map(int, indices)), real=amplitudes.real.tolist(), imag=amplitudes.imag.tolist())


def make_case(family, variant, seed, final_time):
    random = np.random.default_rng(seed)
    beta = FAMILIES.index(family)
    amplitudes = ((1.1e-5, 1.1e-5, 1.2e-5), (1.4e-5, 1.1e-5, 1.3e-5), (1.6e-5, 1.3e-5, 1.45e-5))
    cutoffs = ((1.0, 1.0, 1.0), (0.4, 0.55, 0.46), (0.4, 0.5, 0.46))
    correlations = ((0.2, 0.8, 0.5), (0.3, 0.9, 0.72), (0.6, 1.0, 0.84))
    budgets = ((21.0, 11.5, 21.0), (21.0, 21.0, 13.0), (21.0, 11.5, 21.0))
    drift_factors = ((1.05, 1.1, 1.05), (1.0, 0.95, 1.05), (1.0, 1.1, 1.05))
    detuning_phases = ((0.15, 1.3, 0.6), (0.1, 0.7, 0.35), (0.0, 0.15, 0.1))
    bath = dict(beta=beta, amplitude=amplitudes[beta][variant], cutoff=cutoffs[beta][variant],
                floor=(2e-8 if beta and variant == 1 else 0.0), eta=correlations[beta][variant])
    symmetric = beta == 2
    hopping = float(random.uniform(0.94, 1.08))
    electric = float(random.uniform(0.2, 0.35))
    model = dict(
        hopping=([hopping] * 3 if symmetric else random.uniform(0.9, 1.1, 3).tolist()),
        phase=([0.0] * 3 if symmetric else random.uniform(-0.12, 0.12, 3).tolist()),
        electric=([electric] * 3 if symmetric else random.uniform(0.35, 0.6, 3).tolist()),
        mass=([0.0] * 3 if symmetric else random.uniform(-0.15, 0.15, 3).tolist()),
        error_hop=([1.0] * 3 if symmetric else random.uniform(0.85, 1.15, 3).tolist()),
        error_link=([0.7] * 3 if symmetric else random.uniform(0.55, 0.9, 3).tolist()),
        crosstalk=[0.8, -0.55, 0.35],
        matter_weight=random.uniform(0.45, 0.9, 3).tolist(),
        link_weight=random.uniform(0.45, 0.9, 3).tolist(),
        matter_sign=[1, -1, 1] if variant == 1 else [1, 1, 1],
        link_sign=[1, 1, -1] if variant == 1 else [1, 1, 1],
        kappa=detuning_phases[beta][variant] / (2.6**2 * final_time),
    )
    model["lambda"] = float(drift_factors[beta][variant] * np.sqrt(2.6 / final_time))
    initial = (state([34]) if variant == 0 else
               state([34, 26], [0, float(random.uniform(0.15, 0.5))], [1, 0.35]))
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
    for center in np.geomspace(0.04, 16.0, 13) * random.uniform(0.95, 1.05):
        for mode in (0, 1, -1):
            row = dict(omega=(center * np.array([0.8, 1.0, 1.2])).tolist(), weight=[0.25, 0.5, 0.25], mode=mode)
            mean = float(engine.calibration_rates(bath, [row])[0])
            sigma = max(1e-11, 0.008 * abs(mean))
            row.update(value=float(mean + random.normal() * sigma), sigma=sigma)
            rows.append(row)
    audit_beta = (beta + variant + 1) % 3
    audit_bath = dict(beta=audit_beta, amplitude=float(random.uniform(0.003, 0.008)),
                      cutoff=float(random.uniform(0.4, 0.65)) if audit_beta else 1.0,
                      floor=float(random.uniform(0.0, 0.0004)) if audit_beta else 0.0,
                      eta=(0.1, 0.95, 0.45)[variant])
    if symmetric:
        audit_bath["eta"] = (0.7, 1.0, 0.9)[variant]
    probe = state([0, 3, 5, 18, 29, 42, 56, 63], random.uniform(-np.pi, np.pi, 8), random.uniform(0.6, 1.4, 8))
    identifier = hashlib.sha256(f"c04-ratchet1-{seed}".encode()).hexdigest()[:12]
    case = dict(version=1, case_id=identifier, calibration=rows, model=model, initial=initial,
                actions=actions, budget=budgets[beta][variant], times=np.linspace(0, final_time, 7).tolist(),
                audit=dict(action=actions[0] if symmetric else actions[1], bath=audit_bath, states=[initial, probe]))
    return dict(case=case, family=family, seed=seed, generating_bath=bath,
                coherent_drift_scale=2.6 / model["lambda"]**2,
                incoherent_scaling_indicator=bath["amplitude"] * final_time / 2.6**beta,
                actuator_detuning_phase=detuning_phases[beta][variant])


def all_cases():
    return dict(screening=[make_case(*specification) for specification in SCREENING],
                confirmation=[make_case(*specification) for specification in CONFIRMATION])
