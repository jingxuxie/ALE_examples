"""Standard baseline entry point; accepts --output PATH."""

from pathlib import Path
import runpy
import sys


if __name__ == "__main__":
    workspace = Path(__file__).resolve().parents[1] / "workspace"
    sys.path.insert(0, str(workspace))
    runpy.run_path(str(workspace / "baseline.py"), run_name="__main__")
