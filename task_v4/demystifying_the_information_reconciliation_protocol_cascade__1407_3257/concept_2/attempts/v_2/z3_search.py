import ctypes
import json
import re
import sys
import time


library = ctypes.CDLL('libz3.so.4')
pointer = ctypes.c_void_p
text = ctypes.c_char_p


def bind(name, result, arguments):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = arguments
    return function


make_config = bind('Z3_mk_config', pointer, [])
set_config = bind('Z3_set_param_value', None, [pointer, text, text])
make_context = bind('Z3_mk_context', pointer, [pointer])
make_symbol = bind('Z3_mk_string_symbol', pointer, [pointer, text])
make_tactic = bind('Z3_mk_tactic', pointer, [pointer, text])
make_solver = bind('Z3_mk_solver_from_tactic', pointer, [pointer, pointer])
solver_inc_ref = bind('Z3_solver_inc_ref', None, [pointer, pointer])
solver_from_string = bind('Z3_solver_from_string', None, [pointer, pointer, text])
solver_check = bind('Z3_solver_check', ctypes.c_int, [pointer, pointer])
solver_model = bind('Z3_solver_get_model', pointer, [pointer, pointer])
model_string = bind('Z3_model_to_string', text, [pointer, pointer])
solver_reason = bind('Z3_solver_get_reason_unknown', text, [pointer, pointer])
solver_stats = bind('Z3_solver_get_statistics', pointer, [pointer, pointer])
stats_string = bind('Z3_stats_to_string', text, [pointer, pointer])
config = make_config()
seconds = int(sys.argv[4]) if len(sys.argv) > 4 else 1200
set_config(config, b'timeout', str(seconds * 1000).encode())
context = make_context(config)
solver = make_solver(context, make_tactic(context, b'sat'))
solver_inc_ref(context, solver)
rows = [list(map(int, line.split())) for line in open('signatures.txt')][1:]
mode = sys.argv[1] if len(sys.argv) > 1 else 'xor'
begin = int(sys.argv[2]) if len(sys.argv) > 2 else 0
count = int(sys.argv[3]) if len(sys.argv) > 3 else len(rows)
clauses = ['(set-option :sat.cardinality.solver true)', '(set-option :sat.pb.solver solver)']
if len(sys.argv) > 5 and sys.argv[5] == 'sls':
    clauses.append('(set-option :sat.local_search true)')
clauses += [f'(declare-const x{bit} Bool)' for bit in range(begin, begin + count)]
checks = [[] for _ in range(384)]
for bit, signature in enumerate(rows):
    if not begin <= bit < begin + count:
        continue
    for dimension, block in enumerate(signature):
        checks[64 * dimension + block].append(f'x{bit}')
for check, variables in enumerate(checks):
    if mode.startswith('pairs'):
        clauses.append(f'(declare-const a{check} Bool)')
        weights = ' '.join(['1'] * len(variables) + ['2'])
        clauses.append(f'(assert ((_ pbeq 2 {weights}) ' + ' '.join(variables) + f' (not a{check})))')
    else:
        clauses.append('(assert (not (xor ' + ' '.join(variables) + ')))')
variables = ' '.join(f'x{bit}' for bit in range(begin, begin + count))
if mode.startswith('pairs'):
    exact = int(mode[5:]) // 2 if mode[5:] else None
    for dimension in range(6):
        active = ' '.join(f'a{64 * dimension + block}' for block in range(64))
        clauses.append(f'(assert ((_ at-most {exact or 9}) ' + active + '))')
        clauses.append(f'(assert ((_ at-least {exact or 4}) ' + active + '))')
    if exact is None:
        clauses.append(f'(assert a{begin // 128})')
else:
    clauses.append('(assert ((_ at-most 18) ' + variables + '))')
    clauses.append('(assert ((_ at-least 8) ' + variables + '))')
print('load', time.time(), flush=True)
solver_from_string(context, solver, '\n'.join(clauses).encode())
print('solve', time.time(), flush=True)
result = solver_check(context, solver)
print('result', result, time.time(), flush=True)
print(stats_string(context, solver_stats(context, solver)).decode(), flush=True)
if result == 1:
    model = model_string(context, solver_model(context, solver)).decode()
    print(model, flush=True)
    errors = [int(match) for match in re.findall(r'x(\d+) -> true', model)]
    with open('z3_core_' + mode + '_' + str(begin) + '.json', 'w') as stream:
        json.dump(errors, stream)
else:
    print(solver_reason(context, solver).decode(), flush=True)
