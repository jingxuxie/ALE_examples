import json
import time
from pathlib import Path

import numpy as np
from scipy.fft import fft2, ifft2

from experiment import write_csv
from model import Model, imprint


ROOT = Path(__file__).resolve().parent.parent


def derivative(psi, model, time):
    transformed = fft2(psi, workers=1)
    laplacian = ifft2(-(model.kx ** 2 + model.ky ** 2) * transformed, workers=1)
    derivative_x = ifft2(1j * model.kx * transformed, workers=1)
    derivative_y = ifft2(1j * model.ky * transformed, workers=1)
    return (0.5j * laplacian - 1j * (model.potential(time) + model.g * abs(psi) ** 2) * psi
            + model.omega * (model.xx * derivative_y - model.yy * derivative_x))


def error(first, second, area):
    phase = np.angle(np.vdot(second, first))
    return float(np.sqrt(area * np.sum(abs(first * np.exp(-1j * phase) - second) ** 2)))


def main():
    output = ROOT / 'experiments/independent'
    output.mkdir(exist_ok=True)
    records = []
    sources = [(ROOT / 'inputs/campaign.json', ''),
               (ROOT / 'experiments/transfer_input/manifest.json', 'transfer_')]
    for manifest, prefix in sources:
        cases = json.loads(manifest.read_text())['cases']
        if not prefix:
            cases = [case for case in cases if case['id'] == 'vacancy']
        for case in cases:
            with np.load(manifest.parent / case['asset']) as asset:
                model = Model(case, asset)
                initial = imprint(asset['psi'].copy(), model, case['imprints'])
            target = case['times'][1]
            steps = int(np.ceil(target / 0.0001))
            step = target / steps
            psi = initial.copy()
            started = time.perf_counter()
            for iteration in range(steps):
                time_value = iteration * step
                first = derivative(psi, model, time_value)
                second = derivative(psi + step * first / 2, model, time_value + step / 2)
                third = derivative(psi + step * second / 2, model, time_value + step / 2)
                fourth = derivative(psi + step * third, model, time_value + step)
                psi += step * (first + 2 * second + 2 * third + fourth) / 6
            elapsed = time.perf_counter() - started
            primary = np.load(ROOT / 'experiments' / (prefix + 'primary') / (case['id'] + '.npz'))['psi'][1]
            refined = np.load(ROOT / 'experiments' / (prefix + 'refinement') / (case['id'] + '.npz'))['psi'][1]
            records.append(dict(case=case['id'], frame=1, time=target, rk4_dt=step,
                                primary_wave_l2=error(primary, psi, model.area),
                                refinement_wave_l2=error(refined, psi, model.area),
                                rk4_norm_drift=float(model.area * (np.sum(abs(psi) ** 2) - np.sum(abs(initial) ** 2))),
                                rk4_wall_seconds=elapsed))
            np.savez_compressed(output / (case['id'] + '_rk4.npz'), psi=np.array([initial, psi]), times=[0, target])
            print(records[-1], flush=True)
    write_csv(ROOT / 'independent_solver.csv', records)


if __name__ == '__main__':
    main()
