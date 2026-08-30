from pathlib import Path
import runpy
import sys

sys.argv.extend(["--mode", "multistart"])
runpy.run_path(str(Path(__file__).resolve().parent / "portfolio.py"), run_name="__main__")
