import ctypes
import os
from pathlib import Path
import numpy as np
from adaptive import Decoder as Original

_native = ctypes.CDLL(str(Path(__file__).with_name('libstates.so')))
_ptr=ctypes.c_void_p
_native.create.argtypes=[ctypes.c_int,ctypes.c_int,_ptr,_ptr,_ptr]
_native.create.restype=_ptr
_native.run_states.argtypes=[_ptr,ctypes.c_int,_ptr,_ptr,_ptr,_ptr,ctypes.c_int,ctypes.c_int,ctypes.c_int]
_native.destroy.argtypes=[_ptr]

class Decoder:
    def __init__(self,model):
        self.model=model
        matrix=np.ascontiguousarray(model['detector_matrix'],dtype=np.uint8)
        logical=np.ascontiguousarray(model['observable_matrix'],dtype=np.uint8)
        prob=np.ascontiguousarray(model['probabilities'],dtype=np.float64)
        self.handle=_native.create(*matrix.shape,matrix.ctypes.data,logical.ctypes.data,prob.ctypes.data)
    def __del__(self):
        _native.destroy(self.handle)
    def decode(self,syndromes):
        syndromes=np.ascontiguousarray(syndromes,dtype=np.uint8)
        self.scores=np.empty((len(syndromes),5,16),dtype=np.float32)
        states=np.empty((len(syndromes),16,self.model['num_mechanisms']),dtype=np.uint8)
        costs=np.empty((len(syndromes),16),dtype=np.float32)
        _native.run_states(self.handle,len(syndromes),syndromes.ctypes.data,self.scores.ctypes.data,states.ctypes.data,costs.ctypes.data,int(os.getenv('ITER',40)),int(os.getenv('ORDER',40)),int(os.getenv('TRIALS',24)))
        if os.getenv('STATE_PREFIX'):
            np.savez_compressed(os.environ['STATE_PREFIX']+'_'+self.model['case_id']+'.npz',states=states,costs=costs,scores=self.scores)
        labels=self.scores[:,2].argmin(axis=1)
        return ((labels[:,None]>>np.arange(4))&1).astype(np.uint8)
