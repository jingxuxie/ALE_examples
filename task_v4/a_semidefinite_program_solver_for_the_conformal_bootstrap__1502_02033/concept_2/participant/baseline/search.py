from pathlib import Path
import runpy
import sys


WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"
sys.path.insert(0, str(WORKSPACE))
runpy.run_path(str(WORKSPACE / "baseline_search.py"), run_name="__main__")
