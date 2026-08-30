import ctypes
from pathlib import Path
import numpy as np


class ParityProjection:
    def __init__(self,known,expected,capacity):
        self.known=np.ascontiguousarray(known,dtype=np.float64)
        self.size=len(expected)
        self.capacity=capacity
        half=self.size//2
        base=np.r_[np.zeros(half,dtype=np.int64),np.asarray(known,dtype=np.int64)%2]
        def correlation(values):
            return np.rint(np.fft.irfft(abs(np.fft.rfft(values))**2,n=self.size)).astype(np.int64)%2
        initial=correlation(base)
        columns=[]
        for index in range(half):
            other=base.copy();other[index]^=1;other[index+half]^=1
            columns.append(correlation(other)^initial)
        matrix=np.array(columns).T
        rhs=np.asarray(expected,dtype=np.int64)%2^initial
        rows=[sum(int(matrix[row,column])<<column for column in range(half)) | (int(rhs[row])<<half) for row in range(self.size)]
        for index,total in enumerate(known.astype(int)):
            lower=max(0,total-capacity);upper=min(total,capacity)
            if lower==upper:
                rows.append((1<<index)|((lower%2)<<half))
        pivots=[]
        transforms=[1<<index for index in range(len(rows))]
        rank=0
        for column in range(half):
            pivot=next((index for index in range(rank,len(rows)) if rows[index]>>column&1),None)
            if pivot is None:continue
            rows[rank],rows[pivot]=rows[pivot],rows[rank]
            transforms[rank],transforms[pivot]=transforms[pivot],transforms[rank]
            for index in range(len(rows)):
                if index!=rank and rows[index]>>column&1:
                    rows[index]^=rows[rank]
                    transforms[index]^=transforms[rank]
            pivots.append(column);rank+=1
        self.feasible=not any(row==(1<<half) for row in rows)
        self.rank=rank
        free=[column for column in range(half) if column not in pivots]
        self.free_count=len(free)
        self.particular=np.zeros(half,dtype=np.int32)
        self.masks=np.zeros(half,dtype=np.uint32)
        for index,pivot in enumerate(pivots):self.particular[pivot]=(rows[index]>>half)&1
        if self.free_count<=20:
            for free_index,column in enumerate(free):
                self.masks[column]|=1<<free_index
                for index,pivot in enumerate(pivots):
                    if rows[index]>>column&1:self.masks[pivot]|=1<<free_index
        words=(half+63)//64
        self.rows=np.array([[(row>>(64*word))&((1<<min(64,half-word*64))-1) for word in range(words)] for row in rows[:rank]],dtype=np.uint64).reshape(-1)
        self.rhs=np.array([(row>>half)&1 for row in rows[:rank]],dtype=np.int32)
        self.valid=np.ones(1<<self.free_count if self.free_count<=20 else 1,dtype=np.uint8)
        if self.feasible and self.size<=64 and len(rows)==self.size and self.free_count<=20:
            def parity_bits(numbers):
                numbers=numbers.copy()
                for shift in [32,16,8,4,2,1]:numbers^=numbers>>np.uint64(shift)
                return numbers&np.uint64(1)
            for begin in range(0,len(self.valid),4096):
                patterns=np.arange(begin,min(begin+4096,len(self.valid)),dtype=np.uint64)
                code=np.array([parity_bits(patterns&np.uint64(mask))^np.uint64(part) for mask,part in zip(self.masks,self.particular)],dtype=np.int64).T
                candidates=np.concatenate([code,known.astype(int)[None,:]-code],axis=1)
                actual=np.rint(np.fft.irfft(abs(np.fft.rfft(candidates,axis=1))**2,n=self.size,axis=1)).astype(np.int64)
                residual=((np.asarray(expected)[None,:]-actual)//2)%2
                packed=np.zeros(len(patterns),dtype=np.uint64)
                for index in range(self.size):packed|=residual[:,index].astype(np.uint64)<<np.uint64(index)
                valid=np.ones(len(patterns),dtype=bool)
                for combination in transforms[rank:]:valid&=parity_bits(packed&np.uint64(combination))==0
                self.valid[begin:begin+len(patterns)]=valid
            self.feasible=bool(np.any(self.valid))
        self.library=ctypes.CDLL(str(Path(__file__).resolve().parent/'parity_projection_mod4.so'))
        double_array=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags='C_CONTIGUOUS')
        int_array=np.ctypeslib.ndpointer(dtype=np.int32,ndim=1,flags='C_CONTIGUOUS')
        self.library.project_parity.argtypes=[double_array,double_array,double_array,ctypes.c_int,ctypes.c_int,np.ctypeslib.ndpointer(dtype=np.uint64,ndim=1),int_array,ctypes.c_int,np.ctypeslib.ndpointer(dtype=np.uint32,ndim=1),int_array,ctypes.c_int,np.ctypeslib.ndpointer(dtype=np.uint8,ndim=1)]
    def project(self,values):
        result=np.empty(self.size)
        valid=self.library.project_parity(values,result,self.known,self.size,self.capacity,self.rows,self.rhs,self.rank,self.masks,self.particular,self.free_count,self.valid)
        return result if valid else None
