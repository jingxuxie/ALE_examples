import numpy as np
from fixed_group import Decoder as Parent, _original, _grouped
class Decoder(Parent):
    def __init__(self,model):
        super().__init__(model)
        self.original_trials = (24 if model['distance']>=9 else 16) if model['rounds']>1 else 8
        self.grouped_trials = 2 if model['rounds']>1 and model['distance']<9 else 4
        _grouped.set_group_gap(self.grouped,0)
    def decode(self,syndromes):
        syndromes=np.ascontiguousarray(syndromes,dtype=np.uint8)
        output=np.empty((len(syndromes),4),dtype=np.uint8)
        first=np.empty((len(syndromes),16),dtype=np.float32);second=np.empty_like(first)
        _original.run_info(self.original,len(syndromes),syndromes.ctypes.data,output.ctypes.data,first.ctypes.data,30,32,self.original_trials)
        _grouped.run_group(self.grouped,len(syndromes),syndromes.ctypes.data,output.ctypes.data,second.ctypes.data,40,32,self.grouped_trials,1)
        self.scores=np.minimum(first,second)
        labels=self.scores.argmin(1)
        return ((labels[:,None]>>np.arange(4))&1).astype(np.uint8)
