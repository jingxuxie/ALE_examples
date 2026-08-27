PROFILES = {
    'baseline': {'bond': 24, 'step': 0.2, 'sweeps': 6, 'cutoff': 1e-8},
    'production': {'bond': 96, 'step': 0.05, 'sweeps': 12, 'cutoff': 1e-13},
    'refined': {'bond': 160, 'step': 0.025, 'sweeps': 16, 'cutoff': 1e-15},
}


def policy(case, profile):
    settings = dict(PROFILES[profile])
    if case['family'] == 'ladder':
        settings['bond'] = {'baseline': 24, 'production': 160, 'refined': 240}[profile]
    elif case['family'] == 'paired':
        settings['bond'] = {'baseline': 16, 'production': 48, 'refined': 80}[profile]
    elif case['family'] == 'vibronic':
        settings['bond'] = {'baseline': 16, 'production': 64, 'refined': 112}[profile]
    return settings
