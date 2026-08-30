import ctypes
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.optimize import _lbfgsb
from scipy.linalg import cython_blas
from champion.optimize import Objective as PythonObjective, OptimizationDeadline, rotate, cost

library = ctypes.CDLL(str(Path(__file__).with_name('core.so')))
library.evaluate.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_double, ctypes.c_void_p, ctypes.c_void_p]
library.evaluate.restype = ctypes.c_double
capsule_name = ctypes.pythonapi.PyCapsule_GetName
capsule_name.argtypes = [ctypes.py_object]
capsule_name.restype = ctypes.c_char_p
capsule_pointer = ctypes.pythonapi.PyCapsule_GetPointer
capsule_pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
capsule_pointer.restype = ctypes.c_void_p
blas_capsule = cython_blas.__pyx_capi__['dgemm']
library.set_blas.argtypes = [ctypes.c_void_p]
library.set_blas.restype = None
library.set_blas(capsule_pointer(blas_capsule, capsule_name(blas_capsule)))
optimizer_capsule = getattr(_lbfgsb.setulb, '_cpointer', None)
if optimizer_capsule is not None:
    library.set_optimizer.argtypes = [ctypes.c_void_p]
    library.set_optimizer.restype = None
    library.set_optimizer(capsule_pointer(optimizer_capsule, capsule_name(optimizer_capsule)))
library.optimize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_double, ctypes.c_int, ctypes.c_int, ctypes.c_double,
                             ctypes.c_void_p, ctypes.c_void_p]
library.optimize.restype = ctypes.c_double


class Objective(PythonObjective):
    def __init__(self, one_body, factors, smoothing, deadline=None):
        super().__init__(np.ascontiguousarray(one_body), np.ascontiguousarray(factors), smoothing, deadline)
        self.gradient = np.empty(self.size)
        self.body_pointer = self.one_body.ctypes.data
        self.factor_pointer = self.factors.ctypes.data
        self.gradient_pointer = self.gradient.ctypes.data

    def __call__(self, parameters):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise OptimizationDeadline
        self.evaluations += 1
        value = library.evaluate(self.dimension, self.rank, self.body_pointer, self.factor_pointer,
                                 self.smoothing, parameters.ctypes.data, self.gradient_pointer)
        if value < self.best_value:
            self.best_value = value
            self.best_parameters = parameters.copy()
        return value, self.gradient.copy()


def refine(one_body, factors, orbital, auxiliary, schedule, maxiter=200, verbose=False, deadline=None, maxcor=20, native=True):
    total_evaluations = 0
    started = time.monotonic()
    for stage, smoothing in enumerate(schedule):
        if deadline is not None and time.monotonic() >= deadline:
            break
        rotated_body, rotated_factors = rotate(one_body, factors, orbital, auxiliary)
        objective = Objective(rotated_body, rotated_factors, smoothing, deadline)
        iterations = maxiter if isinstance(maxiter, int) else maxiter[stage]
        iteration_count = 0
        if native and optimizer_capsule is not None:
            parameters = np.zeros(objective.size)
            statistics = np.zeros(2, dtype=np.int32)
            seconds = 1000.0 if deadline is None else max(.000001, deadline - time.monotonic())
            library.optimize(objective.dimension, objective.rank, objective.body_pointer, objective.factor_pointer,
                             smoothing, iterations, maxcor, seconds, parameters.ctypes.data, statistics.ctypes.data)
            iteration_count = int(statistics[0])
            objective.evaluations = int(statistics[1])
        else:
            try:
                solution = minimize(objective, np.zeros(objective.size), jac=True, method='L-BFGS-B',
                                    options={'maxiter': iterations, 'ftol': 1e-11, 'gtol': 1e-6, 'maxls': 30, 'maxcor': maxcor})
                parameters = solution.x
                iteration_count = solution.nit
            except OptimizationDeadline:
                parameters = objective.best_parameters
        change_orbital, change_auxiliary, _, _ = objective.matrices(parameters)
        orbital = orbital @ change_orbital
        auxiliary = change_auxiliary @ auxiliary
        total_evaluations += objective.evaluations
        if verbose:
            print('stage', smoothing, cost(*rotate(one_body, factors, orbital, auxiliary)), iteration_count,
                  objective.evaluations, time.monotonic() - started, flush=True)
    return cost(*rotate(one_body, factors, orbital, auxiliary)), orbital, auxiliary, total_evaluations
