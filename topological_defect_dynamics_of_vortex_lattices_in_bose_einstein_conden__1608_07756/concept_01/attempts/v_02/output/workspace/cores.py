import numpy as np


def detect(psi, model):
    horizontal = np.angle(np.conj(psi[:, :-1]) * psi[:, 1:])
    vertical = np.angle(np.conj(psi[:-1, :]) * psi[1:, :])
    winding = horizontal[:-1, :] + vertical[:, 1:] - horizontal[1:, :] - vertical[:, :-1]
    rows, columns = np.nonzero(np.abs(winding) > np.pi)
    if len(rows) == 0:
        return np.empty((0, 3), dtype=float)
    origin = psi[rows, columns]
    along_x = psi[rows, columns + 1] - origin
    along_y = psi[rows + 1, columns] - origin
    mixed = psi[rows + 1, columns + 1] - origin - along_x - along_y
    fraction_x = np.full(len(rows), 0.5)
    fraction_y = np.full(len(rows), 0.5)
    for iteration in range(15):
        value = origin + along_x * fraction_x + along_y * fraction_y + mixed * fraction_x * fraction_y
        derivative_x = along_x + mixed * fraction_y
        derivative_y = along_y + mixed * fraction_x
        determinant = derivative_x.real * derivative_y.imag - derivative_x.imag * derivative_y.real
        valid = np.abs(determinant) > np.finfo(float).tiny
        delta_x = np.divide(value.real * derivative_y.imag - value.imag * derivative_y.real,
                            determinant, out=np.zeros_like(fraction_x), where=valid)
        delta_y = np.divide(derivative_x.real * value.imag - derivative_x.imag * value.real,
                            determinant, out=np.zeros_like(fraction_y), where=valid)
        fraction_x -= delta_x
        fraction_y -= delta_y
        if max(np.max(np.abs(delta_x)), np.max(np.abs(delta_y))) < 1e-12:
            break
    residual = np.abs(origin + along_x * fraction_x + along_y * fraction_y + mixed * fraction_x * fraction_y)
    scale = np.abs(origin) + np.abs(along_x) + np.abs(along_y) + np.abs(mixed)
    valid = ((fraction_x >= -1e-7) & (fraction_x <= 1 + 1e-7)
             & (fraction_y >= -1e-7) & (fraction_y <= 1 + 1e-7) & (residual <= 1e-8 * scale))
    for index in np.flatnonzero(~valid):
        quadratic = np.imag(along_x[index] * np.conj(mixed[index]))
        linear = np.imag(origin[index] * np.conj(mixed[index]) + along_x[index] * np.conj(along_y[index]))
        constant = np.imag(origin[index] * np.conj(along_y[index]))
        coefficients = [quadratic, linear, constant] if abs(quadratic) > 1e-14 * (abs(linear) + abs(constant)) else [linear, constant]
        for root in np.roots(coefficients):
            if abs(root.imag) > 1e-8 or not -1e-7 <= root.real <= 1 + 1e-7:
                continue
            denominator = along_y[index] + mixed[index] * root.real
            if abs(denominator) == 0:
                continue
            other = -(origin[index] + along_x[index] * root.real) / denominator
            if abs(other.imag) < 1e-7 and -1e-7 <= other.real <= 1 + 1e-7:
                fraction_x[index], fraction_y[index] = root.real, other.real
                valid[index] = True
                break
    positions = np.column_stack((model.x[columns] + model.dx * fraction_x,
                                 model.y[rows] + model.dy * fraction_y))
    labels = np.zeros(len(positions), dtype=int)
    labels[valid] = model.sample(model.roi, positions[valid])
    valid &= labels > 0
    charges = np.rint(winding[rows, columns] / (2 * np.pi))
    cores = np.column_stack((positions[valid], charges[valid]))
    if len(cores) > 1:
        keep = np.ones(len(cores), dtype=bool)
        for index in range(len(cores)):
            if keep[index]:
                distance = np.linalg.norm(cores[index + 1:, :2] - cores[index, :2], axis=1)
                keep[index + 1:] &= distance > 1e-7 * min(model.dx, model.dy)
        cores = cores[keep]
    return cores.reshape((-1, 3))
