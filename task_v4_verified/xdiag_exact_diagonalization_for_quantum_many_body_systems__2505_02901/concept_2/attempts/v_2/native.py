import ctypes
import time
from pathlib import Path
from solve import Compiler, np
from scipy.special import jv


class Native:
    def __init__(self, compiler, degree=36, radius=12., library_name=None):
        library = Path(__file__).with_name('propagate3.so')
        if not library.exists():
            library = Path(__file__).with_name('propagate2.so')
        if not library.exists():
            library = Path(__file__).with_name('propagate.so')
        if library_name is not None:
            library = Path(__file__).with_name(library_name)
        self.library = ctypes.CDLL(str(library))
        self.library.create_model.argtypes = [ctypes.c_void_p] * 5 + [ctypes.c_int, ctypes.c_double]
        self.library.create_model.restype = ctypes.c_void_p
        self.library.evaluate_model.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        self.library.evaluate_model.restype = ctypes.c_double
        orders = np.arange(degree + 1)
        coefficients = np.asarray(2 * (-1j) ** orders * jv(orders, radius * compiler.duration), dtype=np.complex128)
        coefficients[0] /= 2
        arrays = [np.ascontiguousarray(array, dtype=np.complex128) for array in [compiler.drifts, compiler.controls, compiler.initial, compiler.targets, coefficients]]
        self.context = self.library.create_model(*[array.ctypes.data for array in arrays], degree, radius)

    def objective(self, amplitudes, members, mode):
        amplitudes = np.ascontiguousarray(amplitudes, dtype=np.float64)
        gradient = np.empty((24, 3))
        mask = sum(1 << member for member in members)
        mode_index = {'linear': 0, 'aligned': 1, 'fidelity': 2, 'worst': 3}[mode]
        loss = self.library.evaluate_model(self.context, amplitudes.ctypes.data, mask, mode_index, gradient.ctypes.data)
        return loss, gradient

    def complex_objective(self, parameters, members):
        parameters = np.ascontiguousarray(parameters, dtype=np.float64)
        gradient = np.empty(144)
        mask = sum(1 << member for member in members)
        loss = self.library.evaluate_model(self.context, parameters.ctypes.data, mask, 4, gradient.ctypes.data)
        return loss, gradient


if __name__ == '__main__':
    import sys
    compiler = Compiler(sys.argv[1], 'fidelity')
    native = Native(compiler)
    amplitudes = np.random.default_rng(10).normal(size=(24, 3)) * .45
    start = time.monotonic()
    loss, gradient, states = compiler.member((amplitudes, 1))
    print('exact seconds', time.monotonic() - start, flush=True)
    start = time.monotonic()
    native_loss, native_gradient = native.objective(amplitudes, [1], 'fidelity')
    print('native seconds', time.monotonic() - start, 'loss error', native_loss - loss, 'gradient error', np.max(abs(gradient - native_gradient)), flush=True)
    start = time.monotonic()
    for trial in range(20):
        native.objective(amplitudes, [0, 1, 2, 3], 'fidelity')
    print('native ensemble seconds', (time.monotonic() - start) / 20, flush=True)
