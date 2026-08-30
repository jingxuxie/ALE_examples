import ctypes
from pathlib import Path
import numpy as np
from policy import Policy
from tempered import FinalCandidatePolicy


class HybridPolicy(FinalCandidatePolicy):
    def __init__(self, hello):
        super().__init__(hello)
        self.final_library = self.library
        self.library = ctypes.CDLL(str(Path(__file__).parent/'submission'/'sampler.so'))
        double_array = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        integer_array = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        self.library.sample_posterior.argtypes = [ctypes.c_int]*5+[integer_array]+[double_array]*8+[ctypes.c_int]*3+[ctypes.c_uint64]
        self.library.sample_posterior.restype = None
        self.sampler_tempered = False

    def posterior(self, samples=512, burn=450, thin=2):
        if samples<2048:
            return Policy.posterior(self, samples=samples, burn=burn, thin=thin)
        self.library = self.final_library
        self.sampler_tempered = True
        return super().posterior(samples=samples, burn=burn, thin=thin)
