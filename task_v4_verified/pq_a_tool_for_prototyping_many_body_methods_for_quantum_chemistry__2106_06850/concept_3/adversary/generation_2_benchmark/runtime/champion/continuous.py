import ctypes
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from assemble import *


class Model:
    def __init__(self, case):
        self.case = case
        self.library = ctypes.CDLL(str(Path('model.so').resolve()))
        self.library.initialize.argtypes = [ctypes.c_char_p]
        self.library.evaluate.argtypes = [ctypes.c_int, np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')]
        self.dimension = self.library.initialize((case.case_id+'.dat').encode())
        alpha_mask = sum(1 << orbital for orbital in range(0, case.n_orbitals, 2))
        self.keep = [index for index, mask in enumerate(case.determinants) if (mask & alpha_mask).bit_count() == case.n_alpha]
        self.target = case.target[self.keep]
        self.labels = allowed_excitations(case.n_orbitals)
        self.pairs = [rotation_pairs(case.n_orbitals, case.n_electrons, label) for label in self.labels]

    def evaluate(self, labels, angles):
        labels = np.ascontiguousarray(labels, dtype=np.int32)
        angles = np.ascontiguousarray(angles, dtype=np.float64)
        state = np.empty(self.dimension)
        jacobian = np.empty((self.dimension,len(labels)))
        self.library.evaluate(len(labels), labels, angles, state, jacobian)
        return state, jacobian

    def fit(self, labels, angles, evaluations=100):
        labels = np.asarray(labels, dtype=np.int32)
        state, jacobian = self.evaluate(labels, angles)
        phase = 1 if np.dot(state, self.target) >= 0 else -1
        previous = None
        cached = None

        def calculation(parameters):
            nonlocal previous, cached
            if previous is None or not np.array_equal(parameters, previous):
                state, jacobian = self.evaluate(labels, parameters)
                cached = state-phase*self.target, jacobian
                previous = parameters.copy()
            return cached

        result = least_squares(lambda parameters: calculation(parameters)[0], angles, jac=lambda parameters: calculation(parameters)[1], max_nfev=evaluations, ftol=1e-11, xtol=1e-11, gtol=1e-11)
        return float(2*result.cost), (result.x+math.pi)%(2*math.pi)-math.pi


if __name__ == '__main__':
    case = load_cases()[0]
    model = Model(case)
    random = np.random.default_rng(1)
    labels = random.integers(len(model.labels), size=18)
    angles = random.uniform(-1,1,18)
    state, jacobian = model.evaluate(labels, angles)
    public = circuit_state(case, [(model.labels[label], theta) for label,theta in zip(labels, angles)])
    print('state_error',np.max(np.abs(state-public[model.keep])))
    difference = []
    for position in range(len(angles)):
        shifted = angles.copy()
        shifted[position] += 1e-6
        difference.append(np.max(np.abs((model.evaluate(labels,shifted)[0]-state)/1e-6-jacobian[:,position])))
    print('jacobian_error',max(difference))
    start = time.perf_counter()
    loss, angles = model.fit(labels,angles)
    print('fit_loss',loss,'seconds',time.perf_counter()-start)
