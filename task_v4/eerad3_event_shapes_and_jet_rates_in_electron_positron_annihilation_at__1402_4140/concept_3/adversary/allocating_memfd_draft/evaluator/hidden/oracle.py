import math
import mpmath as mp
import numpy as np


def minkowski(left, right):
    return left[3] * right[3] - sum(left[index] * right[index] for index in range(3))


def null_vectors(raw):
    vectors = [[mp.mpf(value) for value in vector] for vector in raw]
    for vector in vectors:
        vector[3] = mp.sqrt(sum(value * value for value in vector[:3]))
    return vectors


def geometric(case, digits=90):
    with mp.workdps(digits):
        vectors = null_vectors(case['p'])
        total_energy = sum(vector[3] for vector in vectors)
        invariants = [[2 * minkowski(left, right) / total_energy**2 for right in vectors] for left in vectors]
        labels = [value - 1 for value in case['labels']]
        slots = [value - 1 for value in case['slots']]
        radiator, first, second, recoil, spectator = [vectors[index] for index in labels]
        antenna = [sum(vector[index] for vector in [radiator, first, second, recoil]) for index in range(4)]
        ya1, ya2, y1b, y2b, y12, yab = [2*minkowski(left, right) for left, right in
            [(radiator, first), (radiator, second), (first, recoil), (second, recoil), (first, second), (radiator, recoil)]]
        weight1 = (y1b+y12)/(ya1+y1b+y12)
        weight2 = y2b/(ya2+y2b+y12)
        unresolved = [weight1*first[index]+weight2*second[index] for index in range(4)]
        ratio = minkowski(antenna, radiator)/minkowski(antenna, recoil)
        offset = (minkowski(antenna, antenna)/2-minkowski(antenna, unresolved))/minkowski(antenna, recoil)
        origin = [unresolved[index]+offset*recoil[index] for index in range(4)]
        direction = [radiator[index]-ratio*recoil[index] for index in range(4)]
        linear = minkowski(origin, direction)
        quadratic = -ratio*yab
        discriminant = linear**2-quadratic*minkowski(origin, origin)
        if discriminant <= 0 or yab <= 0:
            raise ValueError('Degenerate antenna')
        coefficient = (-linear-mp.sqrt(discriminant))/quadratic
        mapped_first = [origin[index]+coefficient*direction[index] for index in range(4)]
        mapped_second = [antenna[index]-mapped_first[index] for index in range(4)]
        mapped = [None]*3
        for slot, vector in zip(slots, [mapped_first, mapped_second, spectator]):
            mapped[slot] = vector
        mapped_invariants = [2*minkowski(mapped[left],mapped[right])/total_energy**2 for left,right in [(0,1),(0,2),(1,2)]]
        shell = max(abs(minkowski(vector,vector))/total_energy**2 for vector in mapped)
        conservation = max(abs(sum(vector[index] for vector in mapped)-sum(vector[index] for vector in vectors))/total_energy for index in range(4))
        if shell > mp.mpf('1e-45') or conservation > mp.mpf('1e-45') or min(vector[3] for vector in mapped) <= 0:
            raise AssertionError('Geometric oracle failed independent physical checks')
        return {'y': [[float(value) for value in row] for row in invariants],
                'mapped': [[float(value) for value in row] for row in mapped],
                's': [float(value) for value in mapped_invariants]}


def dak_crosscheck(case, digits=110):
    with mp.workdps(digits):
        vectors = null_vectors(case['p'])
        labels = [value-1 for value in case['labels']]
        radiator, first, second, recoil, spectator = [vectors[index] for index in labels]
        ya1, ya2, y1b, y2b, y12, yab = [2*minkowski(left,right) for left,right in
            [(radiator,first),(radiator,second),(first,recoil),(second,recoil),(first,second),(radiator,recoil)]]
        total = ya1+ya2+y1b+y2b+y12+yab
        weight1 = (y1b+y12)/(ya1+y1b+y12)
        weight2 = y2b/(ya2+y2b+y12)
        gram = yab**2*y12**2+ya1**2*y2b**2+ya2**2*y1b**2-2*(yab*ya1*y2b*y12+yab*ya2*y1b*y12+ya1*ya2*y1b*y2b)
        rho = mp.sqrt(1+(weight1-weight2)**2*gram/yab**2/total**2+
            ((weight1*(1-weight2)+weight2*(1-weight1))*2*(yab*ya1*y2b+yab*ya2*y1b-yab**2*y12)+
            4*weight1*(1-weight1)*yab*ya1*y1b+4*weight2*(1-weight2)*yab*ya2*y2b)/yab**2/total)
        asymmetry = (ya1*y2b-ya2*y1b)*(weight1-weight2)/yab
        left = ((1+rho)*total-(2*y1b+y12)*weight1-(2*y2b+y12)*weight2+asymmetry)/(2*(yab+ya1+ya2))
        right = ((1-rho)*total-(2*ya1+y12)*weight1-(2*ya2+y12)*weight2-asymmetry)/(2*(yab+y1b+y2b))
        mapped = [left*radiator[index]+weight1*first[index]+weight2*second[index]+right*recoil[index] for index in range(4)]
        return np.array([float(value) for value in mapped])


def check(case, reference, values, target):
    values = np.asarray(values)
    if values.shape != (84,) or not np.isfinite(values).all():
        return ['nonfinite_or_wrong_shape']
    raw = np.asarray(case['p'])
    energy = raw[:,3].sum()
    invariants = values[:25].reshape((5,5),order='F')
    mapped = values[25:37].reshape((4,3),order='F').T / energy
    reported = values[37:40]
    saved = values[40:52].reshape((4,3),order='F').T / energy
    rotation = values[52:68].reshape((4,4),order='F')
    inverse = values[68:84].reshape((4,4),order='F')
    expected = np.asarray(reference['mapped']) / energy
    expected_y = np.asarray(reference['y'])
    errors = []
    resolved = case['family'] in ['generic','rotation','relabel','scale','metamorphic']
    component_tolerance = 3e-12 if resolved else target['momentum_atol']
    mapped_tolerance = 3e-12 if resolved else target['mapped_invariant_atol']
    radiator_left = raw[case['labels'][0]-1,:3]
    radiator_right = raw[case['labels'][3]-1,:3]
    left_scaled = radiator_left/np.max(np.abs(radiator_left))
    right_scaled = radiator_right/np.max(np.abs(radiator_right))
    opening = np.linalg.norm(left_scaled/np.linalg.norm(left_scaled)-right_scaled/np.linalg.norm(right_scaled))
    orientation_slack = 16*np.finfo(float).eps/opening if opening < 1e-4 else 0.
    component_tolerance += orientation_slack
    mapped_tolerance += 2*orientation_slack
    off_diagonal = ~np.eye(5,dtype=bool)
    if np.any(np.abs(invariants-expected_y)[off_diagonal] > target['invariant_rtol']*np.abs(expected_y)[off_diagonal]+target['invariant_atol']):
        errors.append('input_invariants')
    if np.max(np.abs(np.diag(invariants))) > target['invariant_atol'] or np.max(np.abs(invariants-invariants.T)) > 1e-15:
        errors.append('invariant_bookkeeping')
    if np.max(np.abs(mapped-expected)) > component_tolerance:
        errors.append('map_oracle')
    if np.max(np.abs(reported-reference['s'])) > mapped_tolerance:
        errors.append('mapped_invariants')
    shells = mapped[:,3]**2-np.sum(mapped[:,:3]**2,axis=1)
    if np.max(np.abs(shells)) > target['shell_atol'] or np.min(mapped[:,3]) <= 0:
        errors.append('mass_shell_or_energy')
    if np.max(np.abs(mapped.sum(axis=0)-raw.sum(axis=0)/energy)) > target['conservation_atol']:
        errors.append('conservation')
    if np.max(np.abs(saved-mapped)) > 1e-14:
        errors.append('mapmomenta_bookkeeping')
    spectator_slot = case['slots'][2]-1
    spectator_label = case['labels'][4]-1
    if np.max(np.abs(mapped[spectator_slot]-raw[spectator_label]/energy)) > 1e-14:
        errors.append('spectator')
    physical_s = np.array([2*(mapped[left,3]*mapped[right,3]-np.dot(mapped[left,:3],mapped[right,:3])) for left,right in [(0,1),(0,2),(1,2)]])
    if np.max(np.abs(physical_s-reported)) > target['mapped_invariant_atol']:
        errors.append('invariant_consistency')
    axis = np.asarray(case['axis'][:3])
    axis = axis/np.max(np.abs(axis))
    aligned = rotation[:3,:3]@axis
    if max(np.max(np.abs(rotation@rotation.T-np.eye(4))),np.max(np.abs(inverse-rotation.T)),
           abs(np.linalg.det(rotation[:3,:3])-1),np.max(np.abs(rotation[3]-[0,0,0,1])),
           np.max(np.abs(rotation[:,3]-[0,0,0,1])),np.max(np.abs(aligned[:2])),
           abs(aligned[2]-np.linalg.norm(axis))) > target['rotation_atol']:
        errors.append('rotation')
    if case['family'] != 'rotation':
        cosine = abs(axis[0])/np.hypot(axis[0],axis[1])
        sine = np.sign(axis[0])*axis[1]/np.hypot(axis[0],axis[1])
        polarcos = axis[2]/np.linalg.norm(axis)
        polarsin = (cosine*axis[0]+sine*axis[1])/np.linalg.norm(axis)
        conventional = np.array([[polarcos*cosine,polarcos*sine,-polarsin],[-sine,cosine,0],
                                 [polarsin*cosine,polarsin*sine,polarcos]])
        if np.max(np.abs(rotation[:3,:3]-conventional)) > target['rotation_atol']:
            errors.append('rotation_convention')
    if case.get('limit'):
        for slot, vector in zip(case['slots'][:2],case['limit']):
            if np.max(np.abs(mapped[slot-1]-np.asarray(vector)/energy)) > case['limit_bound']:
                errors.append('hard_limit_identity')
                break
    return errors
