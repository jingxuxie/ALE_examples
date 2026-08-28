import argparse
import copy
import json
from pathlib import Path

import numpy as np
import wannierberri as wb
from irrep.spacegroup import SpaceGroup
from wannierberri.calculators.dynamic import Formula_OptCond
from wannierberri.data_K.data_K_R import Data_K_R
from wannierberri.formula.covariant import Omega
from wannierberri.symmetry.projections import Projection, ProjectionsSet
from wannierberri.symmetry.sawf import SymmetrizerSAWF

from qualify_reference import make_te


PILOT = Path(__file__).resolve().parents[2]
TASK_ROOT = PILOT.parent.parent


def make_native(material):
    if material == "Te":
        return make_te()
    if material != "Fe":
        raise ValueError("Unrecognized material")
    data_path = TASK_ROOT / "authoring/sources/WannierBerri-tutorial/tutorials/5_symmetrization/Fe_data/Fe_tb.dat"
    system = wb.System_R.from_tb_dat(tb_file=str(data_path), berry=True)
    spacegroup = SpaceGroup.from_cell(
        cell=(system.real_lattice, [[0, 0, 0]], [1]),
        magmom=[[0, 0, 1]], include_TR=True, spinor=True,
    )
    projections = ProjectionsSet([
        Projection(position_num=[[0, 0, 0]], orbital=orbital, spacegroup=spacegroup)
        for orbital in ["sp3d2", "t2g"]
    ])
    symmetrizer = SymmetrizerSAWF.from_spacegroup_and_projections(
        spacegroup=spacegroup, projections=projections
    )
    return system, symmetrizer


def response(system, points, occupied, external_terms=True):
    grid = wb.Grid(system, NK=1, NKFFT=1)
    inner = np.arange(occupied)
    outer = np.arange(occupied, system.num_wann)
    energies, berry, optical = [], [], []
    for point in points:
        data = Data_K_R(system, grid=grid, dK=point, fftlib="numpy")
        energies.append(data.E_K[0].copy())
        curvature = Omega(data, external_terms=external_terms).nn(0, inner, outer)
        berry.append(np.trace(curvature, axis1=0, axis2=1).real)
        optical.append(Formula_OptCond(data, external_terms=external_terms).trace_ln(0, inner, outer))
    return np.array(energies), np.array(berry), np.array(optical)


def export_model(system, frame, order):
    return {
        "lattice": system.real_lattice @ frame.T,
        "rvec": np.asarray(system.rvec.iRvec, dtype=np.int64),
        "ham": system.Ham_R[:, order][:, :, order],
        "connection": np.einsum("ab,rmnb->rmna", frame, system.get_R_mat("AA"))[:, order][:, :, order],
        "centers": system.wannier_centers_cart[order] @ frame.T,
    }


def export_symmetry(symmetrizer, frame, order):
    count = symmetrizer.num_wann
    operations = symmetrizer.spacegroup.symmetries
    unitary = np.zeros((len(operations), count, count), dtype=complex)
    shifts = np.zeros((len(operations), count, 3), dtype=np.int64)
    for block_index, bounds in enumerate(symmetrizer.D_wann_block_indices):
        rotations = np.asarray(symmetrizer.rot_orb_list[block_index])
        orbital_count = rotations.shape[-1]
        for atom_index in range(rotations.shape[0]):
            source = slice(int(bounds[0]) + atom_index * orbital_count,
                           int(bounds[0]) + (atom_index + 1) * orbital_count)
            for operation_index in range(len(operations)):
                mapped = int(symmetrizer.atommap_list[block_index][atom_index, operation_index])
                target = slice(int(bounds[0]) + mapped * orbital_count,
                               int(bounds[0]) + (mapped + 1) * orbital_count)
                unitary[operation_index, target, source] = rotations[atom_index, operation_index]
                shifts[operation_index, source] = -symmetrizer.T_list[block_index][atom_index, operation_index]
    return {
        "fractional_rotations": np.array([operation.rotation for operation in operations], dtype=np.int64),
        "cartesian_rotations": np.array([frame @ operation.rotation_cart @ frame.T for operation in operations]),
        "antiunitary": np.array([operation.time_reversal for operation in operations], dtype=bool),
        "unitary": unitary[:, order][:, :, order],
        "orbital_shifts": shifts[:, order],
        "translations": np.array([operation.translation for operation in operations]),
    }


def rotate_response(values, frame):
    energies, berry, optical = values
    return energies, np.linalg.det(frame) * berry @ frame.T, np.einsum("ab,kbc,dc->kad", frame, optical, frame)


def solve_case(case_path):
    case_path = Path(case_path)
    metadata = json.loads((case_path / "case.json").read_text())
    with np.load(case_path / "model.npz", allow_pickle=False) as archive:
        payload = {name: archive[name] for name in archive.files}
    frame = np.asarray(metadata["frame"], dtype=float)
    order = np.asarray(metadata["native_order"], dtype=int)
    inverse = np.argsort(order)
    system, symmetrizer = make_native(metadata["material"])
    if not np.array_equal(payload["rvec"], system.rvec.iRvec):
        raise ValueError("Unexpected raw real-space support")
    if not np.allclose(payload["lattice"] @ frame, system.real_lattice, atol=1e-10):
        raise ValueError("Inconsistent coordinate frame")
    system._XX_R["Ham"] = payload["ham"][:, inverse][:, :, inverse].copy()
    system._XX_R["AA"] = np.einsum("ab,rmnb->rmna", frame.T, payload["connection"][:, inverse][:, :, inverse])
    system.set_wannier_centers(wannier_centers_cart=payload["centers"][inverse] @ frame)
    system.clear_cached_R()
    original = rotate_response(response(system, payload["query_points"], metadata["occupied"]), frame)
    system.symmetrize2(symmetrizer, silent=True)
    repaired = rotate_response(response(system, payload["query_points"], metadata["occupied"]), frame)
    output = export_model(system, frame, order)
    output.update(energies=original[0], berry_raw=original[1], optical_raw=original[2],
                  berry_repaired=repaired[1], optical_repaired=repaired[2])
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(arguments.output, **solve_case(arguments.input))


if __name__ == "__main__":
    main()
