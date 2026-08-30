import ctypes
import os
import re
from pathlib import Path
import numpy as np

_native=ctypes.CDLL(str(Path(__file__).with_name('libworm.so')))
_ptr=ctypes.c_void_p
_native.create_worm.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,_ptr,_ptr,_ptr,_ptr,_ptr]
_native.create_worm.restype=_ptr
_native.destroy_worm.argtypes=[_ptr]
_native.run_worm.argtypes=[_ptr,ctypes.c_int,_ptr,_ptr,_ptr,ctypes.c_int,ctypes.c_float,ctypes.c_float,ctypes.c_int]

def generators(model):
    matrix=model['detector_matrix']
    signatures=[int.from_bytes(row.tobytes(),'little') for row in np.packbits(matrix.T,axis=1,bitorder='little')]
    neighbors=[set() for _ in signatures]
    for row in matrix:
        support=np.flatnonzero(row).tolist()
        for var in support:neighbors[var].update(support)
    components=[]
    single={}
    for var,line in enumerate(model['dem_text'].splitlines()[:len(signatures)]):
        pieces=[tuple(sorted(re.findall(r'[DL]\d+',piece))) for piece in line.split(')',1)[1].split('^')]
        components.append(pieces)
        if len(pieces)==1 and model['mechanism_kind'][var] in ('X','Z','readout'):single[pieces[0]]=var
    moves=set()
    for var,signature in enumerate(signatures):
        if signature.bit_count()==2:moves.add((var,))
        for other in neighbors[var]:
            if other>var and (signature^signatures[other]).bit_count()==2:moves.add((var,other))
        pieces=components[var]
        if len(pieces)>1:
            for selected in range(len(pieces)):
                move={var}
                for index,piece in enumerate(pieces):
                    if index!=selected:move.symmetric_difference_update([single[piece]])
                moves.add(tuple(sorted(move)))
    moves=sorted(moves)
    offsets=np.array([0]+[len(move) for move in moves],dtype=np.int32).cumsum(dtype=np.int32)
    indexes=np.array([var for move in moves for var in move],dtype=np.int32)
    ends=[];labels=[]
    obs=model['observable_matrix'].T@np.array([1,2,4,8])
    for move in moves:
        sig=0;label=0
        for var in move:sig^=signatures[var];label^=int(obs[var])
        assert sig.bit_count()==2
        first=(sig&-sig).bit_length()-1;sig^=1<<first
        ends.extend([first,sig.bit_length()-1]);labels.append(label)
    return offsets,indexes,np.array(ends,np.int32),np.array(labels,np.int32)

class Worm:
    def __init__(self,model):
        offsets,indexes,ends,labels=generators(model)
        prob=np.ascontiguousarray(model['probabilities'],dtype=np.float64)
        self.handle=_native.create_worm(len(prob),model['num_detectors'],len(offsets)-1,prob.ctypes.data,offsets.ctypes.data,indexes.ctypes.data,ends.ctypes.data,labels.ctypes.data)
    def __del__(self):
        _native.destroy_worm(self.handle)
    def run(self,states,costs):
        states=np.ascontiguousarray(states,dtype=np.uint8);costs=np.ascontiguousarray(costs,dtype=np.float32)
        output=np.zeros((len(states),32),np.float32)
        _native.run_worm(self.handle,len(states),states.ctypes.data,costs.ctypes.data,output.ctypes.data,int(os.getenv('WSTEPS',100000)),float(os.getenv('BETA',1)),float(os.getenv('FUGACITY',.02)),int(os.getenv('GIBBS',100)))
        return output

class Decoder:
    def __init__(self,model):
        self.model=model;self.worm=Worm(model)
    def decode(self,syndromes):
        data=np.load(os.getenv('STATE_PREFIX','state24')+'_'+self.model['case_id']+'.npz')
        self.scores=self.worm.run(data['states'],data['costs'])
        labels=self.scores[:,:16].argmax(1)
        return ((labels[:,None]>>np.arange(4))&1).astype(np.uint8)
