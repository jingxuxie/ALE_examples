import argparse
import ctypes
import json
import time
import re
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--force', type=int, nargs='*', default=[])
parser.add_argument('--seconds', type=int, default=1800)
arguments = parser.parse_args()
output = Path.cwd()
deployment = json.loads(Path('deployment.json').read_text())
library = ctypes.CDLL('libz3.so.4')
pointer = ctypes.c_void_p


def api(name, result, *types):
    function = getattr(library, name)
    function.restype = result
    function.argtypes = list(types)
    return function


make_config = api('Z3_mk_config', pointer)
set_config = api('Z3_set_param_value', None, pointer, ctypes.c_char_p, ctypes.c_char_p)
make_context = api('Z3_mk_context', pointer, pointer)
make_tactic = api('Z3_mk_tactic', pointer, pointer, ctypes.c_char_p)
make_solver = api('Z3_mk_solver_from_tactic', pointer, pointer, pointer)
solver_ref = api('Z3_solver_inc_ref', None, pointer, pointer)
from_string = api('Z3_solver_from_string', None, pointer, pointer, ctypes.c_char_p)
check = api('Z3_solver_check', ctypes.c_int, pointer, pointer)
get_model = api('Z3_solver_get_model', pointer, pointer, pointer)
model_string = api('Z3_model_to_string', ctypes.c_char_p, pointer, pointer)
get_stats = api('Z3_solver_get_statistics', pointer, pointer, pointer)
stats_string = api('Z3_stats_to_string', ctypes.c_char_p, pointer, pointer)
config = make_config()
set_config(config, b'timeout', str(arguments.seconds * 1000).encode())
set_global = api('Z3_global_param_set', None, ctypes.c_char_p, ctypes.c_char_p)
set_global(b'sat.random_seed', str(arguments.seed).encode())
context = make_context(config)
tactic = make_tactic(context, b'sat')
solver = make_solver(context, tactic)
solver_ref(context, solver)
formulas = [f'(declare-const x{position} Bool)' for position in range(deployment['n'])]
for specification in deployment['passes']:
    permutation = specification['permutation']
    for start in range(0, deployment['n'], specification['block_size']):
        variables = ' '.join(f'x{position}' for position in permutation[start:start + specification['block_size']])
        formulas.append(f'(assert (not (xor {variables})))')
variables = ' '.join(f'x{position}' for position in range(deployment['n']))
formulas.extend([f'(assert ((_ at-most 18) {variables}))', f'(assert ((_ at-least 8) {variables}))'])
for position in arguments.force:
    formulas.append(f'(assert x{position})')
from_string(context, solver, '\n'.join(formulas).encode())
print('START', arguments, time.time(), flush=True)
result = check(context, solver)
print('RESULT', result, time.time(), flush=True)
if result == 1:
    text = model_string(context, get_model(context, solver)).decode()
    print(text, flush=True)
    support = sorted(int(position) for position in re.findall(r'x(\d+)\s*->\s*true', text))
    (output / 'sat_core.json').write_text(json.dumps({'errors': support}) + '\n')
    (output / f'model_{arguments.seed}.txt').write_text(text)
print(stats_string(context, get_stats(context, solver)).decode(), flush=True)
