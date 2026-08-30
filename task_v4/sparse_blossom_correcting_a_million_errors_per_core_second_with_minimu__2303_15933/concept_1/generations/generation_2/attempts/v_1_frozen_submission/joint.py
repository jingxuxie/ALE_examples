import ctypes
import os
from pathlib import Path
import numpy as np

_native=ctypes.CDLL(str(Path(__file__).with_name('libjoint.so')))
_ptr=ctypes.c_void_p
_native.create_multi.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,_ptr,_ptr,_ptr,_ptr,ctypes.c_int,_ptr,_ptr,_ptr,_ptr]
_native.create_multi.restype=_ptr
_native.destroy_multi.argtypes=[_ptr]
_native.run_multi.argtypes=[_ptr,ctypes.c_int,_ptr,_ptr,_ptr,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int]
class Decoder:
    def __init__(self,model):
        kinds=model['mechanism_kind'];probabilities=model['probabilities']
        columns=[[],[],[]];groups=[];weights=[]
        for index,kind in enumerate(kinds):
            if kind=='X':
                px,pz,py=probabilities[index:index+3]
                distribution=np.zeros(4)
                for state in range(8):
                    probability=(px if state&1 else 1-px)*(pz if state&2 else 1-pz)*(py if state&4 else 1-py)
                    distribution[(state&3)^(3 if state&4 else 0)]+=probability
                groups.extend([len(weights)]*2)
                columns[0].extend([index,index+1]);columns[1].extend([index+1,index+2]);columns[2].extend([index,index+2])
                weights.append(np.log(distribution[0]/distribution))
            elif kind not in ('Z','Y'):
                groups.append(len(weights))
                for column in columns:column.append(index)
                weights.append([0,np.log((1-probabilities[index])/probabilities[index]),0,0])
        matrices=np.ascontiguousarray([model['detector_matrix'][:,column] for column in columns],dtype=np.uint8)
        logicals=np.ascontiguousarray([model['observable_matrix'][:,column] for column in columns],dtype=np.uint8)
        weights=np.ascontiguousarray(weights,dtype=np.float32);groups=np.ascontiguousarray(groups,dtype=np.int32)
        full_matrix=np.ascontiguousarray(model['detector_matrix'],dtype=np.uint8);full_obs=np.ascontiguousarray(model['observable_matrix'],dtype=np.uint8);full_prob=np.ascontiguousarray(probabilities,dtype=np.float64);full_columns=np.ascontiguousarray(columns[0],dtype=np.int32)
        self.handle=_native.create_multi(matrices.shape[1],matrices.shape[2],len(weights),matrices.ctypes.data,logicals.ctypes.data,weights.ctypes.data,groups.ctypes.data,len(probabilities),full_matrix.ctypes.data,full_obs.ctypes.data,full_prob.ctypes.data,full_columns.ctypes.data)
    def __del__(self):
        _native.destroy_multi(self.handle)
    def decode(self,syndromes):
        syndromes=np.ascontiguousarray(syndromes,dtype=np.uint8)
        output=np.empty((len(syndromes),4),dtype=np.uint8);self.scores=np.empty((len(syndromes),16),dtype=np.float32)
        _native.run_multi(self.handle,len(syndromes),syndromes.ctypes.data,output.ctypes.data,self.scores.ctypes.data,int(os.getenv('ITER',40)),int(os.getenv('ORDER',40)),int(os.getenv('TRIALS',8)),int(os.getenv('BMASK',7)))
        return output
