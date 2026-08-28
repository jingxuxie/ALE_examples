"""Unrepaired historical import path (a93b8f805b3ade4436a89dffb209ae1d2f857dbd)."""

import numpy as np
import scipy.linalg as la
from historical_model import Model


class CartesianLoader(Model):
    @classmethod
    def from_wannier_files(cls, *, hr_file, wsvec_file=None, xyz_file=None, win_file=None, h_cutoff=0., ignore_orbital_order=False, **kwargs):
        """
        Create a :class:`.Model` instance from Wannier90 output files.

        :param hr_file:     Path of the ``*_hr.dat`` file. Together with the ``*_wsvec.dat`` file, this determines the hopping terms.
        :type hr_file:      str

        :param wsvec_file: Path of the ``*_wsvec.dat`` file. This file determines the remapping of hopping terms when ``use_ws_distance`` is used in the Wannier90 calculation.
        :type wsvec_file: str

        :param xyz_file: Path of the ``*_centres.xyz`` file. This file is used to determine the positions of the orbitals, from the Wannier centers given by Wannier90.
        :type xyz_file: str

        :param win_file: Path of the ``*.win`` file. This file is used to determine the unit cell.
        :type win_file: str

        :param h_cutoff:    Cutoff value for the hopping strength. Hoppings with a smaller absolute value are ignored.
        :type h_cutoff:     float

        :param ignore_orbital_order: Do not throw an error when the order of orbitals does not match what is expected from the Wannier90 output.
        :type ignore_orbital_order: bool

        :param kwargs:  :class:`.Model` keyword arguments.
        """
        if xyz_file is not None:
            if 'pos' in kwargs:
                raise ValueError("Ambiguous orbital positions: The positions can be given either via the 'pos' or the 'xyz_file' keywords, but not both.")
            with open(xyz_file, 'r') as f:
                kwargs['pos'], _ = cls._read_xyz(f)

        if win_file is not None:
            if 'uc' in kwargs:
                raise ValueError("Ambiguous unit cell: It can be given either via 'uc' or the 'win_file' keywords, but not both.")
            with open(win_file, 'r') as f:
                kwargs['uc'] = cls._read_win(f)['unit_cell_cart']

        with open(hr_file, 'r') as f:
            num_wann, hop_entries = cls._read_hr(f, ignore_orbital_order=ignore_orbital_order)
            hop_entries = (hop for hop in hop_entries if abs(hop[0]) > h_cutoff)

            if wsvec_file is not None:
                with open(wsvec_file, 'r') as f:
                    # wsvec_mapping is not a generator because it doesn't have
                    # the same order as the hoppings in _hr.dat
                    # This could still be done, but would be more complicated.
                    wsvec_generator = cls._async_parse(cls._read_wsvec(f), chunksize=num_wann)

                    def remap_hoppings(hop_entries):
                        for t, orbital_1, orbital_2, R in hop_entries:
                            next(wsvec_generator)
                            T_list = wsvec_generator.send((orbital_1, orbital_2, tuple(R)))
                            N = len(T_list)
                            for T in T_list:
                                # not using numpy here increases performance
                                yield (t / N, orbital_1, orbital_2, (r + t for r, t in zip(R, T)))
                    hop_entries = remap_hoppings(hop_entries)
                    return cls.from_hop_list(size=num_wann, hop_list=hop_entries, **kwargs)

            return cls.from_hop_list(size=num_wann, hop_list=hop_entries, **kwargs)
