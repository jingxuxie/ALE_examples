import cmath
import sys
from pathlib import Path

import numpy as np
import scipy.constants as constants
import scipy.sparse.linalg as sparse_linalg

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_geometry
from kwant.continuum import discretizer


class NumericPrinter(discretizer._NumericPrinter):
    def __init__(self):
        super().__init__()
        self.known_functions.update({"sin": "sin", "cos": "cos", "exp": "exp"})


discretizer._NumericPrinter = NumericPrinter


def parameters(field_T, phase_rad):
    energy_unit = constants.eV * 1e-3
    return dict(
        m_eff=0.02 * constants.m_e / energy_unit / 1e18,
        hbar=constants.hbar / energy_unit,
        mu_B=constants.physical_constants["Bohr magneton"][0] / energy_unit,
        exp=cmath.exp,
        cos=cmath.cos,
        sin=cmath.sin,
        g_factor_middle=26,
        g_factor_left=0,
        g_factor_right=0,
        mu=10,
        alpha_middle=20,
        alpha_left=0,
        alpha_right=0,
        Delta_left=1,
        Delta_right=1,
        B_x=field_T,
        B_y=0,
        B_z=0,
        phase=phase_rad,
        V=0,
    )


def make_system(amplitude_nm):
    return clean_geometry.system(
        W=200,
        L_x=3900,
        L_sc_up=300,
        L_sc_down=300,
        z_x=1300,
        z_y=amplitude_nm,
        a=10,
        shape="parallel_curve",
        transverse_soi=True,
        mu_from_bottom_of_spin_orbit_bands=True,
        k_x_in_sc=True,
        wraparound=True,
        infinite=True,
    )


def clean_gap(system, params, samples=5):
    energies = []
    for phase in np.linspace(0, np.pi, samples):
        matrix = system.hamiltonian_submatrix(params=dict(params, k_x=float(phase)), sparse=True)
        spectrum = sparse_linalg.eigsh(matrix, k=4, sigma=0, return_eigenvectors=False)
        energies.append(float(np.min(np.abs(spectrum))))
    return min(energies)
