import ctypes
import numpy as np
from variant import Decoder as Parent
from pathlib import Path
import variant
variant._native=ctypes.CDLL(str(Path(__file__).with_name('libprofile.so')))
variant._native.create.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
variant._native.create.restype=ctypes.c_void_p
variant._native.destroy.argtypes=[ctypes.c_void_p]
variant._native.run_info.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]
variant._native.times.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
class Decoder(Parent):
    def decode(self,syndromes):
        result=super().decode(syndromes)
        times=np.zeros(2,dtype=np.float64)
        variant._native.times(self.handle,times.ctypes.data)
        print('times',times,flush=True)
        return result
