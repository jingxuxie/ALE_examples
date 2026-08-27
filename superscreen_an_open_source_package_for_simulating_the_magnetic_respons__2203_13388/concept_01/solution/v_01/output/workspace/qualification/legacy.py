import numpy as np
from scipy.spatial import cKDTree

from .model import MU0, triangle_geometry


def make_device(case):
    import superscreen as sc
    from superscreen.device import Mesh

    if not hasattr(np, 'trapezoid'):
        np.trapezoid = np.trapz
    layers, films, holes, meshes = [], [], [], {}
    for film_index, spec in enumerate(case.meta['films']):
        indices = np.flatnonzero(case.point_film == film_index)
        face_indices = np.flatnonzero(case.triangle_film == film_index)
        local_index = np.full(len(case.points), -1)
        local_index[indices] = np.arange(len(indices))
        faces = local_index[case.triangles[face_indices]]
        points = case.points[indices, :2]
        sums, counts = np.zeros(len(points)), np.zeros(len(points))
        for face, value in zip(faces, case.lambdas[face_indices]):
            if value > 0:
                sums[face] += value
                counts[face] += 1
        material = np.divide(sums, counts, out=np.full_like(sums, spec['nominal_lambda']), where=counts > 0)
        tree = cKDTree(points)

        def local_lambda(x, y, lookup=tree, values=material):
            return values[lookup.query(np.column_stack((x, y)))[1]]

        layer_name = f'layer_{film_index}'
        layers.append(sc.Layer(layer_name, Lambda=sc.Parameter(local_lambda), z0=spec['z0']))
        films.append(sc.Polygon(spec['name'], layer=layer_name, points=spec['outer']))
        for hole_id, contour in zip(spec['hole_ids'], spec['holes']):
            holes.append(sc.Polygon(f'hole_{hole_id}', layer=layer_name, points=contour))
        meshes[spec['name']] = Mesh.from_triangulation(points, faces)
    device = sc.Device(case.meta['id'], layers=layers, films=films, holes=holes, length_units='um')
    device.meshes = meshes
    return device


def solve(case, config='legacy'):
    import superscreen as sc

    device = make_device(case)
    holes = case.prescribed_current.shape[1]
    names = [f'hole_{hole}' for hole in range(holes)]
    model = sc.factorize_model(device=device, current_units='mA')
    iterations = 4 if config != 'uncoupled' else 0
    tree = cKDTree(case.points)

    def run(currents, source, vortices):
        def applied(x, y, z):
            query = np.column_stack((x, y, np.broadcast_to(z, np.shape(x))))
            return MU0 * source[tree.query(query)[1]]

        model.set_circulating_currents(dict(zip(names, currents)))
        model.set_vortices(vortices)
        return sc.solve(model=model, applied_field=sc.Parameter(applied), field_units='mT',
                        iterations=iterations, progress_bar=False)[-1]

    def fluxoid(solution):
        return np.array([sum(solution.hole_fluxoid(name, units='mT * um ** 2', with_units=False)) for name in names])

    inductance = np.empty((holes, holes))
    for hole in range(holes):
        basis = np.zeros(holes)
        basis[hole] = 1
        inductance[:, hole] = fluxoid(run(basis, np.zeros(len(case.points)), []))
    streams, fields, hole_currents, fluxoids = [], [], [], []
    for drive in range(len(case.drive_H)):
        vortices = [sc.Vortex(*item['position'], film=case.meta['films'][item['film']]['name'], nPhi0=item['nPhi0'])
                    for item in case.meta['vortices'] if item['drive'] == drive]
        currents = case.prescribed_current[drive].copy()
        unknown = np.flatnonzero(~np.isfinite(currents))
        currents[unknown] = 0
        offset_solution = run(currents, case.drive_H[drive], vortices)
        if len(unknown):
            currents[unknown] = np.linalg.solve(inductance[np.ix_(unknown, unknown)],
                                                case.target_fluxoid[drive, unknown] - fluxoid(offset_solution)[unknown])
            solution = run(currents, case.drive_H[drive], vortices)
        else:
            solution = offset_solution
        stream = np.zeros(len(case.points))
        for film_index, spec in enumerate(case.meta['films']):
            stream[case.point_film == film_index] = solution.film_solutions[spec['name']].stream
        streams.append(stream)
        fields.append(solution.screening_field_at_position(case.observers, vector=True, units='mT', with_units=False))
        hole_currents.append(currents)
        fluxoids.append(fluxoid(solution))
    stream = np.array(streams)
    _, _, current_x, current_y = triangle_geometry(case)
    current = np.stack(((current_x @ stream.T).T, (current_y @ stream.T).T), axis=-1)
    return {'stream': stream, 'current': current, 'field': np.array(fields),
            'hole_current': np.array(hole_currents), 'fluxoid': np.array(fluxoids), 'inductance': inductance}
