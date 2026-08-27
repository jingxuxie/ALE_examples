import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'concept_01/solution/workspace'))
from cores import detect
from model import Model
from propagate import Propagator


def create_state(directory, name, kind, nx, ny, length_x, length_y, strength, rotation, relax_steps):
    x = np.arange(nx) * length_x / nx - length_x / 2
    y = np.arange(ny) * length_y / ny - length_y / 2
    xx, yy = np.meshgrid(x, y)
    radius = np.hypot(xx, yy)
    if kind == 'annulus':
        potential = 0.004 * (radius ** 2 - 36) ** 2
        density = np.logaddexp(0, (8 - potential + rotation ** 2 * radius ** 2 / 2) / 0.3) * 0.3 / strength
        roi = ((radius > 6.3) & (radius < 11.0)).astype(int)
        bulk = (radius > 7.3) & (radius < 9.8)
    elif kind == 'doublewell':
        potential = 0.025 * (xx ** 2 - 36) ** 2 + 0.7 * yy ** 2
        density = np.logaddexp(0, (14 - potential + rotation ** 2 * radius ** 2 / 2) / 0.2) * 0.2 / strength
        roi = (((xx - 6.3) / 3.0) ** 2 + (yy / 6.8) ** 2 < 1).astype(int)
        roi += 2 * ((((xx + 6.3) / 3.0) ** 2 + (yy / 6.8) ** 2 < 1).astype(int))
        bulk = (((xx - 6.3) / 2.0) ** 2 + (yy / 4.8) ** 2 < 1) | (((xx + 6.3) / 2.0) ** 2 + (yy / 4.8) ** 2 < 1)
    else:
        anisotropy = [1.08, 0.94] if kind == 'driven' else [1.0, 1.0]
        potential = (anisotropy[0] * xx ** 2 + anisotropy[1] * yy ** 2) / 2
        effective = potential - rotation ** 2 * radius ** 2 / 2
        chemical = np.sqrt(strength * np.sqrt((anisotropy[0] - rotation ** 2) * (anisotropy[1] - rotation ** 2)) / np.pi)
        density = np.logaddexp(0, (chemical - effective) / 0.15) * 0.15 / strength
        roi = (effective < 0.79 * chemical).astype(int)
        bulk = effective < 0.40 * chemical
    phase = np.zeros_like(xx)
    amplitude = np.sqrt(density)
    if kind == 'single':
        amplitude *= np.tanh(radius / 0.35)
        phase += np.arctan2(yy, xx)
    else:
        spacing = np.sqrt(2 * np.pi / (np.sqrt(3) * rotation))
        for row in range(-12, 13):
            for column in range(-12, 13):
                position_x = spacing * (column + (row % 2) / 2) + 0.031
                position_y = spacing * np.sqrt(3) / 2 * row - 0.017
                position_radius = np.hypot(position_x, position_y)
                if kind == 'annulus':
                    use = 2.8 < position_radius < 10.5
                elif kind == 'doublewell':
                    use = min(((position_x - 6.3) / 4.0) ** 2, ((position_x + 6.3) / 4.0) ** 2) + (position_y / 7.0) ** 2 < 1
                else:
                    use = position_radius < min(length_x, length_y) * 0.41
                if use:
                    distance = np.hypot(xx - position_x, yy - position_y)
                    amplitude *= np.tanh(distance / 0.32)
                    phase += np.arctan2(yy - position_y, xx - position_x)
        if kind == 'annulus':
            phase += 7 * np.arctan2(yy, xx)
    psi = amplitude * np.exp(1j * phase)
    psi /= np.sqrt(np.sum(np.abs(psi) ** 2) * length_x * length_y / (nx * ny))
    arrays = dict(x=x, y=y, psi=psi, potential=potential, roi=roi, bulk=bulk)
    case = dict(id=name, asset=name + '.npz', g=strength, omega=rotation, times=[0, 0.2, 1.0, 3.0, 6.0], imprints=[], correlation_edges=[0, 2.8, 5.6, 20.0], spectrum_edges=[0, 1, 2, 4, 8, 16, 64], intervention_center=[0, 0])
    model = Model(case, arrays)
    propagator = Propagator(model)
    for iteration in range(relax_steps):
        psi = propagator.step(psi, 0, 0.002, imaginary=True)
    arrays['psi'] = psi
    np.savez_compressed(directory / case['asset'], **arrays)
    vortices = detect(psi, model)
    print(name, 'shape', psi.shape, 'vortices', len(vortices), 'bulk', np.count_nonzero(model.sample(bulk, vortices[:, :2])), flush=True)
    return case, vortices


def intervention(case, vortices, name, target=(0, 0), count=1, charge=-1):
    result = dict(case, id=name)
    positive = vortices[vortices[:, 2] > 0]
    chosen = positive[np.argsort(np.sum((positive[:, :2] - target) ** 2, axis=1))[:count]]
    result['imprints'] = [dict(x=float(core[0]), y=float(core[1]), charge=charge) for core in chosen]
    result['intervention_center'] = list(target)
    return result


def main():
    public = ROOT / 'concept_01/participant/v_01/input'
    hidden = ROOT / 'concept_01/evaluator/hidden'
    lattice, cores = create_state(public, 'lattice_state', 'disk', 160, 160, 28, 28, 700, 0.94, 4500)
    cases = [dict(lattice, id='control'), intervention(lattice, cores, 'vacancy'), intervention(lattice, cores, 'reverse', charge=-2), intervention(lattice, cores, 'cluster', count=7)]
    (public / 'campaign.json').write_text(json.dumps(dict(cases=cases), indent=2))
    isolated, cores = create_state(public, 'isolated_state', 'single', 96, 96, 14, 14, 80, 0, 2500)
    isolated['times'] = [0, 0.05, 0.2, 0.6, 1.6, 3.2]
    small = intervention(isolated, cores, 'isolated_heal')
    (public / 'calibration.json').write_text(json.dumps(dict(cases=[small]), indent=2))
    disk, cores = create_state(hidden, 'bulk_state', 'disk', 192, 192, 32, 32, 820, 0.97, 5000)
    disk['times'] = [0, 0.1, 0.7, 2.2, 6]
    bulk = intervention(disk, cores, 'rotating_bulk', target=(1.5, 0))
    single, cores = create_state(hidden, 'single_state', 'single', 128, 128, 15, 15, 110, 0, 2800)
    single['times'] = [0, 0.08, 0.4, 1.6, 3.2]
    single = intervention(single, cores, 'isolated_sound')
    driven, cores = create_state(hidden, 'driven_state', 'driven', 160, 128, 28, 24, 700, 0.90, 4200)
    driven = intervention(driven, cores, 'driven_elliptic')
    driven['drive'] = dict(amplitude=3.0, center=[1.2, -0.8], travel=2.0, frequency=1.1, width=0.8)
    driven['times'] = [0, 0.1, 0.5, 1.6, 4]
    annulus, cores = create_state(hidden, 'annulus_state', 'annulus', 160, 160, 28, 28, 700, 0.85, 3000)
    annulus = intervention(annulus, cores, 'annular_current', target=(6, 0), charge=-2)
    annulus['times'] = [0, 0.1, 0.6, 1.8, 4]
    doublewell, cores = create_state(hidden, 'doublewell_state', 'doublewell', 192, 160, 28, 24, 700, 0.85, 3000)
    doublewell = intervention(doublewell, cores, 'split_domains', target=(6.3, 0))
    doublewell['times'] = [0, 0.1, 0.5, 1.4, 3]
    (hidden / 'manifest.json').write_text(json.dumps(dict(cases=[bulk, single, driven, annulus, doublewell]), indent=2))


if __name__ == '__main__':
    main()
