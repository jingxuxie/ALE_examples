import os
import numpy as np
from adaptive import Decoder as Parent

class Decoder(Parent):
    def __init__(self,model):
        mode=int(os.getenv('TRANSFORM',0))
        coords=model['detector_coordinates'];distance=model['distance']
        lookup={tuple(coord):index for index,coord in enumerate(coords)}
        target=[];source=[]
        for index,(column,row,time,sector) in enumerate(coords):
            if sector!=0:continue
            other=lookup[((column+(mode==3))%distance,(row+(mode==4))%distance,time,1)]
            reverse=mode==1 or (mode==2 and (column+row)%2)
            target.append(other if reverse else index)
            source.append(index if reverse else other)
        self.target=np.array(target);self.source=np.array(source)
        copied=dict(model)
        matrix=model['detector_matrix'].copy();matrix[self.target]^=matrix[self.source]
        copied['detector_matrix']=matrix
        super().__init__(copied)
    def decode(self,syndromes):
        shifted=syndromes.copy();shifted[:,self.target]^=shifted[:,self.source]
        return super().decode(shifted)
