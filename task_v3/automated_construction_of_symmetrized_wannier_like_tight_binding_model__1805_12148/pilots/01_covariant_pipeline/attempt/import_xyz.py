"""Cartesian Wannier-centre import using the shared, repaired loader."""

from import_atom import AtomLoader


class CartesianLoader(AtomLoader):
    """Import Cartesian XYZ centres and convert them to reduced coordinates."""
