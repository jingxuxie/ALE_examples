import os
from pathlib import Path
import sys

try:
    import radial_public
except ModuleNotFoundError:
    sys.path.insert(0, os.environ.get("RADIAL_INPUT", str(Path(__file__).resolve().parents[1] / "input")))
from baseline_impl import main

if __name__ == "__main__":
    main()
