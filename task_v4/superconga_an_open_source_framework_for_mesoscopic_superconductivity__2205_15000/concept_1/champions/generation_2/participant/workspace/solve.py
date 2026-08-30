import runpy
from pathlib import Path

baseline = Path(__file__).resolve().parents[1] / "baseline" / "solve.py"
if not baseline.is_file():
    baseline = Path("/participant/baseline/solve.py")
runpy.run_path(str(baseline), run_name="__main__")
