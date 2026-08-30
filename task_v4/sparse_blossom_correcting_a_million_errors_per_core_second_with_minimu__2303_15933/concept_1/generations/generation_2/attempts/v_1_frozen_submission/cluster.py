import ctypes
import os
from pathlib import Path
import numpy as np
from monte import generators
_native=ctypes.CDLL(str(Path(__file__).with_name('libcluster.so')))
_ptr=ctypes.c_void_p
_native.create_cluster.argtypes=[ctypes.c_int,ctypes.c_int,_ptr,_ptr,_ptr]
_native.create_cluster.restype=_ptr
_native.destroy_cluster.argtypes=[_ptr]
_native.run_cluster.argtypes=[_ptr,ctypes.c_int,_ptr,_ptr,_ptr,ctypes.c_float,ctypes.c_int]
class Decoder:
    def __init__(self,model):
        self.model=model;offsets,indexes=generators(model);prob=np.ascontiguousarray(model['probabilities'],dtype=np.float64)
        self.handle=_native.create_cluster(len(prob),len(offsets)-1,prob.ctypes.data,offsets.ctypes.data,indexes.ctypes.data)
    def __del__(self):
        _native.destroy_cluster(self.handle)
    def decode(self,syndromes):
        data=np.load(os.getenv('STATE_PREFIX','state24')+'_'+self.model['case_id']+'.npz');states=np.ascontiguousarray(data['states']);costs=np.ascontiguousarray(data['costs'])
        self.scores=np.empty((len(states),16),dtype=np.float32)
        _native.run_cluster(self.handle,len(states),states.ctypes.data,costs.ctypes.data,self.scores.ctypes.data,float(os.getenv('CUTOFF',4)),int(os.getenv('RANK',12)))
        labels=self.scores.argmin(1)
        return ((labels[:,None]>>np.arange(4))&1).astype(np.uint8)
