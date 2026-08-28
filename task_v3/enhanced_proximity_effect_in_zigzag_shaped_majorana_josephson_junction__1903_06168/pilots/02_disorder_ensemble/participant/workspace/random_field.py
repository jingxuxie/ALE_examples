import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from kwant.digest import uniform


def field(strength_meV, salt):
    def potential(*coordinates):
        return 2 * strength_meV * (uniform(repr(coordinates), repr(salt)) - 0.5)

    return potential
