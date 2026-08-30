import ctypes
import sys
from pathlib import Path

import numpy as np


def main():
    data = np.load(sys.argv[1], allow_pickle=False)
    inputs = np.ascontiguousarray(data["s"], dtype=np.float64)
    outputs = np.empty(len(inputs), dtype=np.float64)
    library = ctypes.CDLL(str(Path(__file__).resolve().parent / "kernel16.so"))
    pointer = ctypes.POINTER(ctypes.c_double)
    library.kernel_batch.argtypes = [ctypes.c_int, pointer, pointer]
    library.kernel_batch(len(inputs), inputs.ctypes.data_as(pointer), outputs.ctypes.data_as(pointer))
    np.savez(sys.argv[2], log_weight=np.log(outputs))


if __name__ == "__main__":
    main()
