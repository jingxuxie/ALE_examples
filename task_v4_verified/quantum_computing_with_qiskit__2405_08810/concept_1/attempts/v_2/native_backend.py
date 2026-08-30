import ctypes
from pathlib import Path


LIBRARY = ctypes.CDLL(str(Path(__file__).with_name('phase_compiler.so')))
FUNCTION = LIBRARY.compile_phase
FUNCTION.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                     ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.c_double,
                     ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                     ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
FUNCTION.restype = ctypes.c_int
IMPROVE = LIBRARY.improve_phase
IMPROVE.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                    ctypes.c_int, ctypes.POINTER(ctypes.c_uint32), ctypes.c_int,
                    ctypes.POINTER(ctypes.c_int), ctypes.c_double,
                    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double)]
IMPROVE.restype = ctypes.c_int
OPTIMIZE = LIBRARY.optimize_phase
OPTIMIZE.argtypes = IMPROVE.argtypes
OPTIMIZE.restype = ctypes.c_int


def compile_native(instance, seconds=2.0, options=None):
    flattened = [value for edge in instance['edges'] for value in edge]
    edge_data = (ctypes.c_int * len(flattened))(*flattened)
    terms = (ctypes.c_uint32 * len(instance['terms']))(*instance['terms'])
    output = (ctypes.c_int * 300000)()
    report = (ctypes.c_double * 20)()
    if options is not None:
        options = list(options)
        if len(options) == 12:
            options.extend([1.0, 0.0, 0.0, 0.0])
    settings = (ctypes.c_double * 16)(*options) if options is not None else None
    length = FUNCTION(instance['n'], len(instance['edges']), edge_data,
                      len(instance['terms']), terms, seconds, output, 100000, settings, report)
    if length <= 0:
        raise RuntimeError('native compilation did not complete')
    operations = [[('cx', 'rz')[output[3 * index]], output[3 * index + 1], output[3 * index + 2]]
                  for index in range(length)]
    return {'ops': operations}, list(report)


def improve_native(instance, circuit, seconds=2.0, peephole=False):
    flattened = [value for edge in instance['edges'] for value in edge]
    edge_data = (ctypes.c_int * len(flattened))(*flattened)
    terms = (ctypes.c_uint32 * len(instance['terms']))(*instance['terms'])
    encoded = [value for kind, first, second in circuit['ops'] for value in (int(kind == 'rz'), first, second)]
    input_data = (ctypes.c_int * len(encoded))(*encoded)
    output = (ctypes.c_int * 300000)()
    report = (ctypes.c_double * 5)()
    function = OPTIMIZE if peephole else IMPROVE
    length = function(instance['n'], len(instance['edges']), edge_data,
                     len(instance['terms']), terms, len(circuit['ops']), input_data,
                     seconds, output, report)
    if not 0 < length <= 100000:
        raise RuntimeError('native optimization exceeded the output limit')
    operations = [[('cx', 'rz')[output[3 * index]], output[3 * index + 1], output[3 * index + 2]]
                  for index in range(length)]
    return {'ops': operations}, list(report)
