import ctypes
from pathlib import Path


library = ctypes.CDLL(str(Path(__file__).resolve().with_name('evaluator.so')))
library.load_cases.argtypes = [ctypes.c_char_p]
library.make_samples.argtypes = [ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_double]
library.make_samples.restype = ctypes.c_void_p
library.free_samples.argtypes = [ctypes.c_void_p]
library.score.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ubyte)]
library.score.restype = ctypes.c_int
library.explicit_samples.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
library.explicit_samples.restype = ctypes.c_void_p
library.load_cases(str(Path(__file__).resolve().parent).encode())


class Samples:
    def __init__(self, scale, seed, count, density):
        self.count = count
        self.pointer = library.make_samples(scale - 1, seed, count, density)

    def score(self, axes, details=False):
        output = (ctypes.c_ubyte * self.count)() if details else None
        correct = library.score(self.pointer, (ctypes.c_int * 24)(*axes), output)
        return list(output) if details else correct / self.count

    def __del__(self):
        library.free_samples(self.pointer)

    @classmethod
    def explicit(cls, scale, records):
        instance = cls.__new__(cls)
        instance.count = len(records)
        offsets = [0]
        slots = []
        for record in records:
            slots.extend(record['support'])
            offsets.append(len(slots))
        instance.pointer = library.explicit_samples(scale - 1, len(records), (ctypes.c_uint * len(offsets))(*offsets), (ctypes.c_uint * len(slots))(*slots))
        return instance
