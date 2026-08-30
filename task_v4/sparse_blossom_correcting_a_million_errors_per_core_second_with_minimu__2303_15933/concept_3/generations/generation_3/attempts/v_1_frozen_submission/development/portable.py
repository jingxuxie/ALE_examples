import ctypes
import solution

portable = ctypes.CDLL(str(solution.ROOT / 'kernel.so'))
for name in ('evaluate', 'distribution', 'conditional'):
    getattr(portable, name).argtypes = getattr(solution.LIB, name).argtypes
    getattr(portable, name).restype = getattr(solution.LIB, name).restype
solution.LIB = portable
solution.main()
