import numpy as np
from scipy.fft import fft, ifft


class Propagator:
    def __init__(self, model):
        self.model = model
        self.cache = {}

    def step(self, psi, time, step, imaginary=False):
        model = self.model
        factor = -1 if imaginary else -1j
        key = (round(step, 14), imaginary)
        if key not in self.cache:
            kinetic_x = model.kx ** 2 / 2 + model.omega * model.yy * model.kx
            kinetic_y = model.ky ** 2 / 2 - model.omega * model.xx * model.ky
            self.cache[key] = (np.exp(factor * step * kinetic_x / 2), np.exp(factor * step * kinetic_y))
        operator_x, operator_y = self.cache[key]
        potential = model.potential(time + step / 2)
        psi = psi * np.exp(factor * step / 2 * (potential + model.g * np.abs(psi) ** 2))
        psi = ifft(fft(psi, axis=1) * operator_x, axis=1)
        psi = ifft(fft(psi, axis=0) * operator_y, axis=0)
        psi = ifft(fft(psi, axis=1) * operator_x, axis=1)
        psi *= np.exp(factor * step / 2 * (potential + model.g * np.abs(psi) ** 2))
        if imaginary:
            psi /= np.sqrt(model.area * np.sum(np.abs(psi) ** 2))
        return psi

    def evolve(self, psi, times, dt):
        time = float(times[0])
        frames = [psi.copy()]
        for target in times[1:]:
            count = int(np.ceil((target - time) / dt - 1e-10))
            step = (target - time) / count
            for iteration in range(count):
                psi = self.step(psi, time, step)
                time += step
            time = float(target)
            frames.append(psi.copy())
        return np.asarray(frames)
