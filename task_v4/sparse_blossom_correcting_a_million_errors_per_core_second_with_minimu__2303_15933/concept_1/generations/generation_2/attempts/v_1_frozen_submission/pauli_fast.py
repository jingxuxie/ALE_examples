import ctypes
import os
from pathlib import Path
import numpy as np

_native = ctypes.CDLL(str(Path(__file__).with_name('libpauli_fast.so')))
_ptr = ctypes.c_void_p
_native.create_group.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, _ptr, _ptr, _ptr, _ptr, _ptr,ctypes.c_int]
_native.create_group.restype = _ptr
_native.destroy_group.argtypes = [_ptr]
_native.run_group.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]

class Decoder:
    def __init__(self, model):
        kinds = model['mechanism_kind']
        probabilities = model['probabilities']
        columns = []
        groups = []
        weights = []
        basis=int(os.getenv('BASIS',1))
        for index in range(len(kinds)):
            kind = kinds[index]
            if kind == 'X':
                assert tuple(kinds[index:index+3]) == ('X','Z','Y')
                px, pz, py = probabilities[index:index+3]
                distribution = np.zeros(4)
                for state in range(8):
                    prob = (px if state&1 else 1-px)*(pz if state&2 else 1-pz)*(py if state&4 else 1-py)
                    label = (state&3) ^ (3 if state&4 else 0)
                    distribution[label] += prob
                groups.extend([len(weights),len(weights)])
                columns.extend([index,index+1])
                weights.append(np.log(distribution[0]/distribution))
            elif kind not in ('Z','Y'):
                groups.append(len(weights))
                columns.append(index)
                weights.append([0,np.log((1-probabilities[index])/probabilities[index]),0,0])
        bp_matrix = np.ascontiguousarray(model['detector_matrix'][:,columns],dtype=np.uint8)
        if basis:
            for position,index in enumerate(columns):
                if kinds[index]=='X':
                    columns[position]=index+(1 if basis==1 else 0)
                    columns[position+1]=index+2
        matrix = np.ascontiguousarray(model['detector_matrix'][:,columns],dtype=np.uint8)
        logical = np.ascontiguousarray(model['observable_matrix'][:,columns],dtype=np.uint8)
        weights = np.ascontiguousarray(weights,dtype=np.float32)
        groups = np.ascontiguousarray(groups,dtype=np.int32)
        self.handle = _native.create_group(*matrix.shape,len(weights),matrix.ctypes.data,bp_matrix.ctypes.data,logical.ctypes.data,weights.ctypes.data,groups.ctypes.data,basis)
        self.trials = int(os.getenv('TRIALS', 4 if model['rounds']>1 else 8))
    def __del__(self):
        if getattr(self,'handle',None):
            _native.destroy_group(self.handle)
    def decode(self, syndromes):
        syndromes = np.ascontiguousarray(syndromes,dtype=np.uint8)
        output = np.empty((len(syndromes),4),dtype=np.uint8)
        self.scores = np.empty((len(syndromes),16),dtype=np.float32)
        _native.run_group(self.handle,len(syndromes),syndromes.ctypes.data,output.ctypes.data,self.scores.ctypes.data,int(os.getenv('ITER',40)),int(os.getenv('ORDER',40)),self.trials,int(os.getenv('EARLY',1)))
        return output
