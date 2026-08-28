import json
from pathlib import Path

import numpy as np
import wannierberri as wb
from irrep.spacegroup import SpaceGroup
from wannierberri.symmetry.projections import Projection
from wannierberri.symmetry.sawf import SymmetrizerSAWF
from wannierberri.data_K.data_K_R import Data_K_R
from wannierberri.formula.covariant import Omega
from wannierberri.calculators.dynamic import Formula_OptCond


def make_te():
    task_root = Path(__file__).resolve().parents[4]
    data_path = task_root / "authoring/sources/WannierBerri-tutorial/tutorials/5_symmetrization/Te_data/Te_tb.dat"
    system = wb.System_R.from_tb_dat(tb_file=str(data_path), berry=True)
    system.spin_block2interlace()
    positions = np.array([[0.274, 0.274, 0], [0.726, 0, 1 / 3], [0, 0.726, 2 / 3]])
    spacegroup = SpaceGroup.from_cell(
        real_lattice=system.real_lattice,
        positions=positions,
        typat=[1, 1, 1],
        magmom=None,
        include_TR=True,
        spinor=True,
    )
    projections = [
        Projection(position_num=positions, orbital=orbital, spacegroup=spacegroup, rotate_basis=False)
        for orbital in ["s", "p"]
    ]
    symmetrizer = SymmetrizerSAWF.from_spacegroup_and_projections(
        spacegroup=spacegroup, projections=projections
    )
    return system, symmetrizer


def main():
    system, symmetrizer = make_te()
    print("RAW", system.Ham_R.shape, system.get_R_mat("AA").shape)
    print("BLOCKS", symmetrizer.D_wann_block_indices)
    print("ATTRIBUTES", sorted(symmetrizer.__dict__))
    print("ATOMIC_MAP_SHAPES", [np.shape(array) for array in symmetrizer.atommap_list])
    print("TRANSFORM_SHAPES", [np.shape(array) for array in symmetrizer.T_list])
    system.symmetrize2(symmetrizer, silent=True)
    print("SYMMETRIZED", system.Ham_R.shape, system.get_R_mat("AA").shape)
    grid = wb.Grid(system, NK=1, NKFFT=1)
    data = Data_K_R(system, grid=grid, dK=[0.17, 0.29, 0.41], fftlib="numpy")
    inner = np.arange(18)
    outer = np.arange(18, 24)
    result = {
        "energy": data.E_K[0],
        "berry": np.trace(Omega(data).nn(0, inner, outer), axis1=0, axis2=1).real,
        "optical": Formula_OptCond(data).trace_ln(0, inner, outer).real,
    }
    print("RESULT", json.dumps({name: np.asarray(values).tolist() for name, values in result.items()}))


if __name__ == "__main__":
    main()
