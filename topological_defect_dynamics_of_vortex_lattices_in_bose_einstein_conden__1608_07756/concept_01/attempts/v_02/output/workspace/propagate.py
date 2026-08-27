import numpy as np
from scipy.fft import fft, ifft


class Propagator:
    def __init__(self, model, configuration=None):
        self.model = model
        self.configuration = configuration or {}
        self.method = self.configuration.get('method', 'suzuki4')
        if self.method not in ('strang2', 'yoshida4', 'suzuki4'):
            raise ValueError('method must be strang2, yoshida4, or suzuki4')
        self.cache = {}
        self.steps = 0
        self.max_step = 0.0

    def factors(self, step):
        key = float(step)
        if key not in self.cache:
            model = self.model
            horizontal = model.kx ** 2 / 2 + model.omega * model.yy * model.kx
            vertical = model.ky ** 2 / 2 - model.omega * model.xx * model.ky
            if len(self.cache) > 24:
                self.cache.clear()
            self.cache[key] = (np.exp(-0.5j * step * horizontal),
                               np.exp(-1j * step * vertical))
        return self.cache[key]

    def step(self, psi, time, step):
        model = self.model
        potential = model.potential(time + step / 2)
        horizontal, vertical = self.factors(step)
        psi = psi * np.exp(-0.5j * step * (potential + model.g * np.abs(psi) ** 2))
        psi = ifft(fft(psi, axis=1, workers=1) * horizontal, axis=1, workers=1)
        psi = ifft(fft(psi, axis=0, workers=1) * vertical, axis=0, workers=1)
        psi = ifft(fft(psi, axis=1, workers=1) * horizontal, axis=1, workers=1)
        return psi * np.exp(-0.5j * step * (potential + model.g * np.abs(psi) ** 2))

    def evolve(self, psi, times, dt):
        times = np.asarray(times, dtype=float)
        if dt <= 0 or not np.isfinite(dt):
            raise ValueError('dt must be finite and positive')
        if len(times) == 0 or times[0] != 0 or np.any(np.diff(times) <= 0):
            raise ValueError('times must start at zero and strictly increase')
        kinetic_limit = self.configuration.get('kinetic_phase_limit')
        nonlinear_limit = self.configuration.get('nonlinear_phase_limit')
        if kinetic_limit is not None:
            maximum_kinetic = float(np.max((self.model.kx ** 2 + self.model.ky ** 2) / 2))
            dt = min(dt, kinetic_limit / maximum_kinetic)
        if nonlinear_limit is not None and self.model.g != 0:
            maximum_nonlinear = abs(self.model.g) * float(np.max(np.abs(psi) ** 2))
            if maximum_nonlinear > 0:
                dt = min(dt, nonlinear_limit / maximum_nonlinear)
        if self.method == 'suzuki4':
            outer = 1 / (4 - 4 ** (1 / 3))
            weights = (outer, outer, 1 - 4 * outer, outer, outer)
        elif self.method == 'yoshida4':
            outer = 1 / (2 - 2 ** (1 / 3))
            weights = (outer, 1 - 2 * outer, outer)
        else:
            weights = (1.0,)
        frames = [psi.copy()]
        for start, target in zip(times[:-1], times[1:]):
            count = max(1, int(np.ceil((target - start) / dt - 1e-12)))
            step = (target - start) / count
            self.max_step = max(self.max_step, step)
            for iteration in range(count):
                time = start + iteration * step
                for weight in weights:
                    psi = self.step(psi, time, step * weight)
                    time += step * weight
                self.steps += 1
            frames.append(psi.copy())
        return np.asarray(frames)
