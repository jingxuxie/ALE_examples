import numpy as np
from scipy.fft import fft2, ifft2


class Propagator:
    def __init__(self, model):
        self.model = model

    def step(self, psi, time, step, imaginary=False):
        model = self.model
        potential = model.potential(time)
        local = np.exp(-1j * step * potential / 2 - step * model.g * np.abs(psi) ** 2 / 2)
        psi = local * psi
        psi = ifft2(fft2(psi) * np.exp(-1j * step * (model.kx ** 2 + model.ky ** 2) / 2))
        derivative_y, derivative_x = np.gradient(psi, model.dy, model.dx)
        psi += step * model.omega * (model.xx * derivative_y - model.yy * derivative_x)
        psi *= local
        return psi / np.sqrt(model.area * np.sum(np.abs(psi) ** 2))

    def evolve(self, psi, times, dt):
        frames = [psi.copy()]
        time = float(times[0])
        for target in times[1:]:
            count = int(np.ceil((target - time) / dt))
            step = (target - time) / count
            for iteration in range(count):
                psi = self.step(psi, time, step)
                time += step
            time = float(target)
            frames.append(psi.copy())
        return np.asarray(frames)
