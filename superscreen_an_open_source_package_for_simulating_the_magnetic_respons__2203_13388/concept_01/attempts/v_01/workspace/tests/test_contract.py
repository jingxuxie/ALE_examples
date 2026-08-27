import numpy as np

from qualification.model import DeviceCase, applied_load, triangle_geometry


def test_affine_stream_current():
    case = DeviceCase({'points': np.array([[0., 0., 0.], [2., 0., 0.], [0., 3., 0.]]),
                       'triangles': np.array([[0, 1, 2]])}, {})
    _, areas, current_x, current_y = triangle_geometry(case)
    stream = 2 * case.points[:, 0] + 3 * case.points[:, 1] + 0.7
    np.testing.assert_allclose(current_x @ stream, 3)
    np.testing.assert_allclose(current_y @ stream, -2)
    np.testing.assert_allclose(areas, 3)


def test_constant_applied_load():
    case = DeviceCase({'points': np.array([[0., 0., 0.], [2., 0., 0.], [0., 3., 0.]]),
                       'triangles': np.array([[0, 1, 2]]), 'drive_H': np.full((1, 3), 2.)}, {})
    np.testing.assert_allclose(applied_load(case), 2)
