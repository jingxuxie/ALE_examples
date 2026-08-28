import numpy as np


def make_geometry(request, parameters):
    if parameters is None:
        return {name: np.asarray(mask, dtype=bool) for name, mask in request['baseline_geometry'].items()}
    grid = request['grid']
    nx, ny, spacing = grid['nx'], grid['ny'], grid['spacing_nm']
    amplitude = parameters.get('amplitude', 100.0)
    width = parameters.get('width', 120.0)
    frequency = parameters.get('frequency', 1)
    rounding = parameters.get('rounding', 0.0)
    modulation = parameters.get('modulation', 0.0)
    third = parameters.get('third', 0.0)
    reflected_columns = np.minimum(np.arange(nx), (-np.arange(nx)) % nx)
    phase = (reflected_columns * frequency / nx) % 1
    triangle = 1 - 4 * np.minimum(phase, 1 - phase)
    angle = 2 * np.pi * phase
    center = amplitude * ((1 - rounding) * triangle + rounding * np.cos(angle))
    center += third * np.cos(3 * angle)
    period = nx * spacing / frequency
    triangle_slope = np.where(phase < 0.5, -4.0, 4.0) * amplitude / period
    slope = (1 - rounding) * triangle_slope - rounding * amplitude * 2 * np.pi / period * np.sin(angle)
    slope -= third * 6 * np.pi / period * np.sin(3 * angle)
    halfwidth = width / 2 * np.sqrt(1 + slope ** 2) + modulation * np.cos(2 * angle)
    positions = (np.arange(ny) - (ny - 1) / 2) * spacing
    return {'sc_top': positions[:, None] >= center[None, :] + halfwidth[None, :],
            'sc_bottom': positions[:, None] <= center[None, :] - halfwidth[None, :]}


def initial_parameters(request):
    mismatch = request['operating_region']['mu_sc_rule'] != 'matched'
    widths = [100, 140, 180, 220] if mismatch else [100, 120, 160, 200]
    yield None
    period_scale = request['grid']['nx'] * request['grid']['spacing_nm'] / 1300.0
    yield dict(amplitude=round(150 * period_scale, 1), width=140, frequency=2,
               rounding=0.07, third=round(-12.2 * period_scale, 1))
    for amplitude in [60, 100, 140, 180]:
        for width in widths:
            yield dict(amplitude=amplitude, width=width, frequency=1)
    for frequency in [2, 3]:
        for amplitude in [70, 110, 150]:
            for width in [100, 140]:
                yield dict(amplitude=amplitude, width=width, frequency=frequency)
    for amplitude in [80, 120, 160]:
        for width in [100, 140, 180]:
            yield dict(amplitude=amplitude, width=width, frequency=1, rounding=1.0)


def neighbors(parameters, generator, count):
    if parameters is None:
        parameters = dict(amplitude=100, width=200, frequency=1)
    bounds = {'amplitude': (30, 240), 'width': (80, 260), 'rounding': (-0.2, 1.2),
              'modulation': (-35, 35), 'third': (-35, 35)}
    scales = {'amplitude': 15, 'width': 12, 'rounding': 0.25, 'modulation': 10, 'third': 10}
    names = list(bounds)
    for number in range(count):
        candidate = dict(parameters)
        selected = [names[number % len(names)]] if number < 2 * len(names) else generator.choice(names, size=2, replace=False)
        for name in selected:
            shift = scales[name] * (1 if number % 2 else -1) if number < 2 * len(names) else scales[name] * generator.normal()
            value = np.clip(candidate.get(name, 0) + shift, *bounds[name])
            candidate[name] = round(float(value), 2 if name == 'rounding' else 1)
        yield candidate
