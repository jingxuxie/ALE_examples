from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np
from scipy import sparse


MU0 = 4 * np.pi / 10
PHI0 = 2.067833848


@dataclass
class DeviceCase:
    data: dict
    meta: dict

    def __getattr__(self, name):
        if name in self.data:
            return self.data[name]
        raise AttributeError(name)


def load_case(path):
    path = Path(path)
    with np.load(path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    return DeviceCase(data, json.loads(path.with_suffix('.json').read_text()))


def triangle_geometry(case):
    vertices = case.points[case.triangles]
    cross = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])[:, 2]
    area = np.abs(cross) / 2
    grad_x = np.stack((vertices[:, 1, 1] - vertices[:, 2, 1],
                       vertices[:, 2, 1] - vertices[:, 0, 1],
                       vertices[:, 0, 1] - vertices[:, 1, 1]), axis=1) / cross[:, None]
    grad_y = np.stack((vertices[:, 2, 0] - vertices[:, 1, 0],
                       vertices[:, 0, 0] - vertices[:, 2, 0],
                       vertices[:, 1, 0] - vertices[:, 0, 0]), axis=1) / cross[:, None]
    row = np.repeat(np.arange(len(area)), 3)
    shape = (len(area), len(case.points))
    current_x = sparse.csr_matrix((grad_y.ravel(), (row, case.triangles.ravel())), shape=shape)
    current_y = sparse.csr_matrix((-grad_x.ravel(), (row, case.triangles.ravel())), shape=shape)
    return vertices, area, current_x, current_y


def applied_load(case):
    _, area, _, _ = triangle_geometry(case)
    result = np.zeros_like(case.drive_H)
    values = case.drive_H[:, case.triangles]
    local = area[None, :, None] * (values + values.sum(axis=2)[:, :, None]) / 12
    for drive in range(len(result)):
        np.add.at(result[drive], case.triangles.ravel(), local[drive].ravel())
    return result


def summarize(case, result):
    _, area, _, _ = triangle_geometry(case)
    rows = []
    inductance = result['inductance']
    reciprocity = np.linalg.norm(inductance - inductance.T) / max(np.linalg.norm(inductance), 1e-12)
    linearity = np.linalg.norm(result['field'][3] + 0.7 * result['field'][2]) / max(np.linalg.norm(result['field'][2]), 1e-12)
    for drive in range(len(case.drive_H)):
        unknown = ~np.isfinite(case.prescribed_current[drive])
        rows.append({
            'case': case.meta['id'], 'family': case.meta['family'], 'drive': drive,
            'stream_norm': float(np.linalg.norm(result['stream'][drive])),
            'current_energy': float(np.sum(area[:, None] * case.lambdas[:, None] * result['current'][drive] ** 2)),
            'field_norm': float(np.linalg.norm(result['field'][drive])),
            'hole_current_norm': float(np.linalg.norm(result['hole_current'][drive])),
            'fluxoid_norm': float(np.linalg.norm(result['fluxoid'][drive])),
            'inductance_norm': float(np.linalg.norm(result['inductance'])),
            'reciprocity_error': float(reciprocity),
            'linearity_error': float(linearity),
            'fluxoid_constraint_error': float(np.linalg.norm((result['fluxoid'][drive] - case.target_fluxoid[drive])[unknown])),
        })
    return rows
