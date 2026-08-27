import json
import sys
from pathlib import Path

import meshpy.triangle as triangle
import numpy as np
from matplotlib.tri import Triangulation
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / 'concept_01/participant/v_01/workspace'
sys.path.insert(0, str(WORKSPACE))
from qualification.model import MU0, PHI0


def ellipse(radius_x, radius_y=None, center=(0, 0), count=36):
    angle = np.linspace(0, 2 * np.pi, count, endpoint=False)
    return np.stack((radius_x * np.cos(angle) + center[0],
                     (radius_x if radius_y is None else radius_y) * np.sin(angle) + center[1]), axis=1)


def box(width, height, center=(0, 0)):
    return np.array([[-width / 2, -height / 2], [width / 2, -height / 2],
                     [width / 2, height / 2], [-width / 2, height / 2]]) + center


def film(name, outer, holes=(), height=0, penetration=0.15, area=0.08, pattern='constant'):
    return dict(name=name, outer=np.asarray(outer), holes=[np.asarray(hole) for hole in holes],
                z0=height, penetration=penetration, max_area=area, pattern=pattern)


def mesh_film(spec):
    contours = [np.asarray(orient(Polygon(points), sign=1).exterior.coords)[:-1]
                for points in [spec['outer'], *spec['holes']]]
    coordinates, segments, markers = [], [], []
    for contour_number, contour in enumerate(contours):
        offset = len(coordinates)
        coordinates.extend(contour)
        segments.extend((offset + index, offset + (index + 1) % len(contour)) for index in range(len(contour)))
        markers.extend([contour_number + 1] * len(contour))
    info = triangle.MeshInfo()
    info.set_points(coordinates)
    info.set_facets(segments, facet_markers=markers)
    mesh = triangle.build(info, max_volume=spec['max_area'], min_angle=25)
    points = np.array(mesh.points)
    triangles = np.array(mesh.elements)
    marker = np.array(mesh.point_markers)
    region = np.zeros(len(points), dtype=int)
    region[marker == 1] = -1
    for hole_index, contour in enumerate(contours[1:]):
        polygon = Polygon(contour)
        inside = np.array([polygon.covers(Point(point)) for point in points])
        inside |= marker == hole_index + 2
        region[inside] = hole_index + 1
    vertices = points[triangles]
    negative = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0]) < 0
    triangles[negative] = triangles[negative][:, [0, 2, 1]]
    centroids = points[triangles].mean(axis=1)
    lambdas = np.full(len(triangles), spec['penetration'])
    if spec['pattern'] == 'junction':
        lambdas *= np.where(centroids[:, 0] < 0, 0.15, 6.0)
    elif spec['pattern'] == 'island':
        lambdas *= np.where((centroids[:, 0] + 0.3) ** 2 + 2 * centroids[:, 1] ** 2 < 1.1, 9.0, 0.2)
    elif spec['pattern'] == 'smooth':
        lambdas *= 1.5 + 1.2 * np.tanh(centroids[:, 0] / 0.6)
    tags = region[triangles]
    lambdas[(tags[:, 0] > 0) & np.all(tags == tags[:, :1], axis=1)] = 0
    return points, triangles, region, lambdas, contours


def make_case(identifier, family, specs, directory, vortex=False):
    all_points, all_triangles, all_regions, all_lambdas = [], [], [], []
    point_films, triangle_films, film_meta = [], [], []
    hole_offset = 0
    point_offset = 0
    for film_index, spec in enumerate(specs):
        points, triangles, regions, lambdas, contours = mesh_film(spec)
        regions[regions > 0] += hole_offset
        all_points.append(np.column_stack((points, np.full(len(points), spec['z0']))))
        all_triangles.append(triangles + point_offset)
        all_regions.append(regions)
        all_lambdas.append(lambdas)
        point_films.extend([film_index] * len(points))
        triangle_films.extend([film_index] * len(triangles))
        film_meta.append({'name': spec['name'], 'z0': spec['z0'], 'outer': contours[0].tolist(),
                          'holes': [contour.tolist() for contour in contours[1:]],
                          'hole_ids': list(range(hole_offset, hole_offset + len(spec['holes']))),
                          'nominal_lambda': spec['penetration'], 'pattern': spec['pattern']})
        point_offset += len(points)
        hole_offset += len(spec['holes'])
    points, triangles = np.concatenate(all_points), np.concatenate(all_triangles)
    regions, lambdas = np.concatenate(all_regions), np.concatenate(all_lambdas)
    point_films, triangle_films = np.array(point_films), np.array(triangle_films)
    centroid = points[:, :2].mean(axis=0)
    span = np.ptp(points[:, :2], axis=0)
    drive_H = np.zeros((4, len(points)))
    dipole_origin = np.array([centroid[0] + 0.15 * span[0], centroid[1] - 0.17 * span[1], points[:, 2].max() + 1.4])
    displacement = points - dipole_origin
    radius_squared = np.sum(displacement ** 2, axis=1)
    dipole = (3 * displacement[:, 2] ** 2 - radius_squared) / radius_squared ** 2.5
    drive_H[1] = 0.13 + 0.08 * dipole
    drive_H[2] = -0.05 + 0.24 * dipole
    currents = np.zeros((4, hole_offset))
    targets = np.zeros_like(currents)
    if hole_offset:
        currents[0, 0] = 1
        currents[1] = np.nan
        currents[2] = np.nan
        if hole_offset > 1:
            currents[2, 0] = -0.4
        targets[2, -1] = 0.7 * PHI0
    else:
        drive_H[0] = 0.2
    vortex_load = np.zeros_like(drive_H)
    vortex_meta = []
    if vortex:
        selected_film = 0
        candidate_triangles = np.flatnonzero((triangle_films == selected_film) & np.all(regions[triangles] == 0, axis=1))
        centers = points[triangles[candidate_triangles]].mean(axis=1)
        chosen = candidate_triangles[np.argmin(np.sum((centers[:, :2] - (centroid + [0.3, 0.3])) ** 2, axis=1))]
        vortex_load[2, triangles[chosen]] = PHI0 / MU0 / 3
        position = points[triangles[chosen]].mean(axis=0)
        vortex_meta.append({'drive': 2, 'film': 0, 'position': position[:2].tolist(), 'nPhi0': 1.0})
    drive_H[3] = -0.7 * drive_H[2]
    currents[3] = -0.7 * currents[2]
    targets[3] = -0.7 * targets[2]
    vortex_load[3] = -0.7 * vortex_load[2]
    if vortex:
        vortex_meta.append({**vortex_meta[0], 'drive': 3, 'nPhi0': -0.7})
    observers = []
    for film_index, spec in enumerate(specs):
        indices = np.flatnonzero((triangle_films == film_index) & ~np.all(regions[triangles] > 0, axis=1))
        selected = indices[np.linspace(0, len(indices) - 1, 12, dtype=int)]
        centers = points[triangles[selected]].mean(axis=1)
        for lift in (0.006, -0.006, 0.11, 0.7):
            observers.extend(centers + np.array([0, 0, lift]))
    observers.extend(np.column_stack((np.linspace(points[:, 0].min(), points[:, 0].max(), 17),
                                     np.full(17, centroid[1]), np.full(17, points[:, 2].max() + 0.5))))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{identifier}.npz'
    np.savez_compressed(path, points=points, triangles=triangles, region=regions, lambdas=lambdas,
                        point_film=point_films, triangle_film=triangle_films, drive_H=drive_H,
                        vortex_load=vortex_load, prescribed_current=currents, target_fluxoid=targets,
                        observers=np.array(observers))
    path.with_suffix('.json').write_text(json.dumps({'id': identifier, 'family': family, 'films': film_meta,
                                                   'vortices': vortex_meta, 'drives': ['current_drive', 'zero_fluxoid', 'mixed', 'linearity']}, indent=2))
    print(identifier, len(points), len(triangles), hole_offset, flush=True)
    return path


def ibm_specs():
    from device_layouts.ibm.small import make_squid
    device = make_squid(with_terminals=False)
    holes_by_film = device.holes_by_film()
    specs = []
    for name, polygon in device.films.items():
        layer = device.layers[polygon.layer]
        outer = np.array(polygon.polygon.simplify(0.025, preserve_topology=True).exterior.coords)[:-1]
        holes = [np.array(hole.polygon.simplify(0.012, preserve_topology=True).exterior.coords)[:-1]
                 for hole in holes_by_film[name]]
        specs.append(film(name, outer, holes, height=layer.z0, penetration=layer.Lambda, area=0.16))
    return specs


def main():
    public = ROOT / 'concept_01/participant/v_01/input'
    hidden = ROOT / 'concept_01/evaluator/hidden'
    paths = []
    paths.append(make_case('dev_ring', 'annular', [film('washer', ellipse(2.4), [ellipse(0.7, count=24)], area=0.13)], public))
    paths.append(make_case('dev_holes', 'perforated', [film('body', box(5, 3), [ellipse(0.55, 0.7, (-1.1, 0), 22), box(0.6, 0.9, (1, 0.2))], area=0.15)], public))
    paths.append(make_case('dev_pattern', 'patterned', [film('body', box(3.4, 2.6), [ellipse(0.45, count=20)], area=0.09, pattern='junction')], public))
    paths.append(make_case('dev_stack', 'shield_stack', [film('lower', ellipse(1.8), [ellipse(0.6, count=20)], area=0.15),
                                                      film('upper', box(3, 2.4, (0.2, 0.1)), height=0.08, area=0.15)], public))
    hidden_paths = []
    hidden_paths.append(make_case('h_annular', 'annular_kinetic', [film('ring', ellipse(2.2, 1.65), [ellipse(0.8, 0.6, (0.08, 0), 26)], penetration=1.4, area=0.12)], hidden))
    hidden_paths.append(make_case('h_perforated', 'asymmetric_multihole', [film('body', box(5.6, 3.6), [ellipse(0.68, 0.9, (-1.3, 0.15), 24), box(0.85, 0.7, (0.95, -0.6)), ellipse(0.37, 0.4, (1.5, 0.85), 18)], penetration=0.045, area=0.19)], hidden))
    hidden_paths.append(make_case('h_ibm', 'official_ibm_multilayer', ibm_specs(), hidden))
    hidden_paths.append(make_case('h_close', 'close_shield_stack', [film('drive', ellipse(1.9), [ellipse(0.7, count=24)], penetration=0.025, area=0.17),
                                                                 film('screen', box(3.4, 2.5, (0.25, -0.15)), height=0.024, penetration=0.055, area=0.16),
                                                                 film('receiver', ellipse(1.3, 0.9, (0.1, 0.1)), [ellipse(0.45, 0.3, (0.1, 0.1), 20)], height=0.085, penetration=0.08, area=0.16)], hidden))
    hidden_paths.append(make_case('h_pattern', 'material_island', [film('body', box(4.2, 3.3), [box(0.7, 0.85, (-1.05, 0))], penetration=0.15, area=0.11, pattern='island')], hidden))
    slit = np.array([[-2, -1.6], [2, -1.6], [2, 1.6], [0.35, 1.6], [0.35, -0.35], [-0.35, -0.35], [-0.35, 1.6], [-2, 1.6]])
    hidden_paths.append(make_case('h_vortex', 'vortex_slit', [film('slotted', slit, penetration=0.32, area=0.085, pattern='smooth')], hidden, vortex=True))
    for directory, items in [(public, paths), (hidden, hidden_paths)]:
        (directory / 'suite.json').write_text(json.dumps({'cases': [path.name for path in items]}, indent=2))


if __name__ == '__main__':
    main()
