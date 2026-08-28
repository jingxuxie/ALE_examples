import json
import sys
from pathlib import Path

import numpy as np


def create(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    cases = []
    specifications = [('elliptic_drive', 144, 112, 20, 16),
                      ('annular_current', 128, 112, 20, 18),
                      ('separated_domains', 160, 112, 26, 18)]
    for name, nx, ny, length_x, length_y in specifications:
        axis_x = (np.arange(nx) - nx / 2) * length_x / nx
        axis_y = (np.arange(ny) - ny / 2) * length_y / ny
        grid_x, grid_y = np.meshgrid(axis_x, axis_y)
        radius2 = grid_x ** 2 + grid_y ** 2
        case = dict(id=name, asset=name + '.npz', times=[0, 0.1, 0.5, 1.5, 3.0, 6.0],
                    imprints=[], correlation_edges=[0, 2.5, 5, 30],
                    spectrum_edges=[0, 1, 2, 4, 8, 16, 100])
        if name == 'elliptic_drive':
            potential = (0.65 * grid_x ** 2 + 1.4 * grid_y ** 2) / 2
            psi = np.exp(-(grid_x ** 2 / 5 + grid_y ** 2 / 3) / 2).astype(complex)
            for position_x, position_y, charge in [(-0.8, -0.3, 1), (0.9, 0.4, 1), (0.1, 1.3, -1)]:
                delta_x, delta_y = grid_x - position_x, grid_y - position_y
                psi *= (delta_x + 1j * charge * delta_y) / np.sqrt(0.2 + delta_x ** 2 + delta_y ** 2)
            roi = (grid_x ** 2 / 36 + grid_y ** 2 / 16 < 1).astype(int)
            bulk = grid_x ** 2 / 16 + grid_y ** 2 / 6.25 < 1
            case.update(g=500, omega=-0.72,
                        drive=dict(amplitude=4, frequency=1.4, travel=1.2, center=[0.3, -0.4], width=0.8),
                        imprints=[dict(x=-0.8, y=-0.3, charge=-1)])
        elif name == 'annular_current':
            radius = np.sqrt(radius2)
            potential = 0.6 * (radius - 3.4) ** 2
            psi = (grid_x + 1j * grid_y) ** 3 * np.exp(-radius2 / 5)
            roi = ((radius > 1.8) & (radius < 5.6)).astype(int)
            bulk = (radius > 2.5) & (radius < 4.8)
            case.update(g=300, omega=0.6)
        else:
            left2 = (grid_x + 4.2) ** 2 + grid_y ** 2
            right2 = (grid_x - 4.2) ** 2 + grid_y ** 2
            potential = 0.5 * np.minimum(left2, right2) + 8 * np.exp(-grid_x ** 2 / 0.4)
            psi = np.zeros_like(grid_x, dtype=complex)
            for center, angle in [(-4.2, 0), (4.2, np.pi / 6)]:
                component = np.exp(-((grid_x - center) ** 2 + grid_y ** 2) / 4).astype(complex)
                for phase in np.arange(6) * np.pi / 3 + angle:
                    delta_x = grid_x - center - 1.5 * np.cos(phase)
                    delta_y = grid_y - 1.5 * np.sin(phase)
                    component *= (delta_x + 1j * delta_y) / np.sqrt(0.15 + delta_x ** 2 + delta_y ** 2)
                psi += component
            roi = np.where(left2 < 3.5 ** 2, 1, np.where(right2 < 3.5 ** 2, 2, 0))
            bulk = (left2 < 2.5 ** 2) | (right2 < 2.5 ** 2)
            case.update(g=900, omega=0.42)
        psi /= np.sqrt(np.sum(np.abs(psi) ** 2) * (length_x / nx) * (length_y / ny))
        np.savez_compressed(destination / case['asset'], x=axis_x, y=axis_y, psi=psi,
                            potential=potential, roi=roi, bulk=bulk)
        cases.append(case)
    (destination / 'manifest.json').write_text(json.dumps(dict(cases=cases), indent=2))


if __name__ == '__main__':
    create(sys.argv[1])
