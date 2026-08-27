import numpy as np


def detect(psi, model):
    horizontal = np.angle(psi[:, 1:] * np.conj(psi[:, :-1]))
    vertical = np.angle(psi[1:, :] * np.conj(psi[:-1, :]))
    winding = horizontal[:-1] + vertical[:, 1:] - horizontal[1:] - vertical[:, :-1]
    rows, columns = np.where(np.abs(winding) > np.pi)
    found = []
    for row, column in zip(rows, columns):
        corners = psi[row:row + 2, column:column + 2]
        base = corners[0, 0]
        along_x = corners[0, 1] - base
        along_y = corners[1, 0] - base
        mixed = corners[1, 1] - base - along_x - along_y
        offset_x, offset_y = 0.5, 0.5
        for iteration in range(8):
            value = base + along_x * offset_x + along_y * offset_y + mixed * offset_x * offset_y
            tangent_x = along_x + mixed * offset_y
            tangent_y = along_y + mixed * offset_x
            matrix = np.array([[tangent_x.real, tangent_y.real], [tangent_x.imag, tangent_y.imag]])
            try:
                update = np.linalg.solve(matrix, [value.real, value.imag])
            except np.linalg.LinAlgError:
                break
            offset_x -= update[0]
            offset_y -= update[1]
            if np.linalg.norm(update) < 1e-9:
                break
        if not (-0.05 <= offset_x <= 1.05 and -0.05 <= offset_y <= 1.05):
            offset_x, offset_y = 0.5, 0.5
        position = np.array([[model.x[column] + offset_x * model.dx, model.y[row] + offset_y * model.dy]])
        if model.sample(model.roi, position)[0] > 0:
            found.append([position[0, 0], position[0, 1], int(np.sign(winding[row, column]))])
    return np.asarray(found, dtype=float).reshape(-1, 3)
