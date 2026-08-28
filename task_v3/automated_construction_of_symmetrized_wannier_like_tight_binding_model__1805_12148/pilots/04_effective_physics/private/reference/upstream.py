import contextlib
import importlib
import io
import pathlib
import sys
import types

import numpy as np
import sympy


ROOT = pathlib.Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'authoring/sources/VASP2KP'


def modules():
    package = types.ModuleType('VASP2KP')
    package.__path__ = [str(SOURCE / 'VASP2KP==1.1.5/VASP2KP')]
    sys.modules['VASP2KP'] = package
    return importlib.import_module('VASP2KP._read_data'), importlib.import_module('VASP2KP._numeric_kp')


def load_material(relative_folder):
    reader, numeric = modules()
    folder = SOURCE / relative_folder
    namespace = dict(vars(sympy))
    exec(compile((folder / 'mat2kp.in').read_text(), str(folder / 'mat2kp.in'), 'exec'), namespace)
    symmetry = namespace['Symmetry']
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        operator, data, energy, target, dimensions = reader.load_data(symmetry, str(folder / namespace['vaspMAT']), gfactor=1, repr_split=False)
        np.random.seed(48191)
        momentum, spin, unitary, symmetry = numeric.get_U_pi_sigma(data, operator, symmetry, repr_split=False, dim_list=dimensions, gfactor=1, log=0)
    case = {
        'energy': np.asarray(energy)[:np.asarray(momentum).shape[1]],
        'momentum': np.asarray(momentum),
        'spin': np.asarray(spin),
        'target': np.asarray(target, dtype=int) - 1,
        'dft_repr': np.asarray([operator[name] for name in symmetry], dtype=complex),
        'standard_repr': np.asarray([entry['repr_matrix'] for entry in symmetry.values()], dtype=complex),
        'antiunitary': np.asarray([entry['repr_has_cc'] for entry in symmetry.values()], dtype=bool),
        'cart_rotation': np.asarray([entry['rotation_matrix'] for entry in symmetry.values()], dtype=float),
        'order': np.array(3),
    }
    return case, np.asarray(unitary, dtype=complex), capture.getvalue()


def coefficients(case):
    import numba
    reader, numeric = modules()
    dimension = len(case['target'])
    result = numeric.get_numeric_kp(list(case['momentum']), list(case['spin']), np.eye(dimension, dtype=complex), case['energy'], case['target'] + 1, order=int(case['order']), gfactor=1, acc=1)
    return {
        'H0': result['1'],
        'H1': np.moveaxis(np.asarray(result['k']), 0, -1),
        'H2': result['k^2'],
        'H3': result.get('k^3', np.zeros((dimension, dimension, 3, 3, 3), dtype=complex)),
        'G': result['B'],
    }


def rotate_basis(tensor, unitary):
    return np.einsum('ai,ab...,bj->ij...', unitary.conj(), tensor, unitary, optimize=True)


def gauge_residual(case, unitary):
    values = []
    for numerical, standard, anti in zip(case['dft_repr'], case['standard_repr'], case['antiunitary']):
        right = unitary.conj() if anti else unitary
        values.append(np.linalg.norm(numerical @ right - unitary @ standard) / max(1, np.sqrt(len(unitary))))
    values.append(np.linalg.norm(unitary.conj().T @ unitary - np.eye(len(unitary))) / np.sqrt(len(unitary)))
    return float(np.sqrt(np.mean(np.square(values))))
