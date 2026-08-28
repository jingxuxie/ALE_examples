import json
import pathlib
import subprocess
import sys


def solve(case):
    num_cells = sum(map(len, case['stacks']))
    num_atoms = len(case['atoms'])
    num_sublattices = case['num_sublattices']
    lines = [' '.join(map(str, [num_cells, num_sublattices, len(case['stacks']), num_atoms, case['direction'], case['voltage_V'], case['cell_length_m'], case['cell_area_m2']]))]
    lines.extend(f'{stack[0]} {stack[-1]}' for stack in case['stacks'])
    for atom in case['atoms']:
        material = case['materials'][atom['material']]
        values = [atom['cell'], material['sublattice'], material['rho_ohm_m'], material['rho_spin_ohm_m'], material['moment_muB'], material['alpha'], material['eta'], material['beta'], *atom['spin']]
        lines.append(' '.join(map(str, values)))
    result = subprocess.run([str(pathlib.Path(__file__).with_name('reference_engine'))], input='\n'.join(lines)+'\n', text=True, capture_output=True, check=True, timeout=15)
    values = iter(map(float, result.stdout.split()))
    def take(count):
        return [next(values) for unused in range(count)]
    output = {'total_resistance_ohm': next(values), 'total_current_A': next(values)}
    for key in ['stack_resistance_ohm', 'stack_current_A']:
        output[key] = take(len(case['stacks']))
    output['cell_resistance_ohm'] = take(num_cells)
    output['channel_current_A'] = [take(num_sublattices) for unused in range(num_cells)]
    output['atom_field_T'] = [take(3) for unused in range(num_atoms)]
    output['atom_dspin_dt'] = [take(3) for unused in range(num_atoms)]
    return output


if __name__ == '__main__':
    case_path, output_path = map(pathlib.Path, sys.argv[1:])
    output_path.write_text(json.dumps(solve(json.loads(case_path.read_text())), allow_nan=False))
