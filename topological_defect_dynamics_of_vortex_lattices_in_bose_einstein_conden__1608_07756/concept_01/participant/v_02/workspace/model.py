import numpy as np


class Model:
    def __init__(self, case, arrays):
        self.case = case
        self.x = arrays['x']
        self.y = arrays['y']
        self.dx = float(self.x[1] - self.x[0])
        self.dy = float(self.y[1] - self.y[0])
        self.area = self.dx * self.dy
        self.xx, self.yy = np.meshgrid(self.x, self.y)
        self.kx = 2 * np.pi * np.fft.fftfreq(len(self.x), self.dx)[None, :]
        self.ky = 2 * np.pi * np.fft.fftfreq(len(self.y), self.dy)[:, None]
        self.roi = arrays['roi']
        self.bulk = arrays['bulk'].astype(bool)
        self.base = arrays['potential']
        self.g = case['g']
        self.omega = case['omega']

    def potential(self, time):
        drive = self.case.get('drive')
        if not drive:
            return self.base
        center = drive['center']
        displacement = drive['travel'] * np.sin(drive['frequency'] * time)
        radius2 = (self.xx - center[0] - displacement) ** 2 + (self.yy - center[1]) ** 2
        return self.base + drive['amplitude'] * np.sin(drive['frequency'] * time) ** 2 * np.exp(-radius2 / (2 * drive['width'] ** 2))

    def sample(self, image, positions):
        if len(positions) == 0:
            return np.empty(0, dtype=image.dtype)
        columns = np.clip(np.rint((positions[:, 0] - self.x[0]) / self.dx).astype(int), 0, len(self.x) - 1)
        rows = np.clip(np.rint((positions[:, 1] - self.y[0]) / self.dy).astype(int), 0, len(self.y) - 1)
        return image[rows, columns]


def imprint(psi, model, operations):
    phase = np.zeros_like(model.xx)
    for operation in operations:
        phase += operation['charge'] * np.arctan2(model.yy - operation['y'], model.xx - operation['x'])
    return psi * np.exp(1j * phase)
