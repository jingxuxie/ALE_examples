import ctypes
import os
import re
from pathlib import Path
import numpy as np

_native=ctypes.CDLL(str(Path(__file__).with_name('libmonte2.so')))
_ptr=ctypes.c_void_p
_native.create_monte.argtypes=[ctypes.c_int,ctypes.c_int,_ptr,_ptr,_ptr]
_native.create_monte.restype=_ptr
_native.destroy_monte.argtypes=[_ptr]
_native.run_monte.argtypes=[_ptr,ctypes.c_int,_ptr,_ptr,_ptr,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_float,ctypes.c_float,ctypes.c_float]

def generators(model):
    matrix=model['detector_matrix']
    full=np.concatenate([matrix,model['observable_matrix']],axis=0)
    signatures=[int.from_bytes(row.tobytes(),'little') for row in np.packbits(full.T,axis=1)]
    lookup={value:index for index,value in enumerate(signatures)}
    neighbors=[set() for _ in signatures]
    for row in matrix:
        support=np.flatnonzero(row).tolist()
        for var in support:
            neighbors[var].update(support)
    component_groups={}
    for var,line in enumerate(model['dem_text'].splitlines()[:len(signatures)]):
        for piece in line.split(')',1)[1].split('^'):
            component=tuple(sorted(re.findall(r'[DL]\d+',piece)))
            component_groups.setdefault(component,[]).append(var)
    for support in component_groups.values():
        for var in support:
            neighbors[var].update(support)
    seen={}
    moves=set()
    for left,adjacent in enumerate(neighbors):
        for right in sorted(adjacent):
            if right<=left:
                continue
            signature=signatures[left]^signatures[right]
            third=lookup.get(signature)
            if third is not None:
                moves.add(tuple(sorted([left,right,third])))
            for old_left,old_right in seen.get(signature,[]):
                move=tuple(sorted(set([left,right])^set([old_left,old_right])))
                if move:
                    moves.add(move)
            seen.setdefault(signature,[]).append((left,right))
    moves=sorted(moves)
    offsets=np.array([0]+[len(move) for move in moves],dtype=np.int32).cumsum(dtype=np.int32)
    indexes=np.array([var for move in moves for var in move],dtype=np.int32)
    return offsets,indexes

class Monte:
    def __init__(self,model):
        offsets,indexes=generators(model)
        prob=np.ascontiguousarray(model['probabilities'],dtype=np.float64)
        self.handle=_native.create_monte(len(prob),len(offsets)-1,prob.ctypes.data,offsets.ctypes.data,indexes.ctypes.data)
        self.move_count=len(offsets)-1
    def __del__(self):
        _native.destroy_monte(self.handle)
    def run(self,states,costs):
        states=np.ascontiguousarray(states,dtype=np.uint8)
        costs=np.ascontiguousarray(costs,dtype=np.float32)
        output=np.zeros((len(states),32),dtype=np.float32)
        _native.run_monte(self.handle,len(states),states.ctypes.data,costs.ctypes.data,output.ctypes.data,int(os.getenv('BLOCKS',500)),int(os.getenv('REPLICAS',4)),int(os.getenv('STEPS',64)),float(os.getenv('BETA',1)),float(os.getenv('HOT',0.6)),float(os.getenv('ACTIVE',0.75)))
        return output

class Decoder:
    def __init__(self,model):
        self.model=model
        self.monte=Monte(model)
    def decode(self,syndromes):
        data=np.load(os.getenv('STATE_PREFIX','state24')+'_'+self.model['case_id']+'.npz')
        self.scores=self.monte.run(data['states'],data['costs'])
        labels=self.scores[:,:16].argmax(axis=1)
        return ((labels[:,None]>>np.arange(4))&1).astype(np.uint8)
