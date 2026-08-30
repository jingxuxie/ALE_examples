import ctypes
from pathlib import Path
import numpy as np
from scipy.sparse.linalg._eigen.arpack import _arpack

LIBRARY=ctypes.CDLL(str(Path(__file__).resolve().with_name('eigensolver.so')))
POINTER=ctypes.POINTER(ctypes.c_double)
LIBRARY.lowest.argtypes=[ctypes.c_int,POINTER,ctypes.c_int,ctypes.c_double,POINTER,POINTER,ctypes.c_int]
LIBRARY.lowest.restype=ctypes.c_int
LIBRARY.dense_lowest.argtypes=[ctypes.c_int,POINTER,ctypes.c_int,POINTER,POINTER]
LIBRARY.dense_lowest.restype=ctypes.c_int
LIBRARY.block_matrix.argtypes=[ctypes.c_int]*3+[POINTER]*4
LIBRARY.add_link.argtypes=[POINTER]+[ctypes.c_int]*7+[ctypes.c_double]+[POINTER]*2
LIBRARY.set_arpack.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
CAPSULE=ctypes.pythonapi.PyCapsule_GetPointer
CAPSULE.argtypes=[ctypes.py_object,ctypes.c_char_p]
CAPSULE.restype=ctypes.c_void_p
LIBRARY.set_arpack(CAPSULE(_arpack.dsaupd._cpointer,None),CAPSULE(_arpack.dseupd._cpointer,None))

def lowest(matrix,number=1,tolerance=1e-8):
    matrix=np.ascontiguousarray(matrix)
    values=np.empty(number)
    vectors=np.empty((len(matrix),number),order='F')
    status=LIBRARY.lowest(len(matrix),matrix.ctypes.data_as(POINTER),number,tolerance,values.ctypes.data_as(POINTER),vectors.ctypes.data_as(POINTER),1)
    if status!=0:
        status=LIBRARY.lowest(len(matrix),matrix.ctypes.data_as(POINTER),number,tolerance,values.ctypes.data_as(POINTER),vectors.ctypes.data_as(POINTER),0)
    if status!=0:
        raise RuntimeError('Eigenproblem failed: '+str(status))
    return values,vectors

def add_link(matrix,source_offset,target_offset,strength,left,right):
    left=np.ascontiguousarray(left)
    right=np.ascontiguousarray(right)
    LIBRARY.add_link(matrix.ctypes.data_as(POINTER),len(matrix),source_offset,target_offset,left.shape[1],right.shape[1],left.shape[0],right.shape[0],strength,left.ctypes.data_as(POINTER),right.ctypes.data_as(POINTER))

def dense_lowest(matrix,number):
    matrix=np.ascontiguousarray(matrix)
    values=np.empty(number)
    vectors=np.empty((len(matrix),number),order='F')
    status=LIBRARY.dense_lowest(len(matrix),matrix.ctypes.data_as(POINTER),number,values.ctypes.data_as(POINTER),vectors.ctypes.data_as(POINTER))
    if status:
        raise RuntimeError('Dense eigenproblem failed: '+str(status))
    return values,vectors

def block_matrix(hopping,interaction,potential,up,down,dimension):
    hopping=np.ascontiguousarray(hopping)
    interaction=np.ascontiguousarray(interaction)
    potential=np.ascontiguousarray(potential)
    matrix=np.empty((dimension,dimension))
    LIBRARY.block_matrix(len(interaction),up,down,hopping.ctypes.data_as(POINTER),interaction.ctypes.data_as(POINTER),potential.ctypes.data_as(POINTER),matrix.ctypes.data_as(POINTER))
    return matrix
